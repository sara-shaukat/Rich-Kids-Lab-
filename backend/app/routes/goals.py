"""Goal routes — create goals, save money, list goals."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Goal
from app.schemas import GoalResponse
from app.services.wallet_service import (
    get_child_by_anonymous_id,
    get_active_goal,
    create_goal,
    save_to_goal,
)

router = APIRouter(prefix="/api/goals", tags=["goals"])


# --- Request schemas ---

class GoalCreateRequest(BaseModel):
    anonymous_id: str
    name: str = Field(..., min_length=1, max_length=100)
    target_amount: Decimal = Field(..., gt=0)
    target_date: date | None = None


class GoalSaveRequest(BaseModel):
    anonymous_id: str
    amount: Decimal = Field(..., gt=0)


class SaveResultResponse(BaseModel):
    wallet_balance: Decimal
    goal_saved_amount: Decimal
    goal_target_amount: Decimal
    goal_status: str
    saved_this_time: Decimal
    message: str


# --- Helper ---

def _goal_to_response(goal: Goal) -> GoalResponse:
    return GoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        saved_amount=goal.saved_amount,
        status=goal.status,
        target_date=str(goal.target_date) if goal.target_date else None,
    )


# --- Routes ---

@router.post("", response_model=GoalResponse)
def create_goal_route(request: GoalCreateRequest, db: Session = Depends(get_db)):
    """Create a new goal. Only allowed if no active goal exists."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    goal = create_goal(
        db,
        child,
        name=request.name,
        target_amount=request.target_amount,
        target_date=request.target_date,
    )
    return _goal_to_response(goal)


@router.get("/{anonymous_id}", response_model=list[GoalResponse])
def list_goals(anonymous_id: str, db: Session = Depends(get_db)):
    """List all goals for a child (active and completed)."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    goals = (
        db.query(Goal)
        .filter(Goal.child_id == child.id)
        .order_by(Goal.created_at.desc())
        .all()
    )
    return [_goal_to_response(g) for g in goals]


@router.post("/{goal_id}/save", response_model=SaveResultResponse)
def save_money_to_goal(goal_id: int, request: GoalSaveRequest, db: Session = Depends(get_db)):
    """Save money from wallet into a specific goal."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)

    # Verify the goal belongs to this child
    goal = db.query(Goal).filter(Goal.id == goal_id, Goal.child_id == child.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found.")

    result = save_to_goal(db, child, goal, request.amount)

    # Build a child-friendly message
    remaining = result["goal_target_amount"] - result["goal_saved_amount"]
    if result["goal_status"] == "completed":
        message = f"Mubarak ho! Aapne apna goal '{goal.name}' complete kar liya!"
    else:
        message = (
            f"Aapne Rs. {result['saved_this_time']} save kiye! "
            f"Ab Rs. {remaining} aur chahiye goal complete karne ke liye."
        )

    return SaveResultResponse(
        wallet_balance=result["wallet_balance"],
        goal_saved_amount=result["goal_saved_amount"],
        goal_target_amount=result["goal_target_amount"],
        goal_status=result["goal_status"],
        saved_this_time=result["saved_this_time"],
        message=message,
    )
