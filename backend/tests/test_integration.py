"""
Integration Tests for FastAPI Backend — Phase 5
Interacts with the LIVE FastAPI server on http://localhost:8000.
Uses real Supabase and Groq — NO mocks here.
Run with: pytest tests/test_integration.py -v -m integration
"""
import httpx
import pytest
import uuid
import re

BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0  # High timeout to prevent ReadTimeout failures with LLM calls

# --------------------------------------------------------------------------
# 1. Full Profile Flow
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_full_profile_flow():
    """Hits /profile with complete data and verifies schemes match afterwards."""
    session_id = str(uuid.uuid4())
    
    profile_data = {
        "session_id": session_id,
        "name": "Kamla",
        "age": 45,
        "gender": "female",
        "state": "bihar",
        "category": "SC",
        "annual_income": 78000,
        "occupation": "Farmer",
        "is_bpl": True,
        "house_type": "Kutcha",
        "has_bank_account": True
    }

    # Step 1: POST /profile
    resp_prof = httpx.post(f"{BASE_URL}/profile", json=profile_data, timeout=TIMEOUT)
    assert resp_prof.status_code == 200
    assert resp_prof.json().get("success") is True

    # Step 2: POST /chat to trigger search
    chat_payload = {
        "message": "what schemes am I eligible for",
        "session_id": session_id,
        "language": "en"
    }
    resp_chat = httpx.post(f"{BASE_URL}/chat", json=chat_payload, timeout=TIMEOUT)
    assert resp_chat.status_code == 200
    
    data = resp_chat.json()
    assert data["response_type"] == "schemes"
    schemes = data["schemes_found"]
    
    assert schemes is not None
    assert len(schemes) >= 2
    
    # Assert PM Kisan exists in top 3
    top_3_names = [s["scheme_name"].lower() for s in schemes[:3]]
    assert any("kisan" in name for name in top_3_names), "PM Kisan not found in top 3 schemes"

    # Assert eligibility breakdown structure exists and has 'passes' booleans
    for scheme in schemes:
        breakdown = scheme.get("eligibility_breakdown")
        assert breakdown is not None
        for key, val in breakdown.items():
            assert "passes" in val


# --------------------------------------------------------------------------
# 2. Incremental Profile Collection
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_incremental_profile_collection():
    """Simulates conversational extraction over 3 turns to fetch schemes."""
    session_id = str(uuid.uuid4())

    # Turn 1: State
    resp1 = httpx.post(f"{BASE_URL}/chat", json={
        "message": "I am from Bihar",
        "session_id": session_id
    }, timeout=TIMEOUT)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["response_type"] != "schemes", "Should not trigger schemes yet"

    # Turn 2: Age only (omitted occupation)
    # Backend triggers complete IF: age + state + (income OR occupation OR category)
    # Providing 'farmer' triggers it turn 2. We provide just age to force turned ask clarification.
    resp2 = httpx.post(f"{BASE_URL}/chat", json={
        "message": "I am 45 years old",
        "session_id": session_id
    }, timeout=TIMEOUT)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["response_type"] != "schemes", "Should not trigger schemes yet"

    # Turn 3: Income & Category -> TRIGGERS SEARCH
    resp3 = httpx.post(f"{BASE_URL}/chat", json={
        "message": "My income is 60000, I am SC category",
        "session_id": session_id
    }, timeout=TIMEOUT)
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["response_type"] == "schemes", "Should trigger schemes list now"
    assert data3["schemes_found"] is not None
    assert len(data3["schemes_found"]) > 0


# --------------------------------------------------------------------------
# 3. Hindi End To End Flow
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_hindi_end_to_end():
    """Hits agent with Hindi request and expects Hindi response output containing schemes."""
    session_id = str(uuid.uuid4())

    # Devanagari text declaring critical profile variables all at once
    resp = httpx.post(f"{BASE_URL}/chat", json={
        "message": "मैं बिहार से हूं, किसान हूं, मेरी उम्र 45 है, आय 60000 है",
        "session_id": session_id
    }, timeout=TIMEOUT)
    assert resp.status_code == 200
    data = resp.json()

    # Check that response message uses Devanagari characters (Hindi output)
    assert re.search(r"[\u0900-\u097F]", data["message"]), "Response message is not in Hindi/Devanagari script"
    
    # Verification that it computed schemes output correctly (even if formatted conversationally)
    assert data["response_type"] == "schemes"
    assert data["schemes_found"] is not None


# --------------------------------------------------------------------------
# 4. Specific Scheme Queries
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_specific_scheme_query():
    """Queries about a specific scheme and asserts rich breakdown payload exists."""
    session_id = str(uuid.uuid4())

    resp = httpx.post(f"{BASE_URL}/chat", json={
        "message": "tell me about PM Kisan scheme",
        "session_id": session_id
    }, timeout=TIMEOUT)
    assert resp.status_code == 200
    data = resp.json()
    
    mesg_lower = data["message"].lower()
    schemes = data.get("schemes_found") or []

    # Valid profile or breakdown components listed implicitly or explicitly
    is_breakdown_present = "eligibility" in mesg_lower or (schemes and schemes[0].get("eligibility_breakdown"))
    is_docs_present = ("document" in mesg_lower or "card" in mesg_lower or "book" in mesg_lower) or (schemes and schemes[0].get("documents_needed"))
    is_steps_present = ("step" in mesg_lower or "apply" in mesg_lower or "visit" in mesg_lower)

    assert is_breakdown_present, "Response doesn't appear to evaluate eligibility limits/breakdown"
    assert is_docs_present, "Response doesn't list required documentation"
    assert is_steps_present, "Response doesn't advise on application process / steps"


# --------------------------------------------------------------------------
# 5. Analytics Recording
# --------------------------------------------------------------------------

@pytest.mark.integration
def test_analytics_recording():
    """Verify that interaction hits successfully increment total_queries payload."""
    # Step 1: Capture initial count
    resp_init = httpx.get(f"{BASE_URL}/analytics/summary", timeout=TIMEOUT)
    assert resp_init.status_code == 200
    init_total = resp_init.json().get("total_queries", 0)

    # Step 2: Push 3 sequential distinct chats
    # Foreign key references user_profiles(session_id). We must create profile first.
    for _ in range(3):
        sess_id = str(uuid.uuid4())
        # Add basic profile so row creates in db to bypass foreign key constraint failures
        httpx.post(f"{BASE_URL}/profile", json={"session_id": sess_id}, timeout=TIMEOUT)
        
        httpx.post(f"{BASE_URL}/chat", json={
            "message": "Hello query checkpoint node",
            "session_id": sess_id
        }, timeout=TIMEOUT)

    # Step 3: Recalculate tally
    resp_new = httpx.get(f"{BASE_URL}/analytics/summary", timeout=TIMEOUT)
    assert resp_new.status_code == 200
    new_total = resp_new.json().get("total_queries", 0)

    assert new_total == init_total + 3
