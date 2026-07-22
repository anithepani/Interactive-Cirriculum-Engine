import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ice_api.models import ResourceNode
import os

async def seed():
    url = os.environ.get("DATABASE_URL")
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    nodes = [
        ResourceNode(
            id="rec_1",
            title="Python Data Structures Basics",
            url="https://docs.python.org/3/tutorial/datastructures.html",
            tags=["python", "basics"],
            is_foundational=True
        ),
        ResourceNode(
            id="rec_2",
            title="Introduction to React Hooks",
            url="https://react.dev/reference/react",
            tags=["react", "ui", "basics"],
            is_foundational=True
        ),
        ResourceNode(
            id="rec_3",
            title="System Design Fundamentals",
            url="https://github.com/donnemartin/system-design-primer",
            tags=["architecture", "design"],
            is_foundational=True
        )
    ]
    
    async with async_session() as session:
        # Check if already seeded
        for node in nodes:
            await session.merge(node)
        await session.commit()
    
    print("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed())
