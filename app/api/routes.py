from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any
from app.api.dependencies import get_db_session

# Create the main API router
router = APIRouter()

# Simple request model for chat queries
class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest) -> Any:
    """
    Main chat endpoint where the user sends a query to the LangGraph agents.
    Forwards user input to the AI conversational pipeline.
    """
    return {"response": "LangGraph response placeholder", "echo": request.query}

@router.get("/schemes")
async def get_schemes(db=Depends(get_db_session)) -> Any:
    """
    Retrieve a list of filtered government schemes from Supabase.
    Currently a placeholder until db logic is wired up.
    """
    return {"schemes": [], "db_status": "injected"}
