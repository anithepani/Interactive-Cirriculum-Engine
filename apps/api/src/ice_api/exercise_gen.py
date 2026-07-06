from __future__ import annotations
import json
import os
from typing import Dict, Any, List, Optional
import httpx

from ice_shared.settings import settings
from sqlalchemy import text
from ice_shared.db import async_session

GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def generate_exercise(segment_text: str, exercise_type: str, start_time: float, end_time: float) -> Dict[str, Any] | None:
    """
    Call Groq API to generate an exercise based on the segment text.
    """
    try:
        # Prompt templates for different exercise types
        if exercise_type == "mcq":
            prompt = f"""
You are an expert programming teacher. Based on the following tutorial segment (from {start_time:.1f}s to {end_time:.1f}s), generate a multiple-choice question that tests understanding of the concept.

Segment text:
\"{segment_text}\"

Generate a JSON response with:
- "question": the question text
- "options": an array of 4 options (strings)
- "answer_index": the index (0-3) of the correct option

Example:
{{
    "question": "What is the correct way to define a function in Python?",
    "options": ["def my_function():", "function my_function():", "define my_function():", "func my_function():"],
    "answer_index": 0
}}
"""
        elif exercise_type == "conceptual":
            prompt = f"""
You are an expert programming teacher. Based on the following tutorial segment (from {start_time:.1f}s to {end_time:.1f}s), generate a conceptual question that tests understanding of the concept.

Segment text:
\"{segment_text}\"

Generate a JSON response with:
- "question": the conceptual question
- "reference_answer": a clear, concise answer

Example:
{{
    "question": "Why is it important to use type annotations in Python?",
    "reference_answer": "Type annotations help with code clarity, enable static type checking, and improve IDE support for autocompletion and error detection."
}}
"""
        else:
            # For coding/debug – keep it simple for now
            prompt = f"""
You are an expert programming teacher. Based on the following tutorial segment (from {start_time:.1f}s to {end_time:.1f}s), generate a coding challenge.

Segment text:
\"{segment_text}\"

Generate a JSON response with:
- "question": the coding problem statement
- "starter_code": a code template to start with (optional)
- "solution": the reference solution

Example:
{{
    "question": "Write a function that calculates the factorial of a number using recursion.",
    "starter_code": "def factorial(n):\\n    # Your code here",
    "solution": "def factorial(n):\\n    if n <= 1:\\n        return 1\\n    return n * factorial(n-1)"
}}
"""

        # Call Groq API with a SUPPORTED model
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-8b-instant",  # Fastest, lowest latency, confirmed working
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that generates educational exercises. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                }
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                exercise_data = json.loads(content)
                return exercise_data
            else:
                print(f"⚠️  Groq API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"⚠️  Exercise generation failed: {e}")
        return None


async def generate_exercises_for_curriculum(curriculum_id: int):
    """
    Generate exercises for all checkpoints of a curriculum.
    """
    print(f"📝 Generating exercises for curriculum {curriculum_id}...")
    
    async with async_session() as session:
        # Get all segments and checkpoints
        segments_result = await session.execute(
            text("SELECT id, title, summary, start_time, end_time FROM segments WHERE curriculum_id = :cid"),
            {"cid": curriculum_id}
        )
        segments = segments_result.fetchall()
        
        checkpoints_result = await session.execute(
            text("SELECT id, segment_id, exercise_type, difficulty FROM checkpoints WHERE curriculum_id = :cid"),
            {"cid": curriculum_id}
        )
        checkpoints = checkpoints_result.fetchall()
        
        # Map segment_id -> segment data
        segment_map = {seg.id: seg for seg in segments}
        
        for cp in checkpoints:
            seg = segment_map.get(cp.segment_id)
            if not seg:
                print(f"⚠️  No segment found for checkpoint {cp.id}")
                continue
            
            # Generate exercise based on the segment's summary
            exercise_payload = await generate_exercise(
                segment_text=seg.summary or seg.title or "",
                exercise_type=cp.exercise_type,
                start_time=seg.start_time,
                end_time=seg.end_time,
            )
            
            if exercise_payload:
                # Extract question/prompt from payload
                prompt_text = exercise_payload.get("question") or exercise_payload.get("prompt", "")
                answer_text = str(exercise_payload.get("answer_index", "")) if "answer_index" in exercise_payload else exercise_payload.get("reference_answer", "")
                
                # Insert exercise into database – include all required columns
                await session.execute(
                    text("""
                        INSERT INTO exercises 
                        (curriculum_id, checkpoint_id, type, exercise_type, prompt, answer, difficulty, payload, confidence, validation_passed)
                        VALUES (:curriculum_id, :cp_id, :type, :exercise_type, :prompt, :answer, :difficulty, :payload, :confidence, :validation_passed)
                    """),
                    {
                        "curriculum_id": curriculum_id,
                        "cp_id": cp.id,
                        "type": cp.exercise_type,
                        "exercise_type": cp.exercise_type,
                        "prompt": prompt_text,
                        "answer": answer_text,
                        "difficulty": cp.difficulty or 3,
                        "payload": json.dumps(exercise_payload),
                        "confidence": 0.8,
                        "validation_passed": True,
                    }
                )
                print(f"✅ Exercise generated for checkpoint {cp.id}")
            else:
                print(f"⚠️  Failed to generate exercise for checkpoint {cp.id}")
        
        await session.commit()
        print(f"✅ Exercise generation complete for curriculum {curriculum_id}")