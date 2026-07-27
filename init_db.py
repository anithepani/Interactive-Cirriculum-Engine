import asyncio, os, sys
repo_root = os.path.dirname(__file__)
sys.path.append(os.path.join(repo_root, "libs", "shared", "src"))
sys.path.append(os.path.join(repo_root, "apps", "api", "src"))

from sqlalchemy.ext.asyncio import create_async_engine
from ice_api.models import Base
from sqlalchemy import text

async def init_db():
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
