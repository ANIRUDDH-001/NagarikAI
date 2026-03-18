from fastapi import HTTPException, status
from typing import AsyncGenerator

async def get_db_session() -> AsyncGenerator:
    """
    Dependency injection for database sessions.
    This will yield a Supabase client or a raw asyncpg connection for pgvector.
    Using Depends(get_db_session) in routes guarantees proper cleanup.
    """
    try:
        # Placeholder for real DB session creation
        session = "supabase_client_placeholder"
        yield session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection error: {str(e)}"
        )
