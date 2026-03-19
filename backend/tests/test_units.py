"""
Unit Tests for FastAPI Backend — Phase 5
Tests: embedder, chunker, agent/tools, translator, schemas.
Uses pytest and unittest.mock to isolate external API dependencies (Supabase, Sarvam).
"""
import sys
import os
import base64
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

# Set up path so imports resolve correctly from backend/
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import modules under test
from pipeline.embedder import embed_text, embed_batch
from pipeline.chunker import chunk_scheme
from utils.translator import detect_language, translate_to_english, text_to_speech
from models.schemas import UserProfile, ChatRequest


# --------------------------------------------------------------------------
# 1. EMBEDDER TESTS
# --------------------------------------------------------------------------

def test_embed_text_returns_correct_length():
    """Verify that embedding output is exactly 384 floats."""
    vec = embed_text("PM Kisan scheme for farmers")
    assert isinstance(vec, list)
    assert len(vec) == 384


def test_embed_text_is_normalized():
    """Verify that vector magnitude is approximately 1.0 (L2 normalized)."""
    import numpy as np
    vec = embed_text("Ayushman Bharat")
    vec_np = np.array(vec)
    norm = np.linalg.norm(vec_np)
    assert abs(norm - 1.0) < 0.01


def test_embed_batch_consistent():
    """Verify same text embedded individually and in batch gives same result."""
    import numpy as np
    texts = ["PM Kisan", "Ayushman Bharat"]
    batch_vecs = embed_batch(texts)
    ind_vec1 = embed_text(texts[0])
    ind_vec2 = embed_text(texts[1])

    assert len(batch_vecs) == 2
    assert np.allclose(batch_vecs[0], ind_vec1, atol=1e-5)
    assert np.allclose(batch_vecs[1], ind_vec2, atol=1e-5)


# --------------------------------------------------------------------------
# 2. CHUNKER TESTS
# --------------------------------------------------------------------------

# Sample scheme structure matching what chunker expects
SAMPLE_SCHEME = {
    "scheme_id": "pm_kisan",
    "scheme_name": "PM Kisan Samman Nidhi",
    "state": "national",
    "tier": 1,
    "eligibility_text": "Small and marginal farmers.",
    "benefits_text": "₹6000 per year in 3 installments.",
    "structured_data": {
        "ministry": "Ministry of Agriculture",
        "benefits_summary": "Financial support to farmers",
        "eligibility_summary": "Landholding farmers",
        "age_min": 18,
        "age_max": 100,
        "income_limit_annual": None,
        "category": ["All"],
        "occupation": ["Farmer"],
        "bpl_required": False,
        "application_steps": ["1. Register online", "2. Verify KYC"],
        "documents_needed": ["Aadhaar", "Land Record"]
    }
}

def test_chunk_scheme_returns_four_types():
    """Verify that scheme produces overview, eligibility, benefits, process chunks."""
    chunks = chunk_scheme(SAMPLE_SCHEME)
    assert len(chunks) == 4
    types = [c["chunk_type"] for c in chunks]
    assert "overview" in types
    assert "eligibility" in types
    assert "benefits" in types
    assert "process" in types


def test_chunk_metadata_present():
    """Verify that every chunk has scheme_id and metadata dict."""
    chunks = chunk_scheme(SAMPLE_SCHEME)
    for c in chunks:
        assert "scheme_id" in c
        assert "metadata" in c
        assert isinstance(c["metadata"], dict)
        assert "state" in c["metadata"]


def test_chunk_text_not_empty():
    """Verify that no chunk has empty chunk_text."""
    chunks = chunk_scheme(SAMPLE_SCHEME)
    for c in chunks:
        assert c["chunk_text"]
        assert len(c["chunk_text"].strip()) > 0


def test_eligibility_chunk_contains_age():
    """Verify that if scheme has age bounds, eligibility chunk mentions it."""
    scheme = dict(SAMPLE_SCHEME)
    scheme["structured_data"] = dict(SAMPLE_SCHEME["structured_data"])
    scheme["structured_data"]["age_min"] = 18
    scheme["structured_data"]["age_max"] = 60

    chunks = chunk_scheme(scheme)
    elig_chunk = next(c for c in chunks if c["chunk_type"] == "eligibility")
    assert "between 18 and 60" in elig_chunk["chunk_text"]


