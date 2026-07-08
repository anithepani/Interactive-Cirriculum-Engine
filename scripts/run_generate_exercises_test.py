import asyncio

from ice_api.exercise_gen import generate_exercises_for_curriculum

async def main():
    # Use curriculum ID 1 for testing — change as needed
    await generate_exercises_for_curriculum(1)

if __name__ == '__main__':
    asyncio.run(main())
