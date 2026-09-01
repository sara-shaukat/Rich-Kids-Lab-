"""Dashboard route — returns aggregated financial summary.

V2: Also returns net_worth, assets, liabilities, badges, level, mascot, history.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Child, Transaction, Goal
from app.schemas import DashboardResponse, GoalResponse

from app.services.badge_service import (
    compute_badges,
    compute_unearned_badges,
    compute_level,
    compute_net_worth,
    compute_assets,
    compute_liabilities,
    compute_business_history,
    compute_investment_history,
    get_last_action_type,
)
from app.services.mascot_lines import get_mascot_line

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/{anonymous_id}", response_model=DashboardResponse)
def get_dashboard(anonymous_id: str, db: Session = Depends(get_db)):
    """Return dashboard summary: balance, totals, badges, level, mascot, history."""
    child = db.query(Child).filter(Child.anonymous_id == anonymous_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Aggregate totals by transaction type
    totals = (
        db.query(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .filter(Transaction.child_id == child.id)
        .group_by(Transaction.type)
        .all()
    )

    total_map = {row[0]: Decimal(str(row[1])) for row in totals}

    # Find active goal
    active_goal = (
        db.query(Goal)
        .filter(Goal.child_id == child.id, Goal.status == "active")
        .first()
    )

    goal_response = None
    if active_goal:
        goal_response = GoalResponse(
            id=active_goal.id,
            name=active_goal.name,
            target_amount=active_goal.target_amount,
            saved_amount=active_goal.saved_amount,
            status=active_goal.status,
            target_date=str(active_goal.target_date) if active_goal.target_date else None,
        )

    # --- V2 fields ---
    net_worth = compute_net_worth(db, child)
    assets = compute_assets(db, child)
    liabilities = compute_liabilities(db, child)
    business_history = compute_business_history(db, child)
    investment_history = compute_investment_history(db, child)
    badges = compute_badges(db, child)
    unearned_badges = compute_unearned_badges(db, child)
    level = compute_level(db, child)
    last_action = get_last_action_type(db, child)

    # Check for investment losses (for mascot context)
    has_investment_losses = any(
        item["type"] == "investment_loss" for item in liabilities
    )

    total_spent_float = float(total_map.get("SPEND", Decimal("0")))
    balance_float = float(child.wallet.balance)

    mascot_data = get_mascot_line(
        last_action_type=last_action,
        balance=balance_float,
        has_active_goal=active_goal is not None,
        has_investment_losses=has_investment_losses,
        total_spent=total_spent_float,
    )

    return DashboardResponse(
        anonymous_id=child.anonymous_id,
        balance=child.wallet.balance,
        total_saved=total_map.get("SAVE", Decimal("0")),
        total_spent=total_map.get("SPEND", Decimal("0")),
        total_grown=total_map.get("GROW", Decimal("0")),
        total_given=total_map.get("GIVE", Decimal("0")),
        active_goal=goal_response,
        # V2
        net_worth=net_worth,
        assets=assets,
        liabilities=liabilities,
        business_history=business_history,
        investment_history=investment_history,
        badges=badges,
        unearned_badges=unearned_badges,
        level=level,
        mascot_line=mascot_data["line"],
        mascot_mode=mascot_data["mode"],
        last_action_type=last_action,
    )
