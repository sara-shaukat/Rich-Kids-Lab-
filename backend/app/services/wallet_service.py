"""Wallet service — centralized financial logic for money operations.

All wallet mutations go through this module so that validation and the
consistency invariant (wallet.balance + SUM(goals.saved_amount) = total money)
are enforced in exactly one place.
"""

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Child, Wallet, Goal, Transaction


def validate_amount(amount) -> Decimal:
    """Validate that an amount is a positive Decimal number.

    Accepts str, int, float, or Decimal. Returns a Decimal.
    Raises HTTPException(400) for invalid input.
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid amount — must be a number.")

    if value <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")

    return value


def get_child_by_anonymous_id(db: Session, anonymous_id: str) -> Child:
    """Look up a child by anonymous_id. Raises 404 if not found."""
    child = db.query(Child).filter(Child.anonymous_id == anonymous_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Session not found.")
    return child


def get_active_goal(db: Session, child_id: int) -> Goal | None:
    """Return the child's active goal, or None."""
    return (
        db.query(Goal)
        .filter(Goal.child_id == child_id, Goal.status == "active")
        .first()
    )


def create_goal(db: Session, child: Child, name: str, target_amount, target_date=None) -> Goal:
    """Create a new goal for a child.

    Rules:
    - Only one active goal at a time.
    - target_amount must be > 0.
    - name must not be empty.
    """
    # Validate no active goal
    existing = get_active_goal(db, child.id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ek active goal pehle se hai. Pehle usay complete karein.",
        )

    # Validate name
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Goal ka naam zaroori hai.")

    # Validate target amount
    amount = validate_amount(target_amount)

    goal = Goal(
        child_id=child.id,
        name=name.strip(),
        target_amount=amount,
        saved_amount=Decimal("0.00"),
        target_date=target_date,
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def save_to_goal(db: Session, child: Child, goal: Goal, save_amount) -> dict:
    """Save money from wallet into a goal.

    Savings model (from ARCHITECTURE.md §6):
    1. Validate: amount > 0, numeric, <= wallet.balance
    2. wallet.balance -= amount
    3. goal.saved_amount += amount
    4. Record a SAVE transaction
    5. If goal.saved_amount >= goal.target_amount → mark completed
    6. Return updated data
    """
    amount = validate_amount(save_amount)

    # Check goal is active
    if goal.status != "active":
        raise HTTPException(status_code=400, detail="Ye goal active nahi hai.")

    # Check wallet has enough balance
    wallet: Wallet = child.wallet
    if amount > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Aapke paas sirf Rs. {wallet.balance} hain. Rs. {amount} save nahi ho sakte.",
        )

    # Perform the save
    wallet.balance -= amount
    goal.saved_amount += amount

    # Record transaction
    txn = Transaction(
        child_id=child.id,
        type="SAVE",
        amount=amount,
        description=f"Saved toward {goal.name}",
    )
    db.add(txn)

    # Check if goal is completed
    if goal.saved_amount >= goal.target_amount:
        goal.status = "completed"

    db.commit()
    db.refresh(wallet)
    db.refresh(goal)

    return {
        "wallet_balance": wallet.balance,
        "goal_saved_amount": goal.saved_amount,
        "goal_target_amount": goal.target_amount,
        "goal_status": goal.status,
        "saved_this_time": amount,
    }
