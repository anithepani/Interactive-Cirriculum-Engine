import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, false, Integer

from ..deps import get_db, get_current_user
from ..models import User, UserSkillProfile, ConceptEdge, ResourceNode, UserInterestCentroid

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

class RecommendationCard(BaseModel):
    id: str
    title: str
    url: str
    tags: List[str]
    badge: str
    reason: str
    score: float

# Tuning parameters
ALPHA_REMEDIAL = 2.0
BETA_SIMILARITY = 1.0

@router.get("/feed", response_model=List[RecommendationCard])
async def get_recommendation_feed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch UserSkillProfile
    profile_result = await db.execute(
        select(UserSkillProfile).where(UserSkillProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    weak_concepts = profile.weak_concepts if profile and profile.weak_concepts else []
    
    # 2. Expand weak concepts via ConceptEdge
    expanded_weak = set(weak_concepts)
    if weak_concepts:
        # Find prerequisites for the weak concepts
        edges_result = await db.execute(
            select(ConceptEdge.source_concept_id)
            .where(ConceptEdge.target_concept_id.in_(weak_concepts))
            .where(ConceptEdge.relation == "prereq")
        )
        prereqs = edges_result.scalars().all()
        expanded_weak.update(prereqs)
        
    expanded_weak_list = list(expanded_weak)

    # 3. Fetch User Centroids
    centroids_result = await db.execute(
        select(UserInterestCentroid.vector_embedding)
        .where(UserInterestCentroid.user_id == current_user.id)
    )
    centroids = centroids_result.scalars().all()
    
    cards = []
    
    # 4. Construct Query
    if not centroids:
        # COLD START: No vectors. Beta = 0.
        # Score is purely Alpha (if tags match) + Foundational pad.
        
        # We need to query ResourceNodes
        query = select(ResourceNode)
        
        # If no weak concepts either, just return foundational
        if not expanded_weak_list:
            query = query.where(ResourceNode.is_foundational == True).limit(3)
            results = await db.execute(query)
            
            for rn in results.scalars().all():
                cards.append(RecommendationCard(
                    id=rn.id,
                    title=rn.title,
                    url=rn.url,
                    tags=rn.tags or [],
                    badge="Foundational",
                    reason="Hand-picked foundational content to get you started.",
                    score=1.0
                ))
            return cards
        
        # We have weak concepts, so we find matches first, and pad with foundational
        results = await db.execute(select(ResourceNode))
        nodes = results.scalars().all()
        
        scored_nodes = []
        for rn in nodes:
            tags = set(rn.tags or [])
            is_match = bool(tags.intersection(expanded_weak))
            score = (ALPHA_REMEDIAL if is_match else 0.0)
            if is_match or rn.is_foundational:
                scored_nodes.append((rn, score, is_match))
                
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        
        for rn, score, is_match in scored_nodes[:3]:
            badge = "High Priority Fix" if is_match else "Discovery"
            reason = "Based on your recent struggles." if is_match else "Foundational topic."
            cards.append(RecommendationCard(
                id=rn.id,
                title=rn.title,
                url=rn.url,
                tags=rn.tags or [],
                badge=badge,
                reason=reason,
                score=score
            ))
            
        return cards
        
    else:
        # WARM START: User has centroids. Compute max similarity + remedial boost.
        distance_exprs = []
        for vec in centroids:
            distance_exprs.append(ResourceNode.vector_embedding.cosine_distance(vec))
            
        min_distance = func.least(*distance_exprs)
        similarity = 1.0 - min_distance
        
        if expanded_weak_list:
            is_match_expr = ResourceNode.tags.overlap(expanded_weak_list)
            match_score = func.cast(is_match_expr, Integer) * ALPHA_REMEDIAL
        else:
            is_match_expr = false()
            match_score = 0.0
            
        total_score = (similarity * BETA_SIMILARITY) + match_score
        
        query = (
            select(ResourceNode, total_score.label("score"), is_match_expr.label("is_match"))
            .order_by(total_score.desc())
            .limit(3)
        )
        
        results = await db.execute(query)
        
        for row in results.all():
            rn = row.ResourceNode
            score = row.score
            is_match = row.is_match
            
            if is_match and (score - ALPHA_REMEDIAL) > 0.5:
                badge = "Next Step"
                reason = "Combines your interests with a core foundational fix."
            elif is_match:
                badge = "High Priority Fix"
                reason = "Recommended to strengthen your weak concepts."
            else:
                badge = "Discovery"
                reason = "Matches your historical learning interests."
                
            cards.append(RecommendationCard(
                id=rn.id,
                title=rn.title,
                url=rn.url,
                tags=rn.tags or [],
                badge=badge,
                reason=reason,
                score=score
            ))
            
        return cards
