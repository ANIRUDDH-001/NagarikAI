"""
Demo Story Multi-Turn Simulation — Phase 5
Runs user scenario sequentially using live FastAPI endpoints.
Validates profile transitions, language strictness and detailed content arrays.
Run with: python tests/test_demo_story.py
"""
import httpx
import uuid
import re
import sys

BASE_URL = "http://localhost:8000"
TIMEOUT = 60.0  # Safe boundary for heavy loads

def assert_hindi(text: str, context: str):
    """Utility asserting text contains Devanagari characters."""
    assert re.search(r"[\u0900-\u097F]", text), f"[{context}] Message is not in Hindi: {text}"

def simulate_demo():
    print("=== NagarikAI Demo Story Simulation Starting ===")
    session_id = str(uuid.uuid4())
    all_responses = []

    # --------------------------------------------------------------------------
    # TURN 1: User introduces herself in Hindi
    # --------------------------------------------------------------------------
    print("\n[Turn 1] User introducing herself...")
    payload1 = {
        "message": "नमस्ते, मैं बिहार से हूं, मेरा नाम कमला है",
        "session_id": session_id
    }
    resp1 = httpx.post(f"{BASE_URL}/chat", json=payload1, timeout=TIMEOUT)
    assert resp1.status_code == 200, "Turn 1 failed request"
    data1 = resp1.json()
    all_responses.append(data1)

    assert_hindi(data1["message"], "Turn 1")
    assert data1["response_type"] == "question", "Expected question, got schemes early"
    print("  ✅ Language set as Hindi; Asked for more profile inputs.")

    # --------------------------------------------------------------------------
    # TURN 2: User provides basic details (Age, occupation, category)
    # --------------------------------------------------------------------------
    print("\n[Turn 2] Providing age/occupation/category...")
    payload2 = {
        "message": "मेरी उम्र 45 साल है, मैं किसान हूं, SC हूं",
        "session_id": session_id
    }
    resp2 = httpx.post(f"{BASE_URL}/chat", json=payload2, timeout=TIMEOUT)
    assert resp2.status_code == 200, "Turn 2 failed request"
    data2 = resp2.json()
    all_responses.append(data2)

    # Assert updated profile state in backend
    profile_resp = httpx.get(f"{BASE_URL}/profile/{session_id}", timeout=TIMEOUT)
    assert profile_resp.status_code == 200, "Failed to fetch updated profile"
    profile = profile_resp.json()

    assert profile.get("age") == 45, f"Expected age=45, got {profile.get('age')}"
    # Validates string overlap accurately
    assert "farm" in str(profile.get("occupation")).lower(), "Occupation not extracted as farmer"
    assert profile.get("category") == "SC", f"Expected category=SC, got {profile.get('category')}"
    assert_hindi(data2["message"], "Turn 2")
    print(f"  [DEBUG] Turn 2 Response Type: {data2.get('response_type')}")
    print(f"  [DEBUG] Schemes Found: {len(data2.get('schemes_found', [])) if data2.get('schemes_found') else 0}")
    assert data2["response_type"] == "question", "Expected more profile collection"
    print("  ✅ Profile parameters updated properly; Still collecting attributes.")

    # --------------------------------------------------------------------------
    # TURN 3: User provides income (Triggers complete profile)
    # --------------------------------------------------------------------------
    print("\n[Turn 3] Providing income (Annual 78,000)...")
    payload3 = {
        "message": "सालाना 78000 रुपये कमाती हूं, BPL कार्ड है, कोई पक्का मकान नहीं है",
        "session_id": session_id
    }
    resp3 = httpx.post(f"{BASE_URL}/chat", json=payload3, timeout=TIMEOUT)
    assert resp3.status_code == 200, "Turn 3 failed request"
    data3 = resp3.json()
    all_responses.append(data3)

    # Fetch profile to see what house_type was extracted
    profile_resp3 = httpx.get(f"{BASE_URL}/profile/{session_id}", timeout=TIMEOUT)
    profile3 = profile_resp3.json()
    with open("d:\\HACK05\\debug_profile_turn3.json", "w", encoding="utf-8") as f:
         json.dump(profile3, f, indent=2)

    assert data3["response_type"] == "schemes", "Turn 3 should trigger schemes search"
    assert data3.get("schemes_found") is not None
    print("  ✅ Profile completes; Schemes retrieved successfully.")

    # --------------------------------------------------------------------------
    # TURN 4: Schemes valuation (Off Turn 3 Response)
    # --------------------------------------------------------------------------
    print("\n[Turn 4] Evaluating scheme returns targets...")
    schemes = data3["schemes_found"]
    assert len(schemes) > 0, "No schemes found"

    scheme_names = [s["scheme_name"].lower() for s in schemes]
    # Check bounds
    has_kisan = any("kisan" in name for name in scheme_names)
    has_awas = any("awas" in name or "awaas" in name for name in scheme_names)
    has_ayushman = any("ayushman" in name for name in scheme_names)

    assert has_kisan, f"PM Kisan missing from results: {scheme_names}"
    assert has_awas, f"PM Awas missing from results: {scheme_names}"
    assert has_ayushman, f"Ayushman Bharat missing from results: {scheme_names}"

    for s in schemes:
        assert s["benefits_summary"], f"Scheme {s['scheme_name']} missing benefits description"
        assert s["eligibility_breakdown"], f"Scheme {s['scheme_name']} missing breakdown"
    print("  ✅ PM Kisan, PM Awas, and Ayushman Bharat successfully listed.")

    # --------------------------------------------------------------------------
    # TURN 5: User asks about housing scheme (PM Awas)
    # --------------------------------------------------------------------------
    print("\n[Turn 5] Inquiring specifics on housing scheme...")
    payload4 = {
        "message": "PM Awas Yojana के बारे में बताओ",
        "session_id": session_id
    }
    resp5 = httpx.post(f"{BASE_URL}/chat", json=payload4, timeout=TIMEOUT)
    assert resp5.status_code == 200, "Turn 5 failed request"
    data5 = resp5.json()
    all_responses.append(data5)

    assert_hindi(data5["message"], "Turn 5")
    # Verify accurate explanation containing required docs/steps
    mesg_lower = data5["message"].lower()

    # Search for documents list OR breakdown items
    is_explained = (" पात्रता " in data5["message"] or " eligibility " in mesg_lower or data5.get("schemes_found"))
    is_docs_listed = (" दस्तावेज " in data5["message"] or " documents " in mesg_lower or "आधार" in data5["message"])

    assert is_explained, "Response doesn't evaluate explanation limits bounds"
    assert is_docs_listed, "Response doesn't supply documents list correctly"
    print("  ✅ Housing scheme detailed safely including document triggers.")

    # --------------------------------------------------------------------------
    # TURN 6: User asks how to apply
    # --------------------------------------------------------------------------
    print("\n[Turn 6] Inquiring application processes guidelines...")
    payload5 = {
        "message": "मैं कैसे apply करूं?",
        "session_id": session_id
    }
    resp6 = httpx.post(f"{BASE_URL}/chat", json=payload5, timeout=TIMEOUT)
    assert resp6.status_code == 200, "Turn 6 failed request"
    data6 = resp6.json()
    all_responses.append(data6)

    assert_hindi(data6["message"], "Turn 6")
    msg = data6["message"].lower()

    # Check for steps references
    has_steps = ("चरण" in msg or "तरीका" in msg or "step" in msg)
    has_office = ("csc" in msg or "केंद्र" in msg or "ग्राम पंचायत" in msg or "panchayat" in msg)

    assert has_steps, "Response doesn't provide guideline directions"
    assert has_office, "Response misses offline centers references (CSC/Panchayat)"
    print("  ✅ Application steps provided incorporating CSC/Panchayat.")

    # --------------------------------------------------------------------------
    # FULL FLOW ASSERTIONS
    # --------------------------------------------------------------------------
    print("\n[Summary] Verifying full flow diagnostics...")
    assert len(all_responses) == 5, f"Expected 5 interaction turns, got {len(all_responses)}"
    for r in all_responses:
         # No "I don't know" or "क्षमा करें" fallback loops
         fallback_terms = ["pata nahi", "don't know", "sorry", "kshema", "नहीं जानता"]
         for term in fallback_terms:
              assert term not in r["message"].lower(), f"Unexpected fallback reply: {r['message']}"

    print("\nDemo story test: PASSED ✅")

if __name__ == "__main__":
    try:
        simulate_demo()
    except AssertionError as e:
        print(f"\nDemo story test: FAILED ❌\nReason: {e}")
        sys.exit(1)
    except Exception as e:
         print(f"\nDemo story test: ERROR ⚠️\nReason: {e}")
         sys.exit(1)
