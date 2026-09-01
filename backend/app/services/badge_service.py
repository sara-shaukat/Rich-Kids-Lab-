"""Badge service — compute badges and levels from existing data.

All badges are computed on-the-fly from transactions and grow_activities.
No new database tables needed.

Icons are culturally neutral (no piggy imagery — Muslim audience).
"""

import json
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Child, Transaction, Goal, GrowActivity


# ---------------------------------------------------------------------------
# Badge Definitions
# ---------------------------------------------------------------------------

BADGE_DEFINITIONS = [
    {
        "id": "first_save",
        "name": "First Save",
        "icon": "💰",
        "condition_desc": "Pehli baar paisay bachao",
        "meme_line": "Sigma grindset activated! Paisay bachana seekh gaya!",
    },
    {
        "id": "first_business",
        "name": "First Business",
        "icon": "🚀",
        "condition_desc": "Pehla business shuru karo",
        "meme_line": "CEO ban gaya! Elon Musk ko call karo!",
    },
    {
        "id": "first_give",
        "name": "First Give",
        "icon": "🤲",
        "condition_desc": "Pehli baar donate karo",
        "meme_line": "Sadqa jariya! Allah bless kare bhai!",
    },
    {
        "id": "big_spender",
        "name": "Big Spender",
        "icon": "💸",
        "condition_desc": "Rs. 200+ kharch karo",
        "meme_line": "Kharcha king! Lekin bhai budget bhi dekh!",
    },
    {
        "id": "profit_maker",
        "name": "Profit Maker",
        "icon": "📈",
        "condition_desc": "3+ businesses try karo",
        "meme_line": "Serial entrepreneur! Paisa follow karta hai!",
    },
    {
        "id": "explorer",
        "name": "Explorer",
        "icon": "🧭",
        "condition_desc": "Business, Investment, aur Skill teeno try karo",
        "meme_line": "Jack of all trades! Teeno try kar liye!",
    },
    {
        "id": "money_master",
        "name": "Money Master",
        "icon": "👑",
        "condition_desc": "Net worth starting balance se zyada ho",
        "meme_line": "Money Master! Paisa hi paisa hoga!",
    },
]

# ---------------------------------------------------------------------------
# Level Definitions
# ---------------------------------------------------------------------------

LEVEL_DEFINITIONS = [
    {"level": 1, "name": "Newbie", "min_actions": 0, "mascot_line": "Chal seekhte hain!"},
    {"level": 2, "name": "Seekhne Wala", "min_actions": 3, "mascot_line": "Hunnar aa raha hai!"},
    {"level": 3, "name": "Smart Saver", "min_actions": 6, "mascot_line": "Ab tu expert ban raha hai!"},
    {"level": 4, "name": "Paisa Pro", "min_actions": 11, "mascot_line": "Bhai tu toh Warren Buffet nikla!"},
]


# ---------------------------------------------------------------------------
# Badge Computation
# ---------------------------------------------------------------------------

def compute_badges(db: Session, child: Child) -> list[dict]:
    """Return list of earned badges with their details."""
    earned = []

    # Pre-fetch counts
    has_save = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.child_id == child.id, Transaction.type == "SAVE")
        .scalar() > 0
    )

    has_give = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.child_id == child.id, Transaction.type == "GIVE")
        .scalar() > 0
    )

    total_spent = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "SPEND")
        .scalar()
    )

    business_count = (
        db.query(func.count(GrowActivity.id))
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "BUSINESS")
        .scalar()
    )

    grow_types = (
        db.query(GrowActivity.type)
        .filter(GrowActivity.child_id == child.id)
        .distinct()
        .all()
    )
    grow_type_set = {row[0] for row in grow_types}

    # Compute net worth for Money Master badge
    net_worth = compute_net_worth(db, child)
    # Starting balance = wallet balance + total outgoing (spent + given) - total incoming (grown profit) + saved amount
    starting_balance = compute_starting_balance(db, child)

    for badge in BADGE_DEFINITIONS:
        is_earned = False

        if badge["id"] == "first_save":
            is_earned = has_save
        elif badge["id"] == "first_business":
            is_earned = business_count > 0
        elif badge["id"] == "first_give":
            is_earned = has_give
        elif badge["id"] == "big_spender":
            is_earned = total_spent >= Decimal("200")
        elif badge["id"] == "profit_maker":
            is_earned = business_count >= 3
        elif badge["id"] == "explorer":
            is_earned = {"BUSINESS", "INVESTMENT", "SKILL"}.issubset(grow_type_set)
        elif badge["id"] == "money_master":
            is_earned = net_worth > starting_balance and starting_balance > Decimal("0")

        if is_earned:
            earned.append({
                "id": badge["id"],
                "name": badge["name"],
                "icon": badge["icon"],
                "meme_line": badge["meme_line"],
                "earned": True,
            })

    return earned


