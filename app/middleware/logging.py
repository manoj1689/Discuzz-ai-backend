"""
Request logging middleware.
"""

import time
import logging
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid4())
        
        # Add request ID to state
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        
        logger.info(
            f"Request started | "
            f"ID: {request_id} | "
            f"Method: {request.method} | "
            f"Path: {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed | "
            f"ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {duration:.3f}s"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
