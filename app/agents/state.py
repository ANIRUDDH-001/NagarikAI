from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State dictionary that gets passed around the LangGraph nodes.
    Tracks messages, scheme context, and user demographic flags.
    """
    # Using operator.add to auto-append new messages to the list
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Context extracted from RAG (the schemes themselves)
    scheme_context: list[str]
    
    # Identified user traits from chat (e.g., student, farmer, widow)
    user_profile: dict
    
    # Target translation language if needed (e.g., 'hi-IN')
    target_language: str | None
