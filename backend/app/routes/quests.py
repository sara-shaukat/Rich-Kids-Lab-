"""Quest routes — V1 trade-off quests (3 quests, deterministic engine)."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.wallet_service import get_child_by_anonymous_id
from app.services.quest_service import (
    get_quest_states,
    resolve_quest,
    submit_reflection,
)

router = APIRouter(prefix="/api/quests", tags=["quests"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QuestChoiceResponse(BaseModel):
    id: str
    label: str
    sub: str


class QuestReflectionOption(BaseModel):
    id: str
    label: str
    bot_line: str


class QuestReflectionResponse(BaseModel):
    question: str
    options: list[QuestReflectionOption]


class QuestResponse(BaseModel):
    id: str
    title: str
    icon: str
    concept: str
    status: str  # locked | available | completed
    lock_reason: str | None = None
    scenario_lines: list[str] = []
    choices: list[QuestChoiceResponse] = []
    verdict: str | None = None
    headline: str | None = None
    reflected: bool = False


class QuestListResponse(BaseModel):
    anonymous_id: str
    quests: list[QuestResponse]


class ResolveRequest(BaseModel):
    anonymous_id: str
    quest_id: str = Field(..., min_length=1)
    choice_id: str = Field(..., min_length=1)


class ResolveResponse(BaseModel):
    quest_id: str
    choice_id: str
    verdict: str
    headline: str
    what_happened: list[str]
    wallet_balance: Decimal
    goal_name: str | None = None
    goal_saved_amount: Decimal | None = None
    goal_target_amount: Decimal | None = None
    goal_status: str | None = None
    goal_pct: int | None = None
    investment_profit_loss: Decimal | None = None
    reflection: QuestReflectionResponse


class ReflectRequest(BaseModel):
    anonymous_id: str
    quest_id: str = Field(..., min_length=1)
    answer_id: str = Field(..., min_length=1)


class ReflectResponse(BaseModel):
    quest_id: str
    answer_id: str
    bot_line: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{anonymous_id}", response_model=QuestListResponse)
def get_quests(anonymous_id: str, db: Session = Depends(get_db)):
    """Return the 3 quest cards with their current states."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    quests = get_quest_states(db, child)
    return QuestListResponse(anonymous_id=child.anonymous_id, quests=quests)


@router.post("/resolve", response_model=ResolveResponse)
def resolve(request: ResolveRequest, db: Session = Depends(get_db)):
    """Resolve a quest choice — executes the real wallet/goal action."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    return resolve_quest(db, child, request.quest_id, request.choice_id)


@router.post("/reflect", response_model=ReflectResponse)
def reflect(request: ReflectRequest, db: Session = Depends(get_db)):
    """Store the child's reflection answer on a completed quest."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    return submit_reflection(db, child, request.quest_id, request.answer_id)
