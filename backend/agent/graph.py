"""
LangGraph Agent — Phase 5
A 5-node conversational agent for government scheme discovery.

Flow:
  START → extract_profile → ask_clarification (if incomplete)
                          → search_and_respond (if complete)
                          → handle_specific_question (if asking about scheme)
  Any node → handle_error (on exception)
"""
import os
import sys
import json
import re
from typing import TypedDict, Annotated, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from agent.tools import search_schemes, explain_scheme, get_application_guide

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


# ---- Agent State (TypedDict for LangGraph) ----

class GraphState(TypedDict):
    """State flowing through the LangGraph nodes."""
    user_message: str
    session_id: str
    language: str
    user_profile: dict           # Incrementally built user profile
    profile_complete: bool       # True when we have enough info to search
    is_specific_question: bool   # True when user asks about a specific scheme
    target_scheme: str           # Name of scheme user is asking about
    schemes_found: list          # Results from search_schemes
    response_message: str        # Final response text
    response_type: str           # answer/question/schemes/error
    error: Optional[str]


# ---- NODE 1: extract_profile ----

def extract_profile(state: GraphState) -> GraphState:
    """
    Reads the user message and uses Groq to extract profile fields.
    Merges into existing profile. Checks if enough to search.
    """
    user_msg = state["user_message"]
    existing_profile = state.get("user_profile", {})

    # Ask the LLM to extract profile data from the message
    extraction_prompt = f"""Extract any personal information from this message and return ONLY valid JSON.
If a field is not mentioned, omit it. Do not guess or assume values.

Message: "{user_msg}"

Existing profile (update if new info given): {json.dumps(existing_profile)}

Return JSON with any of these fields:
{{
  "name": "string or null",
  "age": integer or null,
  "gender": "male/female/other or null",
  "state": "Indian state name in lowercase_underscore format or null",
  "district": "string or null",
  "category": "SC/ST/OBC/General/EWS or null",
  "annual_income": integer or null,
  "occupation": "string or null",
  "marital_status": "string or null",
  "is_bpl": true/false or null,
  "has_disability": true/false or null,
  "is_specific_question": false,
  "target_scheme": null
}}

If the user is asking about a SPECIFIC scheme (e.g. "tell me about PM Kisan" or "what is PMAY"),
set is_specific_question to true and target_scheme to the scheme name.

IMPORTANT: Return ONLY JSON. No explanation."""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a JSON extractor. Return ONLY valid JSON."},
                {"role": "user", "content": extraction_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        raw = response.choices[0].message.content.strip()
        # Parse JSON — handle code blocks
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        extracted = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        extracted = {}

    # Check if this is a specific scheme question
    is_specific = extracted.pop("is_specific_question", False)
    target_scheme = extracted.pop("target_scheme", None)

    # Merge extracted data into existing profile (only non-null values)
    merged = dict(existing_profile)
    for key, val in extracted.items():
        if val is not None and val != "" and str(val).lower() not in ["none", "null"]:
            merged[key] = val

    # Heuristic for housing declarations LLM JSON might miss
    if "मकान नहीं" in user_msg or "घर नहीं" in user_msg or "no pucca house" in user_msg.lower():
        merged["house_type"] = "kutcha"

    # Check if profile is complete enough to search
    # Minimum: age + state + one of (income, occupation, category)
    has_age = merged.get("age") is not None
    has_state = merged.get("state") is not None
    has_income = merged.get("annual_income") is not None
    has_extra = any(merged.get(k) is not None for k in ["occupation", "category"])
    profile_complete = has_age and has_state and has_income and has_extra


    state["user_profile"] = merged
    state["profile_complete"] = profile_complete
    state["is_specific_question"] = is_specific
    state["target_scheme"] = target_scheme or ""
    state["error"] = None

    return state


# ---- NODE 2: ask_clarification ----

def ask_clarification(state: GraphState) -> GraphState:
    """
    Profile is incomplete. Ask for missing information.
    Asks maximum 2 things at once. Switches to Hindi if needed.
    """
    profile = state.get("user_profile", {})
    language = state.get("language", "en")

    missing = []
    if not profile.get("age"):
        missing.append("age")
    if not profile.get("state"):
        missing.append("state")
    if not profile.get("annual_income"):
        missing.append("annual_income")
    if not profile.get("category"):
        missing.append("category (SC/ST/OBC/General/EWS)")

    # Ask maximum 2 at a time
    to_ask = missing[:2]

    if language == "hi":
        question_prompt = f"""Generate a friendly question in Hindi asking the user to provide: {', '.join(to_ask)}.
Context: We are helping them find government schemes they qualify for.
Already known: {json.dumps(profile)}
Keep it conversational and warm. Use simple Hindi. One short paragraph."""
    else:
        question_prompt = f"""Generate a friendly question asking the user to provide: {', '.join(to_ask)}.
Context: We are helping them find government schemes they qualify for.
Already known: {json.dumps(profile)}
Keep it conversational and warm. One short paragraph."""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a friendly government schemes assistant helping Indian citizens. Be warm and conversational."},
                {"role": "user", "content": question_prompt},
            ],
            temperature=0.5,
            max_tokens=200,
        )
        message = response.choices[0].message.content.strip()
    except Exception as e:
        message = f"Could you please tell me your {' and '.join(to_ask)}? This will help me find the best schemes for you."

    state["response_message"] = message
    state["response_type"] = "question"
    return state


