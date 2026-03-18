from langchain_groq import ChatGroq
from app.core.config import settings, master_config

def get_llm():
    """
    Returns an initialized LangChain ChatGroq instance
    using configurations from the master_config.json
    """
    model_name = master_config["groq"]["model"]
    max_tokens = master_config["groq"]["max_tokens"]
    temperature = master_config["groq"]["temperature"]
    
    # settings.GROQ_API_KEY is validated at startup
    llm = ChatGroq(
        groq_api_key=settings.GROQ_API_KEY,
        model_name=model_name,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return llm

# Global LLM instance intended for the agents
chat_llm = get_llm()
