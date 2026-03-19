"""
Agent Tools — Phase 5
Three callable tools that the LangGraph agent can invoke.
Each function has a clear docstring that the LLM reads to decide when to use it.
"""
import os
import sys
import json
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq import Groq
from dotenv import load_dotenv
from db.supabase_client import supabase
from pipeline.embedder import embed_text

load_dotenv()

GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def _find_scheme_by_name(name: str) -> dict | None:
    """Fuzzy scheme lookup: tries ilike, then keyword splits, then vector search."""
    # Try direct ilike
    res = supabase.table("schemes").select("*").ilike("scheme_name", f"%{name}%").limit(1).execute()
    if res.data:
        return res.data[0]

    # Try each keyword (e.g. 'PM Kisan' → search '%Kisan%')
    keywords = [w for w in name.split() if len(w) > 2]
    for kw in keywords:
        res = supabase.table("schemes").select("*").ilike("scheme_name", f"%{kw}%").limit(1).execute()
        if res.data:
            return res.data[0]

    # Fallback: use vector similarity to find the closest scheme name
    query_embedding = embed_text(name)
    rpc_res = supabase.rpc("match_schemes", {
        "query_embedding": query_embedding,
        "match_threshold": 0.2,
        "match_count": 1,
        "p_state": None,
        "p_age": None,
        "p_income": None,
    }).execute()
    if rpc_res.data:
        sid = rpc_res.data[0]["scheme_id"]
        res = supabase.table("schemes").select("*").eq("id", sid).execute()
        if res.data:
            return res.data[0]

    return None


# ---- TOOL 1: search_schemes ----

def search_schemes(user_profile: dict) -> list[dict]:
    """Search for government schemes matching the user's profile.
    Call this when you have enough profile information (at minimum: age, state,
    income or occupation). Returns a ranked list of matching schemes with
    eligibility details."""

    age = user_profile.get("age")
    state = user_profile.get("state")
    income = user_profile.get("annual_income") or user_profile.get("income")
    occupation = user_profile.get("occupation", "")
    category = user_profile.get("category", "")
    gender = user_profile.get("gender", "all")

    # Build a semantic search query from user profile
    search_parts = []
    if occupation:
        search_parts.append(f"schemes for {occupation}")
    if state:
        search_parts.append(f"in {state}")
    if income:
        search_parts.append(f"earning {income} rupees")
    if category:
        search_parts.append(f"for {category} category")
    if user_profile.get("gender") and user_profile.get("gender").lower() != "all":
        search_parts.append(f"for {user_profile.get('gender')}")
    if user_profile.get("is_bpl"):
        search_parts.append("BPL below poverty line")
    if user_profile.get("house_type") and str(user_profile.get("house_type")).lower() in ["kutcha", "none", "no pucca house"]:
        search_parts.append("needs housing pucca house")
        
    search_query = " ".join(search_parts) or "government welfare schemes"

    # Embed the query
    query_embedding = embed_text(search_query)

    # Call the match_schemes RPC function with metadata pre-filter
    result = supabase.rpc("match_schemes", {
        "query_embedding": query_embedding,
        "match_threshold": 0.15,
        "match_count": 10,
        "p_state": state,
        "p_age": age,
        "p_income": income,
    }).execute()

    if not result.data:
        return []

    # Group chunks by scheme and pick best match per scheme
    scheme_map: dict[str, dict] = {}
    for row in result.data:
        sid = row["scheme_id"]
        if sid not in scheme_map or row["similarity"] > scheme_map[sid]["similarity"]:
            scheme_map[sid] = row

    # Fetch full scheme metadata for matched schemes
    scheme_ids = list(scheme_map.keys())
    if not scheme_ids:
        return []

    schemes_data = (
        supabase.table("schemes")
        .select("*")
        .in_("id", scheme_ids)
        .execute()
    )

    schemes_by_id = {s["id"]: s for s in (schemes_data.data or [])}

    # Build results with eligibility breakdown
    results = []
    for sid, match in sorted(scheme_map.items(), key=lambda x: x[1]["similarity"], reverse=True)[:5]:
        scheme = schemes_by_id.get(sid, {})
        breakdown = _calculate_eligibility(scheme, user_profile)

        results.append({
            "scheme_name": scheme.get("scheme_name", match.get("scheme_name", "")),
            "ministry": scheme.get("ministry", ""),
            "state": scheme.get("state", "national"),
            "benefits_summary": match.get("chunk_text", "")[:200],
            "eligibility_summary": "",
            "match_score": round(match["similarity"], 3),
            "eligibility_breakdown": breakdown,
            "documents_needed": scheme.get("documents_needed", []),
            "application_url": scheme.get("application_url", ""),
        })

    return results