# ---- NODE 3: search_and_respond ----

def search_and_respond(state: GraphState) -> GraphState:
    """
    Profile is complete enough. Search for schemes and format results.
    """
    profile = state.get("user_profile", {})

    try:
        # Call the search tool
        results = search_schemes(profile)
        state["schemes_found"] = results

        if not results:
            state["response_message"] = (
                "I searched our database but couldn't find schemes matching your exact profile. "
                "This could mean your income is above the limits, or we may not have schemes for "
                "your specific criteria yet. Would you like to adjust any details?"
            )
            state["response_type"] = "answer"
            return state

        # Format results into a readable response
        lines = [f"I found {len(results)} schemes that you may qualify for:\n"]
        for i, s in enumerate(results[:3], 1):
            name = s["scheme_name"]
            score = s["match_score"]
            benefits = s.get("benefits_summary", "")[:120]

            # Show eligibility breakdown
            breakdown_parts = []
            for field, info in s.get("eligibility_breakdown", {}).items():
                icon = "✅" if info["passes"] else "❌"
                breakdown_parts.append(f"  {icon} {field}: {info['user_value']} (needs: {info['required']})")

            lines.append(f"**{i}. {name}** (match: {score:.0%})")
            if benefits:
                lines.append(f"   {benefits}")
            if breakdown_parts:
                lines.append("\n".join(breakdown_parts))
            lines.append("")

        lines.append("Would you like to know more about any of these schemes?")
        state["response_message"] = "\n".join(lines)
        state["response_type"] = "schemes"

    except Exception as e:
        state["error"] = str(e)
        state["response_message"] = f"I encountered an error while searching: {e}. Please try again."
        state["response_type"] = "error"

    return state


# ---- NODE 4: handle_specific_question ----

