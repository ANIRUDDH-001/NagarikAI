"""
Pydantic v2 Data Models — Phase 5
Every data shape flowing through the agent, API, and database.
Strong types prevent bugs. Every API request/response uses these.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


# ---- Valid Indian States ----

INDIAN_STATES = [
    "andhra_pradesh", "arunachal_pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal_pradesh", "jharkhand", "karnataka",
    "kerala", "madhya_pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim",
    "tamil_nadu", "telangana", "tripura", "uttar_pradesh", "uttarakhand",
    "west_bengal", "delhi", "jammu_kashmir", "ladakh", "chandigarh",
    "puducherry", "andaman_nicobar", "dadra_nagar_haveli", "lakshadweep",
    "national",
]


class ResponseType(str, Enum):
    """Type of response the agent returns to the frontend."""
    ANSWER = "answer"
    QUESTION = "question"
    SCHEMES = "schemes"
    ERROR = "error"


# ---- 1. UserProfile ----

class UserProfile(BaseModel):
    """
    Matches the Supabase user_profiles table exactly.
    Created incrementally from conversational extraction.
    """
    session_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    category: Optional[str] = None
    annual_income: Optional[int] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None
    is_bpl: bool = False
    has_disability: bool = False
    owns_land: bool = False
    house_type: Optional[str] = None
    education_level: Optional[str] = None
    has_bank_account: bool = False
    language_pref: str = "en"

    @field_validator("age")
    @classmethod
    def age_in_range(cls, v):
        if v is not None and not 1 <= v <= 120:
            raise ValueError("Age must be between 1 and 120")
        return v

    @field_validator("annual_income")
    @classmethod
    def income_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Annual income must be positive")
        return v

    @field_validator("state")
    @classmethod
    def state_valid(cls, v):
        if v is not None and v.lower().replace(" ", "_") not in INDIAN_STATES:
            # Be lenient — normalize
            return v.lower().replace(" ", "_")
        return v.lower().replace(" ", "_") if v else v

    @field_validator("category")
    @classmethod
    def category_valid(cls, v):
        valid = {"SC", "ST", "OBC", "General", "EWS"}
        if v is not None and v not in valid:
            raise ValueError(f"Category must be one of {valid}")
        return v


# ---- 2. ChatMessage ----

class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---- 3. ChatRequest ----

class ChatRequest(BaseModel):
    """What the frontend sends to the /chat endpoint."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1)
    language: str = "en"


# ---- 4. SchemeMatch ----

class SchemeMatch(BaseModel):
    """One matched scheme returned to the user with eligibility breakdown."""
    scheme_name: str
    ministry: Optional[str] = None
    state: Optional[str] = None
    benefits_summary: Optional[str] = None
    eligibility_summary: Optional[str] = None
    match_score: float = Field(ge=0, le=1, default=0.0)
    eligibility_breakdown: dict = Field(default_factory=dict)
    documents_needed: list[str] = Field(default_factory=list)
    application_url: Optional[str] = None


# ---- 5. ChatResponse ----

class ChatResponse(BaseModel):
    """What the API returns to the frontend."""
    message: str
    session_id: str
    schemes_found: Optional[list[SchemeMatch]] = None
    response_type: ResponseType = ResponseType.ANSWER
    language: str = "en"


# ---- 6. AgentState ----

class AgentState(BaseModel):
    """
    The complete state object flowing through LangGraph nodes.
    Each node reads this, modifies it, and passes it along.
    """
    messages: list[ChatMessage] = Field(default_factory=list)
    user_profile: Optional[UserProfile] = None
    profile_complete: bool = False
    schemes_found: list[SchemeMatch] = Field(default_factory=list)
    current_tool: Optional[str] = None
    error: Optional[str] = None