def compute_unearned_badges(db: Session, child: Child) -> list[dict]:
    """Return list of badges NOT yet earned."""
    earned_ids = {b["id"] for b in compute_badges(db, child)}
    unearned = []
    for badge in BADGE_DEFINITIONS:
        if badge["id"] not in earned_ids:
            unearned.append({
                "id": badge["id"],
                "name": badge["name"],
                "icon": badge["icon"],
                "condition_desc": badge["condition_desc"],
                "earned": False,
            })
    return unearned


# ---------------------------------------------------------------------------
# Level Computation
# ---------------------------------------------------------------------------

def compute_level(db: Session, child: Child) -> dict:
    """Return current level info based on total actions."""
    total_actions = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.child_id == child.id)
        .scalar()
    )
    total_actions += (
        db.query(func.count(GrowActivity.id))
        .filter(GrowActivity.child_id == child.id)
        .scalar()
    )

    # Find current level
    current = LEVEL_DEFINITIONS[0]
    for lvl in LEVEL_DEFINITIONS:
        if total_actions >= lvl["min_actions"]:
            current = lvl

    # Find next level
    next_level = None
    for lvl in LEVEL_DEFINITIONS:
        if lvl["level"] > current["level"]:
            next_level = lvl
            break

    progress = 0
    if next_level:
        actions_in_range = total_actions - current["min_actions"]
        range_size = next_level["min_actions"] - current["min_actions"]
        progress = int((actions_in_range / range_size) * 100)
    else:
        progress = 100  # Max level

    return {
        "level": current["level"],
        "name": current["name"],
        "mascot_line": current["mascot_line"],
        "total_actions": total_actions,
        "progress_to_next": progress,
        "next_level_name": next_level["name"] if next_level else None,
    }


# ---------------------------------------------------------------------------
# Financial Computations
# ---------------------------------------------------------------------------

def compute_net_worth(db: Session, child: Child) -> Decimal:
    """Net worth = wallet.balance + saved_amount + net_grow_profit."""
    balance = child.wallet.balance

    saved = (
        db.query(func.coalesce(func.sum(Goal.saved_amount), 0))
        .filter(Goal.child_id == child.id, Goal.status == "active")
        .scalar()
    )

    # Net grow profit = SUM of all GROW transaction amounts (positive = profit, stored as abs)
    # We need to check actual profit/loss from grow_activities
    net_grow = _compute_net_grow_profit(db, child)

    return balance + saved + net_grow


def compute_starting_balance(db: Session, child: Child) -> Decimal:
    """Compute what the starting balance was.
    
    starting_balance = current_balance + total_spent + total_given + total_saved 
                       - total_grow_profit + total_grow_loss
    """
    balance = child.wallet.balance

    total_saved = (
        db.query(func.coalesce(func.sum(Goal.saved_amount), 0))
        .filter(Goal.child_id == child.id)
        .scalar()
    )

    total_spent = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "SPEND")
        .scalar()
    )

    total_given = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "GIVE")
        .scalar()
    )

    net_grow = _compute_net_grow_profit(db, child)

    return balance + total_saved + total_spent + total_given - net_grow


def _compute_net_grow_profit(db: Session, child: Child) -> Decimal:
    """Compute net profit/loss from all GROW activities."""
    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id)
        .all()
    )

    total = Decimal("0")
    for act in activities:
        if not act.details:
            continue
        details = json.loads(act.details)

        if act.type == "BUSINESS":
            profit = details.get("actual_profit", 0)
            total += Decimal(str(profit))
        elif act.type == "INVESTMENT":
            pl = details.get("profit_loss", 0)
            total += Decimal(str(pl))

    return total


# ---------------------------------------------------------------------------
# Assets & Liabilities
# ---------------------------------------------------------------------------