def handle_specific_question(state: GraphState) -> GraphState:
    """
    User asked about a specific scheme. Fetch details and explain.
    """
    scheme_name = state.get("target_scheme", "")
    profile = state.get("user_profile", {})
    user_msg = state.get("user_message", "").lower()

    try:
        # Decide which tool to use
        if any(kw in user_msg for kw in ["apply", "how to", "application", "process", "steps"]):
            result = get_application_guide(scheme_name)
            if "error" in result:
                state["response_message"] = result["error"]
                state["response_type"] = "error"
                return state

            lines = [f"**How to apply for {result['scheme_name']}:**\n"]
            for step in result["steps"]:
                lines.append(f"• {step}")
            lines.append(f"\n**Documents needed:** {', '.join(result['documents'])}")
            if result["application_url"]:
                lines.append(f"\n**Apply online:** {result['application_url']}")
            lines.append(f"\n**Offline:** {result['offline_option']}")
            state["response_message"] = "\n".join(lines)
        else:
            result = explain_scheme(scheme_name, profile)
            if "error" in result:
                state["response_message"] = result["error"]
                state["response_type"] = "error"
                return state

            state["response_message"] = result["explanation"]
            if result.get("eligibility_breakdown"):
                state["schemes_found"] = [{
                    "scheme_name": result["scheme_name"],
                    "eligibility_breakdown": result["eligibility_breakdown"],
                    "documents_needed": result["documents_needed"],
                    "application_url": result["application_url"],
                    "match_score": 1.0,
                }]

        state["response_type"] = "answer"

    except Exception as e:
        state["error"] = str(e)
        state["response_message"] = f"Sorry, I couldn't find details about '{scheme_name}'. Error: {e}"
        state["response_type"] = "error"

    return state


# ---- NODE 5: handle_error ----

def handle_error(state: GraphState) -> GraphState:
    """Friendly error handler. Suggests alternatives."""
    error = state.get("error", "Unknown error")
    state["response_message"] = (
        f"I'm sorry, something went wrong while processing your request. "
        f"You can try:\n"
        f"1. Rephrasing your question\n"
        f"2. Providing your age, state, and income to search for schemes\n"
        f"3. Asking about a specific scheme like 'Tell me about PM Kisan'\n\n"
        f"(Technical: {error})"
    )
    state["response_type"] = "error"
    return state


# ---- Router function ----

def route_after_extraction(state: GraphState) -> str:
    """Decides which node to run after profile extraction."""
    if state.get("error"):
        return "handle_error"
    if state.get("is_specific_question") and state.get("target_scheme"):
        return "handle_specific_question"
    if state.get("profile_complete"):
        return "search_and_respond"
    return "ask_clarification"


# ---- Build the Graph ----

def build_graph():
    """Build and compile the LangGraph StateGraph."""
    from langgraph.graph import StateGraph, END

    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("extract_profile", extract_profile)
    graph.add_node("ask_clarification", ask_clarification)
    graph.add_node("search_and_respond", search_and_respond)
    graph.add_node("handle_specific_question", handle_specific_question)
    graph.add_node("handle_error", handle_error)

    # Set entry point — always start with profile extraction
    graph.set_entry_point("extract_profile")

    # Conditional routing after extraction
    graph.add_conditional_edges(
        "extract_profile",
        route_after_extraction,
        {
            "ask_clarification": "ask_clarification",
            "search_and_respond": "search_and_respond",
            "handle_specific_question": "handle_specific_question",
            "handle_error": "handle_error",
        },
    )

    # Terminal edges — all nodes end after execution
    graph.add_edge("ask_clarification", END)
    graph.add_edge("search_and_respond", END)
    graph.add_edge("handle_specific_question", END)
    graph.add_edge("handle_error", END)

    return graph.compile()


# Compile the graph at module level
app = build_graph()


# ---- Public entry point ----

async def run_agent(message: str, session_id: str, language: str = "en",
                    existing_profile: dict | None = None) -> dict:
    """
    Run the agent graph with a user message.
    Returns the final GraphState as a dict.
    """
    initial_state: GraphState = {
        "user_message": message,
        "session_id": session_id,
        "language": language,
        "user_profile": existing_profile or {},
        "profile_complete": False,
        "is_specific_question": False,
        "target_scheme": "",
        "schemes_found": [],
        "response_message": "",
        "response_type": "answer",
        "error": None,
    }

    try:
        result = app.invoke(initial_state)
        return dict(result)
    except Exception as e:
        initial_state["error"] = str(e)
        return handle_error(initial_state)