# --------------------------------------------------------------------------
# 3. TOOLS TESTS (MOCK SUPABASE)
# --------------------------------------------------------------------------

@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client inside agent.tools."""
    with patch("agent.tools.supabase") as mock:
        yield mock


def test_search_schemes_returns_list(mock_supabase):
    """Verify that search_schemes returns a list."""
    # Mock RPC response
    mock_rpc = MagicMock()
    mock_supabase.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value.data = [
        {"scheme_id": "1", "similarity": 0.8, "chunk_text": "Sample summary"}
    ]

    # Mock Table response
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value.in_.return_value.execute.return_value.data = [
        {"id": "1", "scheme_name": "PM Kisan", "age_min": 18, "income_limit": 100000}
    ]

    from agent.tools import search_schemes
    user_profile = {"age": 45, "income": 78000, "state": "Bihar"}
    res = search_schemes(user_profile)
    assert isinstance(res, list)


def test_eligibility_breakdown_structure(mock_supabase):
    """Verify breakdown has 'passes' boolean for each field."""
    mock_rpc = MagicMock()
    mock_supabase.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value.data = [{"scheme_id": "1", "similarity": 0.8}]

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value.in_.return_value.execute.return_value.data = [
        {"id": "1", "scheme_name": "PM Kisan", "age_min": 18, "income_limit": 100000}
    ]

    from agent.tools import search_schemes
    user_profile = {"age": 45, "annual_income": 78000}
    res = search_schemes(user_profile)
    assert len(res) > 0
    breakdown = res[0]["eligibility_breakdown"]
    assert "income" in breakdown
    assert "passes" in breakdown["income"]


def test_income_filter_works(mock_supabase):
    """Verify that scheme with income limit excludes user with higher income."""
    mock_rpc = MagicMock()
    mock_supabase.rpc.return_value = mock_rpc
    mock_rpc.execute.return_value.data = [{"scheme_id": "1", "similarity": 0.8}]

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_table.select.return_value.in_.return_value.execute.return_value.data = [
        {"id": "1", "scheme_name": "Scheme A", "income_limit": 100000}
    ]

    from agent.tools import search_schemes
    # User with income > limit
    user_profile = {"age": 25, "annual_income": 200000}
    res = search_schemes(user_profile)
    assert len(res) > 0
    breakdown = res[0]["eligibility_breakdown"]
    assert breakdown["income"]["passes"] is False


# --------------------------------------------------------------------------
# 4. TRANSLATOR TESTS (MOCK SARVAM API)
# --------------------------------------------------------------------------

def test_detect_hindi_devanagari():
    """Verify that Devanagari script is detected as 'hi'."""
    assert detect_language("मैं किसान हूं") == "hi"


@patch("utils.translator.httpx.Client")
def test_translate_english_passthrough(mock_client):
    """Verify that English text returns unchanged without API call."""
    res = translate_to_english("Hello", source_lang="en")
    assert res == "Hello"
    mock_client.assert_not_called()


@patch("utils.translator.httpx.Client")
def test_tts_returns_bytes_or_none(mock_client):
    """Verify that text_to_speech returns bytes or handles failure."""
    mock_inst = MagicMock()
    mock_client.return_value.__enter__.return_value = mock_inst
    mock_resp = MagicMock()
    mock_inst.post.return_value = mock_resp

    # Success case
    mock_resp.json.return_value = {"audios": [base64.b64encode(b"dummy_audio").decode()]}
    mock_resp.raise_for_status.return_value = None

    res = text_to_speech("test text", language="hi")
    assert isinstance(res, bytes)

    # Failure case
    mock_inst.post.side_effect = Exception("API connection failed")
    res_fail = text_to_speech("test text", language="hi")
    assert res_fail is None


# --------------------------------------------------------------------------
# 5. SCHEMAS TESTS
# --------------------------------------------------------------------------

def test_user_profile_age_validation():
    """Verify age 150 raises ValidationError."""
    with pytest.raises(ValidationError):
        UserProfile(session_id="123", age=150)


def test_user_profile_income_validation():
    """Verify negative income raises ValidationError."""
    with pytest.raises(ValidationError):
        UserProfile(session_id="123", annual_income=-5000)


def test_chat_request_defaults():
    """Verify that language defaults to 'en' in ChatRequest."""
    req = ChatRequest(message="Hello", session_id="123")
    assert req.language == "en"
