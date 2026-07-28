import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ice_api.models import ResourceNode
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv("../../.env")

async def seed():
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Default to the local docker postgres
        url = "postgresql+asyncpg://postgres:postgres@localhost:5432/ice"
        
    engine = create_async_engine(url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    nodes_data = [
        {
            "id": "rec_1",
            "title": "Python Data Structures Basics",
            "url": "https://docs.python.org/3/tutorial/datastructures.html",
            "tags": ["python", "basics", "programming"],
            "is_foundational": True
        },
        {
            "id": "rec_2",
            "title": "Introduction to React Hooks",
            "url": "https://react.dev/reference/react",
            "tags": ["react", "ui", "basics", "programming"],
            "is_foundational": True
        },
        {
            "id": "rec_3",
            "title": "System Design Fundamentals",
            "url": "https://github.com/donnemartin/system-design-primer",
            "tags": ["architecture", "design", "programming"],
            "is_foundational": True
        },
        {
            "id": "rec_4",
            "title": "Advanced C++ Memory Management",
            "url": "https://isocpp.org/wiki/faq/freestore-mgmt",
            "tags": ["c++", "cpp", "memory", "programming"],
            "is_foundational": False
        },
        {
            "id": "rec_5",
            "title": "Machine Learning Crash Course",
            "url": "https://developers.google.com/machine-learning/crash-course",
            "tags": ["ai", "machine learning", "ml", "data"],
            "is_foundational": True
        },
        {
            "id": "rec_6",
            "title": "Understanding UX Principles",
            "url": "https://lawsofux.com/",
            "tags": ["design", "ux", "ui"],
            "is_foundational": True
        },
        {
            "id": "rec_7",
            "title": "Startup Finance 101",
            "url": "https://www.ycombinator.com/library/4D-startup-finance-for-founders",
            "tags": ["business", "finance", "startup"],
            "is_foundational": False
        },
        {
            "id": "rec_8",
            "title": "Deep Learning Specialization",
            "url": "https://www.coursera.org/specializations/deep-learning",
            "tags": ["ai", "deep learning", "neural networks"],
            "is_foundational": False
        }
    ]
    
    import random
    nodes = []
    for data in nodes_data:
        # Generate random 768d vector
        vector = [random.random() for _ in range(768)]
        
        nodes.append(ResourceNode(
            id=data["id"],
            title=data["title"],
            url=data["url"],
            tags=data["tags"],
            is_foundational=data["is_foundational"],
            vector_embedding=vector
        ))
        print(f"Generated embedding for: {data['title']}")

    async with async_session() as session:
        for node in nodes:
            await session.merge(node)
        await session.commit()
    
    print("Seed complete!")

if __name__ == "__main__":
    asyncio.run(seed())
