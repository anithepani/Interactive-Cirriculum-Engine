import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect('postgresql://ice:ice_dev_password@localhost:5432/ice')
    try:
        await conn.execute('ALTER TABLE curricula ADD COLUMN IF NOT EXISTS difficulty VARCHAR(50) DEFAULT \'medium\';')
        print('Added difficulty to curricula')
    except Exception as e:
        print(f'Error adding difficulty: {e}')
    
    try:
        await conn.execute('ALTER TABLE curricula ADD COLUMN IF NOT EXISTS duration INTEGER;')
        print('Added duration to curricula')
    except Exception as e:
        print(f'Error adding duration: {e}')
        
    try:
        await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER DEFAULT 1;')
        print('Added token_version to users')
    except Exception as e:
        print(f'Error adding token_version: {e}')

    try:
        await conn.execute("ALTER TABLE concepts ADD COLUMN IF NOT EXISTS category VARCHAR;")
        await conn.execute("ALTER TABLE concepts ADD COLUMN IF NOT EXISTS review_format VARCHAR;")
        await conn.execute("ALTER TABLE concepts ADD COLUMN IF NOT EXISTS review_payload JSONB;")
        print('Added category, review_format, and review_payload to concepts')
    except Exception as e:
        print(f'Error adding concept fields: {e}')

    await conn.close()
if __name__ == "__main__":
    asyncio.run(main())
