"""
Database seeding script.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.user import User
from app.models.space import Space
from app.models.post import Post


async def seed_database():
    """Seed the database with initial data."""
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create demo users
        users = [
            User(
                email="alice@example.com",
                hashed_password=get_password_hash("password123"),
                name="Alice Johnson",
                handle="@alice",
                bio="Tech enthusiast and writer",
                is_verified=True
            ),
            User(
                email="bob@example.com",
                hashed_password=get_password_hash("password123"),
                name="Bob Smith",
                handle="@bob",
                bio="Developer and open source contributor"
            ),
            User(
                email="charlie@example.com",
                hashed_password=get_password_hash("password123"),
                name="Charlie Brown",
                handle="@charlie",
                bio="UX designer with a passion for accessibility"
            )
        ]
        
        for user in users:
            session.add(user)
        await session.commit()
        
        for user in users:
            await session.refresh(user)
        
        print(f"Created {len(users)} users")
        
        # Create spaces
        spaces = [
            Space(
                title="Technology",
                description="Discussions about the latest in tech",
                tags=["tech", "ai"],
                host_id=users[0].id,
            ),
            Space(
                title="Design",
                description="UI/UX, graphic design, and visual arts",
                tags=["design", "ux"],
                host_id=users[2].id,
            ),
            Space(
                title="AI & ML",
                description="Artificial Intelligence and Machine Learning",
                tags=["ai", "ml"],
                host_id=users[1].id,
            )
        ]
        
        for space in spaces:
            session.add(space)
        await session.commit()
        
        for space in spaces:
            await session.refresh(space)
        
        print(f"Created {len(spaces)} spaces")
        
        # Create sample posts
        posts = [
            Post(
                content="Just discovered an amazing new AI tool that helps with code reviews. The context-aware suggestions are incredibly accurate!",
                author_id=users[0].id,
                context_profile={
                    "intent": "Share discovery",
                    "tone": "Excited",
                    "assumptions": "Readers are developers",
                    "audience": "Tech community",
                    "core_argument": "AI tools are improving developer productivity"
                }
            ),
            Post(
                content="Accessibility in design isn't just a nice-to-have—it's essential. Every pixel we push should consider users of all abilities.",
                author_id=users[2].id,
                context_profile={
                    "intent": "Advocate for accessibility",
                    "tone": "Passionate",
                    "assumptions": "Some designers overlook accessibility",
                    "audience": "Designers and developers",
                    "core_argument": "Accessibility should be a priority"
                }
            ),
            Post(
                content="The future of web development is server-first. With RSC and streaming, we're finally getting the best of both worlds.",
                author_id=users[1].id,
                context_profile={
                    "intent": "Share opinion on web dev trends",
                    "tone": "Analytical",
                    "assumptions": "Reader knows about RSC",
                    "audience": "Frontend developers",
                    "core_argument": "Server-first is the future"
                }
            )
        ]
        
        for post in posts:
            session.add(post)
        await session.commit()
        
        print(f"Created {len(posts)} posts")
        
        print("\n✅ Database seeded successfully!")
        print("\nDemo accounts:")
        print("  - alice@example.com / password123")
        print("  - bob@example.com / password123")
        print("  - charlie@example.com / password123")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
