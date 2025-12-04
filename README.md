# Discuzz.ai Backend API

Production-ready FastAPI backend with PostgreSQL database for the Discuzz.ai social platform.

## Features

- **Authentication & Authorization**: JWT-based authentication with refresh tokens
- **User Management**: Profile CRUD, follow/unfollow, interests
- **Posts & Context Profiles**: AI-powered context profile generation
- **Spaces**: Live audio space management
- **Notifications**: Real-time notification system
- **Comments**: Threaded comments with AI delegate responses
- **Security**: Rate limiting, CORS, input validation, SQL injection protection

## Tech Stack

- **FastAPI** - Modern async Python web framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM with async support
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Authentication tokens
- **Redis** - Caching and rate limiting (optional)
- **Google Gemini / OpenAI** - AI integrations

## Quick Start

\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (use async driver for SQLAlchemy)
# Example:
# DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/discuss_db"
# SECRET_KEY="your-long-random-secret"
# ENABLE_DOCS=true  # set to true to expose /docs and /redoc

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
\`\`\`

## Auth Configuration

- `GOOGLE_CLIENT_ID` - optional; used to validate Google ID tokens
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - optional; service account JSON used to validate Firebase-issued Google ID tokens
- `FIREBASE_PROJECT_ID` - optional override of project ID (otherwise taken from the service account JSON)

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

\`\`\`
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── posts.py
│   │   │   │   ├── comments.py
│   │   │   │   ├── notifications.py
│   │   │   │   ├── spaces.py
│   │   │   │   └── ai.py
│   │   │   └── router.py
│   │   └── deps.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── init_db.py
│   ├── models/
│   │   ├── user.py
│   │   ├── post.py
│   │   ├── comment.py
│   │   ├── notification.py
│   │   └── space.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── post.py
│   │   ├── comment.py
│   │   ├── notification.py
│   │   └── space.py
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── auth_service.py
│   │   └── notification_service.py
│   └── main.py
├── alembic/
├── tests/
├── requirements.txt
└── .env.example
# Discuzz-ai-backend
