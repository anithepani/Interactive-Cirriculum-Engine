import asyncio
import json
from pathlib import Path
from datetime import datetime

from sqlalchemy import text
from ice_shared.db import async_session
from ice_api.process import process_video

TEST_CURRICULUM_ID = 41
TEST_AUDIO_FILE = Path("scripts/test_audio.wav")

async def query_exercises(curriculum_id: int, limit: int = 5):
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT id, checkpoint_id, type, payload FROM exercises WHERE curriculum_id = :cid ORDER BY id LIMIT :limit"
            ),
            {"cid": curriculum_id, "limit": limit},
        )
        rows = result.mappings().all()

    print(f"\nExercises for curriculum_id={curriculum_id} (first {limit} rows):")
    if not rows:
        print("  No exercises found.")
        return
    for row in rows:
        payload = row["payload"]
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                pass
        print(f"  id={row['id']} checkpoint_id={row['checkpoint_id']} type={row['type']} payload_keys={list(payload.keys()) if isinstance(payload, dict) else 'N/A'}")
        print(f"    payload snippet: {json.dumps(payload, indent=2) if isinstance(payload, dict) else payload}\n")

async def ensure_test_curriculum(curriculum_id: int):
    async with async_session() as session:
        result = await session.execute(text("SELECT id FROM curricula WHERE id = :cid"), {"cid": curriculum_id})
        exists = result.scalar_one_or_none()
        if exists:
            print(f"Found existing curriculum id={curriculum_id}. Clearing associated data.")
            await session.execute(text("DELETE FROM exercises WHERE curriculum_id = :cid"), {"cid": curriculum_id})
            await session.execute(text("DELETE FROM checkpoints WHERE curriculum_id = :cid"), {"cid": curriculum_id})
            await session.execute(text("DELETE FROM segments WHERE curriculum_id = :cid"), {"cid": curriculum_id})
            await session.execute(text("DELETE FROM concepts WHERE curriculum_id = :cid"), {"cid": curriculum_id})
            await session.execute(
                text(
                    "UPDATE curricula SET title = :title, source_ref = :source_ref, status = 'queued', ready_at = NULL WHERE id = :cid"
                ),
                {
                    "cid": curriculum_id,
                    "title": "Test Curriculum 41",
                    "source_ref": str(TEST_AUDIO_FILE),
                },
            )
            await session.commit()
        else:
            print(f"Creating new curriculum id={curriculum_id}.")
            await session.execute(
                text(
                    "INSERT INTO curricula (id, tenant_id, title, source_ref, status, created_at) VALUES (:id, :tenant_id, :title, :source_ref, 'queued', :created_at)"
                ),
                {
                    "id": curriculum_id,
                    "tenant_id": 1,
                    "title": "Test Curriculum 41",
                    "source_ref": str(TEST_AUDIO_FILE),
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            await session.commit()

async def main():
    if not TEST_AUDIO_FILE.exists():
        TEST_AUDIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEST_AUDIO_FILE.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
        print(f"Created dummy audio file at {TEST_AUDIO_FILE}")

    await ensure_test_curriculum(TEST_CURRICULUM_ID)
    print(f"Running process_video for curriculum {TEST_CURRICULUM_ID}...")
    await process_video(TEST_CURRICULUM_ID)
    await query_exercises(TEST_CURRICULUM_ID)

    print("\nVerifying existing curriculum 1 now:")
    await query_exercises(1)

if __name__ == '__main__':
    asyncio.run(main())
