import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://ice:ice_dev_password@localhost:5432/ice')
    try:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255);')
        print('Added avatar_url')
    except Exception as e:
        print(e)
    
    try:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_count INTEGER DEFAULT 0;')
        print('Added streak_count')
    except Exception as e:
        print(e)

    try:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_color VARCHAR(50) DEFAULT \'emerald\';')
        print('Added streak_color')
    except Exception as e:
        print(e)

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
