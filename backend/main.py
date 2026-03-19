"""
FastAPI Application — Phase 5
Complete API server for the NagarikAI government schemes discovery agent.
"""
import os
import sys
import json
import time
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from models.schemas import (
    ChatRequest, ChatResponse, UserProfile, SchemeMatch, ResponseType,
)
from agent.graph import run_agent
from agent.tools import search_schemes
from db.supabase_client import supabase
from utils.translator import (
    detect_language, translate_to_english, translate_to_language,
    translate_scheme_card,
)


app = FastAPI(
    title="NagarikAI — Government Schemes Discovery Agent",
    description="RAG-powered conversational agent for Indian government welfare scheme discovery",
    version="1.0.0",
)

# ---- CORS ----
cors_origins = os.environ.get("CORS_ORIGINS", '["http://localhost:3000"]')
try:
    origins = json.loads(cors_origins)
except json.JSONDecodeError:
    origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Rate Limiting (in-memory, per session_id) ----
_rate_tracker: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 30  # max requests per minute


def check_rate_limit(session_id: str):
    now = time.time()
    window = [t for t in _rate_tracker[session_id] if now - t < 60]
    _rate_tracker[session_id] = window
    if len(window) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT} requests/minute per session."
        )
    _rate_tracker[session_id].append(now)


# ---- Request Logging Middleware ----
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000
    print(f"[{request.method}] {request.url.path} — {response.status_code} ({duration:.0f}ms)")
    return response


# ---- Global Exception Handler ----
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}. Please try again."},
    )


