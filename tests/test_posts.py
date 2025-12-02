"""
Tests for post endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, auth_headers):
    """Test creating a post."""
    response = await client.post(
        "/api/v1/posts",
        headers=auth_headers,
        json={
            "content": "This is a test post content.",
            "delegate_enabled": True,
            "is_published": True,
            "context_profile": {
                "intent": "To share knowledge",
                "tone": "Informative",
                "assumptions": "Reader has basic understanding",
                "audience": "Developers",
                "core_argument": "Testing is important"
            }
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "This is a test post content."
    assert data["delegate_enabled"] == True


@pytest.mark.asyncio
async def test_get_posts(client: AsyncClient):
    """Test getting posts list."""
    response = await client.get("/api/v1/posts")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_post_unauthorized(client: AsyncClient):
    """Test creating post without authentication."""
    response = await client.post(
        "/api/v1/posts",
        json={"content": "Test content"}
    )
    
    assert response.status_code == 401
