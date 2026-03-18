import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def async_client():
    """
    Creates an async test client for hitting FastAPI endpoints in tests.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