# =======================================
# ENDPOINT 1: POST /chat
# =======================================

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Main conversational endpoint.
    Processes user message through the LangGraph agent.
    """
    check_rate_limit(req.session_id)

    # 1. Load existing profile from Supabase
    existing_profile = {}
    try:
        profile_res = (
            supabase.table("user_profiles")
            .select("*")
            .eq("session_id", req.session_id)
            .limit(1)
            .execute()
        )
        if profile_res.data:
            existing_profile = profile_res.data[0]
    except Exception:
        pass

    # 2. Detect language and translate to English if needed
    detected_lang = req.language
    message_en = req.message

    if detected_lang != "en":
        message_en = translate_to_english(req.message, detected_lang)
    elif detect_language(req.message) != "en":
        detected_lang = detect_language(req.message)
        message_en = translate_to_english(req.message, detected_lang)

    # 3. Run the agent
    result = await run_agent(
        message=message_en,
        session_id=req.session_id,
        language=detected_lang,
        existing_profile=existing_profile,
    )

    # 4. Save/update user profile if new data was extracted
    updated_profile = result.get("user_profile", {})
    if updated_profile and any(v for k, v in updated_profile.items() if k != "session_id" and v is not None):
        try:
            updated_profile["session_id"] = req.session_id
            # Check if profile exists
            existing = (
                supabase.table("user_profiles")
                .select("id")
                .eq("session_id", req.session_id)
                .execute()
            )
            # Filter out non-table fields
            db_fields = {
                "session_id", "name", "age", "gender", "state", "district",
                "category", "annual_income", "occupation", "marital_status",
                "is_bpl", "has_disability", "owns_land", "house_type",
                "education_level", "has_bank_account", "language_pref"
            }
            profile_row = {k: v for k, v in updated_profile.items() if k in db_fields and v is not None}
            profile_row["session_id"] = req.session_id
            profile_row["language_pref"] = detected_lang

            if existing.data:
                supabase.table("user_profiles").update(profile_row).eq("session_id", req.session_id).execute()
            else:
                supabase.table("user_profiles").insert(profile_row).execute()
        except Exception as e:
            print(f"[warn] Failed to save profile: {e}")

    # 5. Log query
    try:
        schemes_shown = [s.get("scheme_name", "") for s in result.get("schemes_found", [])]
        supabase.table("query_logs").insert({
            "session_id": req.session_id,
            "state": updated_profile.get("state"),
            "query_text": req.message,
            "schemes_shown": schemes_shown,
            "response_time_ms": 0,
        }).execute()
    except Exception:
        pass

    # 6. Translate response if needed
    response_msg = result.get("response_message", "Sorry, I couldn't process your request.")
    if detected_lang != "en":
        response_msg = translate_to_language(response_msg, detected_lang)

    # Build SchemeMatch list
    schemes = None
    raw_schemes = result.get("schemes_found", [])
    if raw_schemes:
        schemes = []
        for s in raw_schemes:
            match = SchemeMatch(
                scheme_name=s.get("scheme_name", ""),
                ministry=s.get("ministry"),
                state=s.get("state"),
                benefits_summary=s.get("benefits_summary"),
                eligibility_summary=s.get("eligibility_summary"),
                match_score=s.get("match_score", 0),
                eligibility_breakdown=s.get("eligibility_breakdown", {}),
                documents_needed=s.get("documents_needed", []),
                application_url=s.get("application_url"),
            )
            if detected_lang != "en":
                match_dict = translate_scheme_card(match.model_dump(), detected_lang)
                match = SchemeMatch(**match_dict)
            schemes.append(match)

    return ChatResponse(
        message=response_msg,
        session_id=req.session_id,
        schemes_found=schemes,
        response_type=ResponseType(result.get("response_type", "answer")),
        language=detected_lang,
    )


# =======================================
# ENDPOINT 2: POST /profile
# =======================================

@app.post("/profile")
async def save_profile(profile: UserProfile):
    """Save or update a user profile."""
    try:
        existing = (
            supabase.table("user_profiles")
            .select("id")
            .eq("session_id", profile.session_id)
            .execute()
        )
        profile_data = profile.model_dump(exclude_none=True)

        if existing.data:
            supabase.table("user_profiles").update(profile_data).eq("session_id", profile.session_id).execute()
        else:
            supabase.table("user_profiles").insert(profile_data).execute()

        return {"success": True, "session_id": profile.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================
# ENDPOINT 3: GET /profile/{session_id}
# =======================================

@app.get("/profile/{session_id}")
async def get_profile(session_id: str):
    """Fetch a user profile by session_id."""
    try:
        res = (
            supabase.table("user_profiles")
            .select("*")
            .eq("session_id", session_id)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
        return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =======================================
# ENDPOINT 4: GET /schemes/search
# =======================================

@app.get("/schemes/search")
async def search_schemes_direct(
    state: str = None,
    category: str = None,
    age: int = None,
    income: int = None,
):
    """Direct scheme search without agent (for testing)."""
    profile = {}
    if state:
        profile["state"] = state
    if category:
        profile["category"] = category
    if age:
        profile["age"] = age
    if income:
        profile["annual_income"] = income

    results = search_schemes(profile)
    return [SchemeMatch(**r) for r in results]


# =======================================
# ENDPOINT 5: GET /analytics/summary
# =======================================

@app.get("/analytics/summary")
async def analytics_summary():
    """Analytics dashboard data."""
    try:
        # Total queries
        q_res = supabase.table("query_logs").select("id", count="exact").execute()
        total_queries = q_res.count or 0

        # Unique sessions
        s_res = supabase.table("user_profiles").select("id", count="exact").execute()
        unique_sessions = s_res.count or 0

        # Top schemes (from query_logs.schemes_shown)
        logs_res = supabase.table("query_logs").select("schemes_shown").execute()
        scheme_counter: dict[str, int] = defaultdict(int)
        for log in (logs_res.data or []):
            for name in (log.get("schemes_shown") or []):
                if name:
                    scheme_counter[name] += 1
        top_schemes = [
            {"name": k, "count": v}
            for k, v in sorted(scheme_counter.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Queries by state
        state_res = supabase.table("query_logs").select("state").execute()
        state_counter: dict[str, int] = defaultdict(int)
        for log in (state_res.data or []):
            st = log.get("state") or "unknown"
            state_counter[st] += 1

        # Queries today
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        today_res = (
            supabase.table("query_logs")
            .select("id", count="exact")
            .gte("timestamp", f"{today_str}T00:00:00Z")
            .execute()
        )
        queries_today = today_res.count or 0

        return {
            "total_queries": total_queries,
            "unique_sessions": unique_sessions,
            "top_schemes": top_schemes,
            "queries_by_state": dict(state_counter),
            "queries_today": queries_today,
        }
    except Exception as e:
        return {"error": str(e), "total_queries": 0, "unique_sessions": 0,
                "top_schemes": [], "queries_by_state": {}, "queries_today": 0}


# =======================================
# ENDPOINT 6: GET /health
# =======================================

@app.get("/health")
async def health_check():
    """Health check: DB connected, LLM reachable."""
    status = {"status": "ok", "db_connected": False, "llm_connected": False}

    # Check Supabase
    try:
        supabase.table("schemes").select("id").limit(1).execute()
        status["db_connected"] = True
    except Exception:
        pass

    # Check Groq
    try:
        from groq import Groq
        client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
        client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        status["llm_connected"] = True
    except Exception:
        pass

    return status
