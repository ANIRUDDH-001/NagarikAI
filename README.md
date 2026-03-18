# CSIHACK05 Backend 🚀

This is the robust backend structure for the CSIHACK05 government schemes discovery platform, designed to serve a Next.js 14 frontend.

## 🏗️ Architecture

- **Framework**: Python + FastAPI for asynchronous and high-performance API serving.
- **AI & Reasoning**: LangGraph for stateful multi-agent workflows, LangChain for RAG pipelines.
- **LLM & STT**: Groq API (Mixtral 8x7B for text, Whisper large-v3 for Speech-to-Text).
- **TTS & Translation**: Sarvam TTS, Sarvam Mayura API for native Indian language translation.
- **Embeddings**: HuggingFace (`sentence-transformers`).
- **Database**: Supabase (PostgreSQL with `pgvector` for semantic search).

## 📂 Folder Structure

- `/app/api`: FastAPI routes and dependency injection.
- `/app/agents`: LangGraph state definitions and multi-agent routing.
- `/app/core`: Application lifespan, configurations, Supabase DB initialization.
- `/app/ingestion`: RAG pipeline (chunking, creating embeddings, pushing to vector DB).
- `/app/scrapers`: Scripts to extract data from government portals.
- `/app/services`: External API wrappers (Groq, Sarvam, HuggingFace).
- `/app/utils`: Shared helpers.
- `/tests`: Pytest suite.

## ⚙️ Getting Started

1. **Clone & Setup Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Copy `.env.example` to `.env` and fill in your keys (Supabase, Groq, Sarvam, HuggingFace).

3. **Run the server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

4. **API Documentation**
   Once running, access the Swagger UI at `http://localhost:8000/docs`.
