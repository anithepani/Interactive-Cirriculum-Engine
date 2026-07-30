from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import google.generativeai as genai
import os
import uuid

from ice_api.deps import get_db, get_current_user
from ice_api.models import Curriculum, User, Checkpoint
from sqlalchemy import func

router = APIRouter(prefix="/api/v1/curricula", tags=["tutor"])

class TutorRequest(BaseModel):
    message: str
    video_time: float
    chat_history: List[dict] = []  # [{"role": "user", "content": "..."}, ...]

class TutorResponse(BaseModel):
    response: str

@router.post("/{id}/tutor", response_model=TutorResponse)
async def ask_tutor(
    request: TutorRequest,
    id: uuid.UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch curriculum and its transcript
    result = await session.execute(select(Curriculum).where(Curriculum.id == id, Curriculum.user_id == current_user.id))
    curriculum = result.scalar_one_or_none()
    
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")
        
    # Extract transcript context (find chunks around video_time)
    context_text = "No transcript available."
    
    # Fetch transcript from S3
    from ice_shared.s3 import get_s3_client
    from ice_shared import settings
    import json

    try:
        s3_key = f"tenants/{curriculum.tenant_id}/curricula/{id}/transcript.json"
        s3 = get_s3_client()
        response = s3.get_object(Bucket=settings.s3.bucket, Key=s3_key)
        transcript = json.loads(response['Body'].read().decode('utf-8'))
        
        segments = transcript.get("segments", [])
        if not segments and isinstance(transcript, list):
            segments = transcript
            
        # Find elements around the time
        relevant_chunks = []
        for chunk in segments:
            start = chunk.get("start", 0)
            end = chunk.get("end", 0)
            # within 30 seconds before and 30 seconds after
            if request.video_time - 30 <= start <= request.video_time + 30 or start <= request.video_time <= end:
                relevant_chunks.append(chunk.get("text", ""))
        
        if relevant_chunks:
            context_text = " ".join(relevant_chunks)
    except Exception as e:
        print(f"Failed to fetch transcript for curriculum {id}: {e}")

    # Fetch number of checkpoints
    cp_result = await session.execute(select(func.count(Checkpoint.id)).where(Checkpoint.curriculum_id == id))
    checkpoint_count = cp_result.scalar_one_or_none() or 0

    # Configure Gemini
    target_model = "gemini-3.5-flash"
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"), transport="rest")
        available_models = [
            m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods
        ]
        for m in ["models/gemini-3.5-flash", "models/gemini-3.1-pro-preview", "models/gemini-flash-latest"]:
            if m in available_models:
                target_model = m.replace("models/", "")
                break
        if target_model == "gemini-3.5-flash" and available_models and "models/gemini-3.5-flash" not in available_models:
            target_model = available_models[0].replace("models/", "")
    except Exception as e:
        print(f"Warning: Failed to list models: {e}")
        # fallback to a known good model if list_models fails
        target_model = "gemini-3.5-flash"
    
    system_prompt = f"""
You are the ICE Socratic AI Tutor, a world-class, highly charismatic, and insightful mentor. You are watching a video alongside the user at timestamp {request.video_time}s.

Video Title: {curriculum.title}
Total Interactive Exercises/Checkpoints in this video: {checkpoint_count}

Here is what is currently happening in the video around the {request.video_time}s mark:
{context_text}

CRITICAL RULES:
1. Directly and accurately address the user's specific question or request FIRST. If they ask for a summary, provide a concise summary. If they ask for an explanation, explain it clearly. Do not dodge their question.
2. If the user says they don't know, are stuck, or explicitly ask for the answer, DO NOT deflect with another hard question. Gently explain the concept to them in a clear, supportive way, and then ask a simpler guiding question to check their understanding.
3. Never use the word "transcript" or phrases like "Based on the video...". Speak as if you are organically experiencing the content together right now.
4. While answering their question, point out something subtle, fascinating, or deeply insightful about the current moment.
5. After answering their question (or explaining if they are stuck), end with a single, highly engaging Socratic question that makes the user pause and think critically about the underlying concepts, psychology, or themes.
6. Be EXTREMELY concise and punchy. Your entire response must be a maximum of 2 to 4 short sentences. Cut out any fluff and get straight to the point, while keeping it warm and encouraging.
"""
    
    # We will use Gemini to generate the response
    try:
        model = genai.GenerativeModel(target_model, system_instruction=system_prompt)
        
        # Convert history format to Gemini format
        formatted_history = []
        for msg in request.chat_history:
            role = "user" if msg.get("role") == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg.get("content", "")]})
            
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(request.message)
        
        return {"response": response.text}
    except Exception as e:
        import traceback
        with open("/tmp/tutor_error.log", "w") as f:
            f.write(traceback.format_exc())
        print(f"Error in ask_tutor: {e}")
        raise HTTPException(status_code=500, detail=str(e))