def _calculate_eligibility(scheme: dict, profile: dict) -> dict:
    """Calculate per-field eligibility breakdown."""
    breakdown = {}

    # Age check
    age = profile.get("age")
    age_min = scheme.get("age_min")
    age_max = scheme.get("age_max")
    if age is not None:
        age_req = f"{age_min or 'any'}-{age_max or 'any'}"
        passes = True
        if age_min and age < age_min:
            passes = False
        if age_max and age > age_max:
            passes = False
        breakdown["age"] = {
            "required": age_req,
            "user_value": str(age),
            "passes": passes,
        }

    # Income check
    income = profile.get("annual_income") or profile.get("income")
    income_limit = scheme.get("income_limit")
    if income is not None:
        if income_limit:
            breakdown["income"] = {
                "required": f"below ₹{income_limit:,}",
                "user_value": f"₹{income:,}",
                "passes": income <= income_limit,
            }
        else:
            breakdown["income"] = {
                "required": "no limit",
                "user_value": f"₹{income:,}",
                "passes": True,
            }

    # Category check
    user_cat = profile.get("category")
    scheme_cats = scheme.get("category", [])
    if user_cat and scheme_cats:
        passes = "All" in scheme_cats or user_cat in scheme_cats
        breakdown["category"] = {
            "required": "/".join(scheme_cats),
            "user_value": user_cat,
            "passes": passes,
        }

    # Gender check
    user_gender = profile.get("gender", "all")
    scheme_gender = scheme.get("gender", "all")
    if scheme_gender != "all" and user_gender != "all":
        breakdown["gender"] = {
            "required": scheme_gender,
            "user_value": user_gender,
            "passes": scheme_gender == user_gender or scheme_gender == "all",
        }

    # BPL check
    if scheme.get("bpl_required"):
        breakdown["bpl"] = {
            "required": "BPL card required",
            "user_value": "Yes" if profile.get("is_bpl") else "No",
            "passes": profile.get("is_bpl", False),
        }

    return breakdown


# ---- TOOL 2: explain_scheme ----

def explain_scheme(scheme_name: str, user_profile: dict) -> dict:
    """Get detailed explanation of a specific scheme and why the user qualifies or doesn't.
    Call this when the user asks about a specific scheme or wants to know more about one result."""

    # Fetch scheme by name (fuzzy)
    scheme = _find_scheme_by_name(scheme_name)
    if not scheme:
        return {"error": f"Scheme '{scheme_name}' not found in database."}

    # Fetch all chunks for this scheme
    chunks_res = (
        supabase.table("scheme_chunks")
        .select("chunk_text, chunk_type")
        .eq("scheme_id", scheme["id"])
        .execute()
    )
    chunks_text = "\n\n".join(
        f"[{c['chunk_type']}]: {c['chunk_text']}" for c in (chunks_res.data or [])
    )

    # Build the profile summary
    profile_summary = ", ".join(
        f"{k}: {v}" for k, v in user_profile.items() if v is not None and v != ""
    )

    # Call Groq for personalized explanation
    prompt = f"""Given this user profile: {profile_summary}
And this scheme information:
{chunks_text}

Explain in simple language:
1) What this scheme offers
2) Why this person qualifies or doesn't qualify (be specific about each criterion)
3) Exactly what documents they need
4) Step by step how to apply

Keep it concise and helpful. Use bullet points."""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful government scheme advisor for Indian citizens. Explain clearly in simple language."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    explanation = response.choices[0].message.content

    breakdown = _calculate_eligibility(scheme, user_profile)

    return {
        "scheme_name": scheme["scheme_name"],
        "explanation": explanation,
        "eligibility_breakdown": breakdown,
        "documents_needed": scheme.get("documents_needed", []),
        "application_url": scheme.get("application_url", ""),
    }


# ---- TOOL 3: get_application_guide ----

def get_application_guide(scheme_name: str) -> dict:
    """Get the complete step-by-step application guide for a scheme.
    Call this when user wants to know how to apply."""

    scheme = _find_scheme_by_name(scheme_name)
    if not scheme:
        return {"error": f"Scheme '{scheme_name}' not found."}

    # Fetch process chunks
    chunks_res = (
        supabase.table("scheme_chunks")
        .select("chunk_text")
        .eq("scheme_id", scheme["id"])
        .eq("chunk_type", "process")
        .execute()
    )
    process_text = "\n".join(c["chunk_text"] for c in (chunks_res.data or []))

    # Extract application steps from the structured data
    steps = []
    if process_text:
        # Split by numbered items or newlines
        lines = [l.strip() for l in process_text.split("\n") if l.strip()]
        for i, line in enumerate(lines, 1):
            steps.append(f"Step {i}: {line}")

    if not steps:
        steps = ["Step 1: Visit the official portal or nearest CSC center",
                 "Step 2: Fill the application form with required details",
                 "Step 3: Submit required documents",
                 "Step 4: Track application status online"]

    return {
        "scheme_name": scheme["scheme_name"],
        "steps": steps,
        "documents": scheme.get("documents_needed", []),
        "application_url": scheme.get("application_url", ""),
        "offline_option": "Visit nearest CSC center or Gram Panchayat",
    }


# ---- Tools list for LangGraph ----

TOOLS_LIST = [search_schemes, explain_scheme, get_application_guide]
