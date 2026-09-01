"""Grow routes — business, investment, and skill endpoints."""

import json
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Child
from app.services.wallet_service import get_child_by_anonymous_id
from app.services.grow_service import (
    BUSINESS_TEMPLATES,
    SKILL_CARDS,
    INVESTMENT_SCENARIOS,
    get_templates_for_budget,
    start_business,
    invest,
    explore_skill,
)
from app.services.ai_provider import (
    INTEREST_OPTIONS,
    rank_templates,
)

router = APIRouter(prefix="/api/grow", tags=["grow"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BusinessTemplateResponse(BaseModel):
    id: str
    name: str
    min_budget: int
    cost: int
    expected_profit_min: int
    expected_profit_max: int
    skills: list[str]
    description: str
    affordable: bool


class RankedBusinessResponse(BaseModel):
    id: str
    name: str
    min_budget: int
    cost: int
    expected_profit_min: int
    expected_profit_max: int
    skills: list[str]
    description: str
    affordable: bool
    match_score: int
    pitch: str


class SkillCardResponse(BaseModel):
    id: str
    name: str
    icon: str
    why: str
    steps: str
    practice_question: str
    earning_potential: str
    category: str
    discover: str = ""
    challenge: dict = {}
    connect_text: str = ""
    linked_business_ids: list[str] = []
    optional_practice: str = ""


class GrowTemplatesResponse(BaseModel):
    business: list[BusinessTemplateResponse]
    skills: list[SkillCardResponse]
    investment_options: list[dict]
    interest_options: list[dict]


class RecommendRequest(BaseModel):
    anonymous_id: str
    interests: list[str]


class RecommendResponse(BaseModel):
    business: list[RankedBusinessResponse]
    message: str


class BusinessRequest(BaseModel):
    anonymous_id: str
    template_id: str = Field(..., min_length=1)


class BusinessResultResponse(BaseModel):
    wallet_balance: Decimal
    idea: str
    cost: Decimal
    actual_revenue: Decimal
    actual_profit: Decimal
    expected_profit_min: Decimal
    expected_profit_max: Decimal
    skills: list[str]
    description: str
    message: str
    disclaimer: str


class InvestRequest(BaseModel):
    anonymous_id: str
    amount: float = Field(..., gt=0)
    risk_level: str = Field(..., min_length=1)


class InvestResultResponse(BaseModel):
    wallet_balance: Decimal
    invested_amount: Decimal
    risk_level: str
    risk_name: str
    return_percentage: float
    outcome_amount: Decimal
    profit_loss: Decimal
    is_profit: bool
    risk_message: str
    disclaimer: str
    message: str


class SkillRequest(BaseModel):
    anonymous_id: str
    skill_id: str = Field(..., min_length=1)
    practice_answer: str | None = None
    challenge_answer: str | None = None
    practice_text: str | None = None


class SkillResultResponse(BaseModel):
    skill_name: str
    icon: str
    why: str
    steps: str
    practice_question: str
    earning_potential: str
    category: str
    message: str
    is_correct: bool | None = None
    explanation: str = ""
    connect_text: str = ""
    linked_business_ids: list[str] = []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/templates/{anonymous_id}", response_model=GrowTemplatesResponse)
def get_grow_templates(anonymous_id: str, db: Session = Depends(get_db)):
    """Return business templates (filtered by budget) + skill cards + interest options."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    balance = child.wallet.balance

    templates = get_templates_for_budget(balance)

    business_list = [
        BusinessTemplateResponse(
            id=t["id"],
            name=t["name"],
            min_budget=t["min_budget"],
            cost=t["cost"],
            expected_profit_min=t["expected_profit_min"],
            expected_profit_max=t["expected_profit_max"],
            skills=t["skills"],
            description=t["description"],
            affordable=Decimal(str(t["cost"])) <= balance,
        )
        for t in templates
    ]

    skill_list = [
        SkillCardResponse(
            id=s["id"],
            name=s["name"],
            icon=s["icon"],
            why=s["why"],
            steps=s["steps"],
            practice_question=s["practice_question"],
            earning_potential=s["earning_potential"],
            category=s["category"],
            discover=s.get("discover", ""),
            challenge=s.get("challenge", {}),
            connect_text=s.get("connect_text", ""),
            linked_business_ids=s.get("linked_business_ids", []),
            optional_practice=s.get("optional_practice", ""),
        )
        for s in SKILL_CARDS
    ]

    investment_options = [
        {
            "id": key,
            "name": val["name"],
            "icon": val["icon"],
            "description": val["description"],
            "range": f"{val['min_return']}% to +{val['max_return']}%",
        }
        for key, val in INVESTMENT_SCENARIOS.items()
    ]

    return GrowTemplatesResponse(
        business=business_list,
        skills=skill_list,
        investment_options=investment_options,
        interest_options=INTEREST_OPTIONS,
    )


@router.post("/recommend", response_model=RecommendResponse)
def recommend_businesses(request: RecommendRequest, db: Session = Depends(get_db)):
    """Rank business templates by child's interests and add AI personalized pitches."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    balance = child.wallet.balance

    templates = get_templates_for_budget(balance)

    # Rank and add personalized pitches
    ranked = rank_templates(request.interests, templates)

    business_list = [
        RankedBusinessResponse(
            id=t["id"],
            name=t["name"],
            min_budget=t["min_budget"],
            cost=t["cost"],
            expected_profit_min=t["expected_profit_min"],
            expected_profit_max=t["expected_profit_max"],
            skills=t["skills"],
            description=t["description"],
            affordable=Decimal(str(t["cost"])) <= balance,
            match_score=t["match_score"],
            pitch=t["pitch"],
        )
        for t in ranked
    ]

    # Build AI message
    if request.interests:
        interest_labels = []
        for i in request.interests:
            for opt in INTEREST_OPTIONS:
                if opt["id"] == i:
                    interest_labels.append(opt["label"])
                    break
        msg = f"Aapko {', '.join(interest_labels)} pasand hai! Ye businesses aapke liye best hain:"
    else:
        msg = "Ye businesses aapke budget mein hain — koi bhi try karein!"

    # Save interests to child record
    existing_interests = json.loads(child.interests) if child.interests else []
    for interest in request.interests:
        if interest not in existing_interests:
            existing_interests.append(interest)
    child.interests = json.dumps(existing_interests)
    db.commit()

    return RecommendResponse(business=business_list, message=msg)


@router.post("/business", response_model=BusinessResultResponse)
def business_route(request: BusinessRequest, db: Session = Depends(get_db)):
    """Start a business simulation."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    result = start_business(db, child, request.template_id)

    return BusinessResultResponse(
        **result,
        message=f"Mubarak ho! Aapne '{result['idea']}' business shuru kiya aur Rs. {result['actual_profit']} kamaye!",
        disclaimer="Ye ek simulation hai. Real business mein results alag ho sakte hain.",
    )


@router.post("/invest", response_model=InvestResultResponse)
def invest_route(request: InvestRequest, db: Session = Depends(get_db)):
    """Run an investment simulation."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    result = invest(db, child, request.amount, request.risk_level)

    if result["is_profit"]:
        msg = f"Aapne Rs. {result['profit_loss']} profit kamaya!"
    else:
        msg = f"Aapka Rs. {abs(result['profit_loss'])} loss hua. Lekin ye simulation hai — seekhna zaroori hai!"

    return InvestResultResponse(
        **result,
        message=msg,
    )


@router.post("/skill", response_model=SkillResultResponse)
def skill_route(request: SkillRequest, db: Session = Depends(get_db)):
    """Explore a skill card and optionally complete a challenge."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    result = explore_skill(
        db, child, request.skill_id,
        practice_answer=request.practice_answer,
        challenge_answer=request.challenge_answer,
        practice_text=request.practice_text,
    )
    return SkillResultResponse(**result)