def compute_assets(db: Session, child: Child) -> list[dict]:
    """Things that grew the child's money."""
    assets = []

    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id)
        .all()
    )

    for act in activities:
        if not act.details:
            continue
        details = json.loads(act.details)

        if act.type == "BUSINESS":
            profit = Decimal(str(details.get("actual_profit", 0)))
            if profit > 0:
                assets.append({
                    "type": "business",
                    "name": details.get("idea", "Unknown"),
                    "amount": profit,
                    "label": f"+Rs. {int(profit)}",
                })
        elif act.type == "INVESTMENT":
            pl = Decimal(str(details.get("profit_loss", 0)))
            if pl > 0:
                risk = details.get("risk_level", "unknown")
                assets.append({
                    "type": "investment",
                    "name": f"Investment ({risk})",
                    "amount": pl,
                    "label": f"+Rs. {int(pl)}",
                })

    return assets


def compute_liabilities(db: Session, child: Child) -> list[dict]:
    """Money that went out without return."""
    liabilities = []

    # Losing investments
    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id)
        .all()
    )

    for act in activities:
        if not act.details:
            continue
        details = json.loads(act.details)

        if act.type == "INVESTMENT":
            pl = Decimal(str(details.get("profit_loss", 0)))
            if pl < 0:
                risk = details.get("risk_level", "unknown")
                liabilities.append({
                    "type": "investment_loss",
                    "name": f"Investment ({risk})",
                    "amount": abs(pl),
                    "label": f"-Rs. {int(abs(pl))}",
                })

    # Total spent
    total_spent = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "SPEND")
        .scalar()
    )
    if total_spent > 0:
        liabilities.append({
            "type": "spent",
            "name": "Total Spending",
            "amount": total_spent,
            "label": f"Rs. {int(total_spent)} spent",
        })

    # Total given
    total_given = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "GIVE")
        .scalar()
    )
    if total_given > 0:
        liabilities.append({
            "type": "given",
            "name": "Total Donations",
            "amount": total_given,
            "label": f"Rs. {int(total_given)} donated",
        })

    return liabilities


# ---------------------------------------------------------------------------
# Business & Investment History
# ---------------------------------------------------------------------------

def compute_business_history(db: Session, child: Child) -> list[dict]:
    """All businesses tried, with outcomes."""
    history = []
    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "BUSINESS")
        .order_by(GrowActivity.created_at.desc())
        .all()
    )

    for act in activities:
        if not act.details:
            continue
        details = json.loads(act.details)
        profit = Decimal(str(details.get("actual_profit", 0)))
        cost = Decimal(str(details.get("cost", 0)))

        history.append({
            "name": details.get("idea", "Unknown"),
            "cost": cost,
            "profit": profit,
            "revenue": Decimal(str(details.get("actual_revenue", 0))),
            "expected_min": Decimal(str(details.get("expected_profit_min", 0))),
            "expected_max": Decimal(str(details.get("expected_profit_max", 0))),
            "is_profit": profit > 0,
            "verdict": "Ye business ne kaam kiya!" if profit > 0 else "Ye business ne kaam nahi kiya",
            "date": str(act.created_at) if act.created_at else None,
        })

    return history


def compute_investment_history(db: Session, child: Child) -> list[dict]:
    """All investments tried, with outcomes."""
    history = []
    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "INVESTMENT")
        .order_by(GrowActivity.created_at.desc())
        .all()
    )

    for act in activities:
        if not act.details:
            continue
        details = json.loads(act.details)
        pl = Decimal(str(details.get("profit_loss", 0)))

        history.append({
            "risk_level": details.get("risk_level", "unknown"),
            "invested": Decimal(str(details.get("initial_amount", 0))),
            "return_pct": details.get("return_percentage", 0),
            "outcome": Decimal(str(details.get("outcome_amount", 0))),
            "profit_loss": pl,
            "is_profit": pl >= 0,
            "verdict": "Investment ne return diya!" if pl >= 0 else "Loss ho gaya, lekin seekh gaye!",
            "date": str(act.created_at) if act.created_at else None,
        })

    return history


# ---------------------------------------------------------------------------
# Last Action Detection
# ---------------------------------------------------------------------------

def get_last_action_type(db: Session, child: Child) -> str | None:
    """Get the most recent action type for mascot context."""
    last_txn = (
        db.query(Transaction)
        .filter(Transaction.child_id == child.id)
        .order_by(Transaction.created_at.desc())
        .first()
    )

    last_grow = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id)
        .order_by(GrowActivity.created_at.desc())
        .first()
    )

    # Compare timestamps
    if last_txn and last_grow:
        if last_txn.created_at >= last_grow.created_at:
            return last_txn.type
        else:
            return f"GROW_{last_grow.type}"
    elif last_txn:
        return last_txn.type
    elif last_grow:
        return f"GROW_{last_grow.type}"

    return None
