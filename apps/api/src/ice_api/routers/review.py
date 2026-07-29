from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from ice_shared.db import get_session
from ..deps import get_current_user
from ..models import User, SkillModel, Concept, Checkpoint, Exercise, Curriculum
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/review", tags=["review"])

class GradeReviewRequest(BaseModel):
    concept_id: str
    grade: int  # 0 to 5

@router.get("/due")
async def get_due_reviews(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Fetch all concepts due for review for the current user, along with a practice exercise."""
    today = date.today()
    
    # Due if next_review_date is null (never reviewed) OR next_review_date <= today
    stmt = (
        select(SkillModel, Concept)
        .join(Concept, SkillModel.concept_id == Concept.id)
        .where(
            SkillModel.user_id == current_user.id,
            or_(
                SkillModel.next_review_date == None,
                SkillModel.next_review_date <= datetime.now()
            )
        )
        .limit(20) # Limit to 20 flashcards per session
    )
    
    result = await session.execute(stmt)
    rows = result.all()
    
    cards = []
    for sm, concept in rows:
        # Fetch an exercise for this concept
        ex_stmt = (
            select(Exercise)
            .join(Checkpoint, Exercise.checkpoint_id == Checkpoint.id)
            .where(Checkpoint.concept_id == concept.id)
            .limit(1)
        )
        ex_res = await session.execute(ex_stmt)
        exercise = ex_res.scalar_one_or_none()
        
        cards.append({
            "concept_id": concept.id,
            "label": concept.label,
            "description": concept.description,
            "difficulty": concept.difficulty,
            "category": concept.category,
            "review_format": concept.review_format.value if concept.review_format else None,
            "review_payload": concept.review_payload,
            "srs_interval": sm.srs_interval,
            "next_review_date": sm.next_review_date.isoformat() if sm.next_review_date else None,
            "exercise": {
                "id": exercise.id,
                "type": exercise.type,
                "payload": exercise.payload
            } if exercise else None
        })
        
    return cards

@router.post("/grade")
async def grade_review(
    payload: GradeReviewRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Apply the SuperMemo-2 algorithm based on the user's grade (0-5)."""
    grade = payload.grade
    if grade < 0 or grade > 5:
        raise HTTPException(status_code=400, detail="Grade must be between 0 and 5")
        
    stmt = select(SkillModel).where(
        SkillModel.user_id == current_user.id,
        SkillModel.concept_id == payload.concept_id
    )
    result = await session.execute(stmt)
    sm = result.scalar_one_or_none()
    
    if not sm:
        raise HTTPException(status_code=404, detail="Skill model not found for concept")
        
    # SuperMemo-2 Algorithm
    if grade >= 3:
        if sm.srs_interval == 0:
            sm.srs_interval = 1
        elif sm.srs_interval == 1:
            sm.srs_interval = 6
        else:
            sm.srs_interval = round(sm.srs_interval * sm.ease_factor)
    else:
        sm.srs_interval = 0
        
    sm.ease_factor = sm.ease_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    if sm.ease_factor < 1.3:
        sm.ease_factor = 1.3
        
    sm.next_review_date = datetime.now() + timedelta(days=sm.srs_interval)
    
    # Increase XP for doing flashcards!
    if grade >= 3:
        current_user.xp = (current_user.xp or 0) + 5
    
    await session.commit()
    
    return {
        "status": "ok",
        "next_review_date": sm.next_review_date.isoformat(),
        "srs_interval": sm.srs_interval,
        "ease_factor": sm.ease_factor,
        "xp": current_user.xp
    }

@router.get("/quiz")
async def get_random_quiz(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Generate a random quiz of 5 multiple choice exercises for the user's concepts."""
    # Select exercises belonging to the user's tenant/curricula
    stmt = (
        select(Exercise, Concept)
        .join(Checkpoint, Exercise.checkpoint_id == Checkpoint.id)
        .join(Concept, Checkpoint.concept_id == Concept.id)
        .join(Curriculum, Concept.curriculum_id == Curriculum.id)
        .where(
            Curriculum.tenant_id == current_user.tenant_id,
            Exercise.type == "multiple_choice"
        )
        .order_by(func.random())
        .limit(5)
    )
    result = await session.execute(stmt)
    rows = result.all()
    
    quiz = []
    for exercise, concept in rows:
        quiz.append({
            "id": exercise.id,
            "concept_label": concept.label,
            "type": exercise.type,
            "payload": exercise.payload
        })
        
    return quiz
