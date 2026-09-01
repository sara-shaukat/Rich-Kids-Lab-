"""Mentor context builder — assembles the child's financial state
for the AI Mentor (ARCHITECTURE.md §9).

One query pass over the same data the dashboard uses. No new tables.
"""

import json

from sqlalchemy.orm import Session

from app.models import Child, Transaction, Goal, GrowActivity
from app.services.badge_service import compute_level


def build_mentor_context(db: Session, child: Child) -> dict:
    """Build a structured context dict for the mentor providers."""
    # Goal
    goal = (
        db.query(Goal)
        .filter(Goal.child_id == child.id, Goal.status == "active")
        .first()
    )

    goal_info = None
    if goal:
        remaining = goal.target_amount - goal.saved_amount
        progress_pct = int(goal.saved_amount / goal.target_amount * 100) if goal.target_amount else 0
        goal_info = {
            "name": goal.name,
            "target": float(goal.target_amount),
            "saved": float(goal.saved_amount),
            "remaining": float(remaining),
            "progress_pct": progress_pct,
        }

    # Totals by transaction type
    totals = {"saved": 0.0, "spent": 0.0, "grown": 0.0, "given": 0.0}
    txn_rows = (
        db.query(Transaction)
        .filter(Transaction.child_id == child.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    key_map = {"SAVE": "saved", "SPEND": "spent", "GROW": "grown", "GIVE": "given"}
    for txn in txn_rows:
        totals[key_map.get(txn.type, "grown")] += float(txn.amount)

    recent_transactions = [
        {
            "type": txn.type,
            "amount": float(txn.amount),
            "description": txn.description or "",
        }
        for txn in txn_rows[:5]
    ]

    # Last GROW activity (most recent of business/investment/skill)
    last_grow = None
    grow_act = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id)
        .order_by(GrowActivity.created_at.desc())
        .first()
    )
    if grow_act and grow_act.details:
        details = json.loads(grow_act.details)
        last_grow = {
            "type": grow_act.type,
            "name": details.get("idea") or details.get("name") or "",
        }
        if grow_act.type == "INVESTMENT":
            last_grow["risk_level"] = details.get("risk_level", "unknown")
            last_grow["profit_loss"] = float(details.get("profit_loss", 0))

    # Skills completed
    skills_completed = []
    skill_acts = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "SKILL")
        .all()
    )
    for act in skill_acts:
        if act.details:
            details = json.loads(act.details)
            name = details.get("name")
            if name and name not in skills_completed:
                skills_completed.append(name)

    # Interests
    try:
        interests = json.loads(child.interests) if child.interests else []
    except (ValueError, TypeError):
        interests = []

    # Level
    level = compute_level(db, child)

    return {
        "balance": float(child.wallet.balance),
        "goal": goal_info,
        "totals": totals,
        "recent_transactions": recent_transactions,
        "interests": interests,
        "last_grow": last_grow,
        "skills_completed": skills_completed,
        "level_name": level["name"],
        "total_actions": level["total_actions"],
    }
