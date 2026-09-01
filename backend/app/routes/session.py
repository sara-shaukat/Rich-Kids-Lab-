"""Session routes — create and retrieve child sessions."""

import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Child, Wallet, Goal
from app.schemas import SessionCreateRequest, SessionResponse, WalletResponse, GoalResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _generate_anonymous_id() -> str:
    """Generate an anonymous child ID like RKL-7F29A."""
    return "RKL-" + secrets.token_hex(3).upper()


def _get_active_goal(db: Session, child_id: int) -> Goal | None:
    return db.query(Goal).filter(
        Goal.child_id == child_id,
        Goal.status == "active",
    ).first()


def _build_session_response(child: Child) -> SessionResponse:
    active_goal = None
    goal = _get_active_goal_simple(child)
    if goal:
        active_goal = GoalResponse(
            id=goal.id,
            name=goal.name,
            target_amount=goal.target_amount,
            saved_amount=goal.saved_amount,
            status=goal.status,
            target_date=str(goal.target_date) if goal.target_date else None,
        )

    return SessionResponse(
        anonymous_id=child.anonymous_id,
        wallet=WalletResponse(balance=child.wallet.balance),
        active_goal=active_goal,
    )


def _get_active_goal_simple(child: Child) -> Goal | None:
    """Get active goal from the child's loaded relationships."""
    for goal in child.goals:
        if goal.status == "active":
            return goal
    return None


@router.post("", response_model=SessionResponse)
def create_session(request: SessionCreateRequest, db: Session = Depends(get_db)):
    """Create a new child session with anonymous ID and wallet."""
    # Validate starting balance
    if request.starting_balance <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Starting balance must be greater than zero.")

    # Generate unique anonymous ID
    anonymous_id = _generate_anonymous_id()
    while db.query(Child).filter(Child.anonymous_id == anonymous_id).first():
        anonymous_id = _generate_anonymous_id()

    # Create child + wallet
    child = Child(anonymous_id=anonymous_id)
    db.add(child)
    db.flush()  # Get child.id

    wallet = Wallet(child_id=child.id, balance=request.starting_balance)
    db.add(wallet)
    db.commit()
    db.refresh(child)

    return _build_session_response(child)


@router.get("/{anonymous_id}", response_model=SessionResponse)
def get_session(anonymous_id: str, db: Session = Depends(get_db)):
    """Get an existing child session by anonymous ID."""
    child = db.query(Child).filter(Child.anonymous_id == anonymous_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Session not found.")

    return _build_session_response(child)
