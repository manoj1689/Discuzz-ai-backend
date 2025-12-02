"""
API v1 router that combines all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    posts,
    comments,
    notifications,
    spaces,
    ai,
    search
)


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(posts.router)
api_router.include_router(comments.router)
api_router.include_router(notifications.router)
api_router.include_router(spaces.router)
api_router.include_router(ai.router)
api_router.include_router(search.router)
