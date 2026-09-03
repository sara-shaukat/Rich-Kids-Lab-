"""Money Lab V2 — 7-day business experiment service.

Upgrades the instant experiment into a simulated 7-day business experience:
CHOOSE → PLAN → RUN → OBSERVE → DECIDE → CONSEQUENCES → ADAPT → FINAL RESULT → REFLECT → RETRY

State stored in GrowActivity.details JSON field — no new database tables.
Reuses: Transaction model, GrowActivity model, validate_amount from wallet_service.
"""

import json
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Child, Transaction, GrowActivity
from app.services.wallet_service import validate_amount


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_START_MONEY = Decimal("500")
TOTAL_DAYS = 7
DECISION_DAY = 4

EXPERIMENT_BUSINESSES = [
    {
        "id": "art_cards", "name": "Art Cards",
        "icon": "\U0001f3a8",
        "description": "Handmade greeting cards — creative aur fun!",
        "base_cost": 100, "unit_cost": 10,
        "risk": "medium",
        "demand": {"cheap": [6, 10], "normal": [4, 7], "premium": [2, 4]},
    },
    {
        "id": "bracelets", "name": "Bracelets",
        "icon": "\U0001f4ff",
        "description": "Colorful bracelets — safe aur steady!",
        "base_cost": 80, "unit_cost": 8,
        "risk": "low",
        "demand": {"cheap": [7, 12], "normal": [4, 8], "premium": [2, 5]},
    },
    {
        "id": "snack_stall", "name": "Snack Stall",
        "icon": "\U0001f37f",
        "description": "Snacks aur drinks — bada risk, bada reward!",
        "base_cost": 150, "unit_cost": 15,
        "risk": "high",
        "demand": {"cheap": [8, 14], "normal": [5, 10], "premium": [2, 6]},
    },
]

INVESTMENT_OPTIONS = [
    {"id": "small", "label": "Chhota", "multiplier": 1,
     "description": "Kam invest — kam risk, kam stock"},
    {"id": "medium", "label": "Darmiyana", "multiplier": 2,
     "description": "Munasib invest — balance risk aur reward"},
    {"id": "large", "label": "Bada", "multiplier": 3,
     "description": "Zyada invest — zyada stock, zyada risk"},
]

PRICING_OPTIONS = [
    {"id": "cheap", "label": "Sasta", "price_multiplier": Decimal("0.8"),
     "revenue_multiplier": Decimal("0.8"),
     "demand_hint": "6–12 customers/day",
     "description": "Kam qeemat — zyada customers ki umeed"},
    {"id": "normal", "label": "Aam", "price_multiplier": Decimal("1.0"),
     "revenue_multiplier": Decimal("1.0"),
     "demand_hint": "4–8 customers/day",
     "description": "Normal qeemat — balanced demand"},
    {"id": "premium", "label": "Mehnga", "price_multiplier": Decimal("1.3"),
     "revenue_multiplier": Decimal("1.3"),
     "demand_hint": "2–5 customers/day",
     "description": "Zyada qeemat — kam customers, zyada per sale"},
]

DAILY_EVENTS = [
    {"id": "normal_day", "day": 1, "name": "Normal Day", "icon": "\u2600\ufe0f",
     "customer_modifier": Decimal("1.0"), "extra_cost": 0,
     "message": "Aam din — business as usual!", "story": "Business khul gaya!"},
    {"id": "good_weather", "day": 2, "name": "Acha Mausam", "icon": "\U0001f324\ufe0f",
     "customer_modifier": Decimal("1.2"), "extra_cost": 0,
     "message": "Mausam acha hai — zyada log bahar hain!", "story": "Acha mausam tha!"},
    {"id": "rainy_day", "day": 3, "name": "Barish!", "icon": "\U0001f327\ufe0f",
     "customer_modifier": Decimal("0.5"), "extra_cost": 0,
     "message": "Barish ho gayi — kam customers aaye!", "story": "Barish ka din tha."},
    {"id": "decision_day", "day": 4, "name": "Decision Day", "icon": "\U0001f914",
     "customer_modifier": Decimal("1.0"), "extra_cost": 0,
     "message": "Waqt hai faisla karne ka!", "story": "Business check ka din."},
    {"id": "school_fair", "day": 5, "name": "School Fair!", "icon": "\U0001f3aa",
     "customer_modifier": Decimal("1.5"), "extra_cost": 0,
     "message": "School fair mein zabardast bheer!", "story": "School fair ka din!"},
    {"id": "supplier_cost", "day": 6, "name": "Mehnga Supplier", "icon": "\U0001f4b8",
     "customer_modifier": Decimal("1.0"), "extra_cost": 30,
     "message": "Supplier ne qeematein barha deen!", "story": "Supplier ka jhatka!"},
    {"id": "trending", "day": 7, "name": "Trending!", "icon": "\U0001f525",
     "customer_modifier": Decimal("1.3"), "extra_cost": 0,
     "message": "Tumhara product trending pe hai!", "story": "Aakhri din — trending!"},
]

DAY4_DECISIONS = [
    {"id": "buy_stock", "label": "\U0001f4e6 Aur Stock Khareedo",
     "description": "Paisay lagao, zyada sales ka chance"},
    {"id": "raise_price", "label": "\U0001f4b5 Qeemat Barhao",
     "description": "Zyada per sale — lekin kam customers ho sakte hain"},
    {"id": "lower_price", "label": "\U0001f3f7\ufe0f Qeemat Kam Karo",
     "description": "Kam qeemat — zyada customers aa sakte hain"},
    {"id": "keep_going", "label": "\u27a1\ufe0f Kuch Mat Badlo",
     "description": "Current strategy se aage barho"},
]

REFLECTION_OPTIONS = [
    {"id": "change_price", "label": "\U0001f4b5 Qeemat badloon ga",
     "bot_line": "Smart! Pricing ek powerful tool hai — experiment karke best price dhundho!"},
    {"id": "invest_less", "label": "\U0001f4b0 Kam invest karoon ga",
     "bot_line": "Samajhdari! Chhota start kabhi kabhi best hota hai — risk control mein rehta hai."},
    {"id": "invest_more", "label": "\U0001f4aa Zyada invest karoon ga",
     "bot_line": "Himmat! Zyada stock = zyada sales ka chance — lekin plan zaroor banao!"},
    {"id": "different_business", "label": "\U0001f504 Doosra business try karoon ga",
     "bot_line": "Acha idea! Har business alag hota hai — try karke dekho konsa best hai!"},
    {"id": "keep_strategy", "label": "\u2705 Yehi strategy rakhoon ga",
     "bot_line": "Confidence! Agar strategy kaam karti hai to usse improve karna seekho!"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_business(business_id: str) -> dict | None:
    return next((b for b in EXPERIMENT_BUSINESSES if b["id"] == business_id), None)


def _find_investment(investment_id: str) -> dict | None:
    return next((o for o in INVESTMENT_OPTIONS if o["id"] == investment_id), None)


def _find_pricing(pricing_id: str) -> dict | None:
    return next((o for o in PRICING_OPTIONS if o["id"] == pricing_id), None)


def _event_for_day(day: int) -> dict:
    return DAILY_EVENTS[day - 1]


def _calc_demand(business: dict, pricing_id: str,
                 investment_multiplier: int, event: dict) -> tuple[int, int]:
    """Return (low, high) customer count for this day."""
    base = business["demand"][pricing_id]
    # Moderate scaling: 1x, 1.3x, 1.6x for investment levels 1, 2, 3
    scale = Decimal("1") + Decimal(str(investment_multiplier - 1)) * Decimal("0.3")
    mod = event["customer_modifier"]
    low = int(Decimal(str(base[0])) * scale * mod)
    high = int(Decimal(str(base[1])) * scale * mod)
    return max(1, low), max(low, high)


def _round_money(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _make_initial_state(child_id: int) -> dict:
    return {
        "phase": "choosing", "day": 0,
        "business_id": None, "investment_id": None, "pricing_id": None,
        "cash": float(EXPERIMENT_START_MONEY), "stock": 0,
        "total_revenue": 0.0, "total_costs": 0.0, "initial_investment": 0.0,
        "total_customers": 0, "total_units_sold": 0,
        "events_log": [], "decision_made": None,
        "daily_outcomes": [], "current_price_multiplier": 1.0,
    }


def _get_latest_activity(db: Session, child: Child) -> GrowActivity | None:
    return (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id,
                GrowActivity.type == "MONEY_LAB")
        .order_by(GrowActivity.id.desc())
        .first()
    )


def _load_state(activity: GrowActivity) -> dict:
    return json.loads(activity.details) if activity and activity.details else {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_experiment(db: Session, child: Child) -> dict:
    """Grant Rs. 500 virtual experiment money and initialise state."""
    wallet = child.wallet
    wallet.balance += EXPERIMENT_START_MONEY

    txn = Transaction(
        child_id=child.id, type="GROW",
        amount=EXPERIMENT_START_MONEY,
        description="Money Lab: Experiment grant (7-day)",
    )
    db.add(txn)

    state = _make_initial_state(child.id)
    activity = GrowActivity(
        child_id=child.id, type="MONEY_LAB",
        details=json.dumps(state),
    )
    db.add(activity)
    db.commit()
    db.refresh(wallet)
    db.refresh(activity)

    return {
        "activity_id": activity.id,
        "balance": wallet.balance,
        "grant": EXPERIMENT_START_MONEY,
        "businesses": EXPERIMENT_BUSINESSES,
        "investment_options": INVESTMENT_OPTIONS,
        "pricing_options": [
            {k: v for k, v in p.items() if k not in ("revenue_multiplier",)}
            for p in PRICING_OPTIONS
        ],
    }


def get_experiment_state(db: Session, child: Child) -> dict:
    """Return current experiment state for recovery / polling."""
    activity = _get_latest_activity(db, child)
    if not activity:
        return {"phase": "none"}
    state = _load_state(activity)
    business = _find_business(state.get("business_id", "")) if state.get("business_id") else None
    return {
        "activity_id": activity.id,
        "state": state,
        "business": business,
        "wallet_balance": float(child.wallet.balance),
    }


def submit_choices(
    db: Session, child: Child,
    business_id: str, investment_id: str, pricing_id: str,
) -> dict:
    """Submit business/investment/pricing and simulate Day 1."""
    business = _find_business(business_id)
    if not business:
        raise HTTPException(400, "Invalid business selected.")
    investment = _find_investment(investment_id)
    if not investment:
        raise HTTPException(400, "Invalid investment level.")
    pricing = _find_pricing(pricing_id)
    if not pricing:
        raise HTTPException(400, "Invalid pricing strategy.")

    cost = Decimal(str(business["base_cost"] * investment["multiplier"]))
    if cost > child.wallet.balance:
        raise HTTPException(
            400,
            f"Aapke paas sirf Rs. {child.wallet.balance} hain. Rs. {cost} chahiye.",
        )

    stock = investment["multiplier"] * 20
    experiment_cash = float(EXPERIMENT_START_MONEY - cost)

    activity = _get_latest_activity(db, child)
    if not activity:
        raise HTTPException(400, "Start experiment first.")

    # Build state
    state = {
        "phase": "running", "day": 1,
        "business_id": business_id, "investment_id": investment_id,
        "pricing_id": pricing_id,
        "cash": experiment_cash, "stock": stock,
        "total_revenue": 0.0, "total_costs": float(cost),
        "initial_investment": float(cost),
        "total_customers": 0, "total_units_sold": 0,
        "events_log": [], "decision_made": None,
        "daily_outcomes": [], "current_price_multiplier": 1.0,
    }

    # Simulate Day 1
    event = _event_for_day(1)
    outcome = _simulate_day(state, business, pricing, investment, event)
    state["daily_outcomes"].append(outcome)
    state["events_log"].append(event["id"])
    _apply_day(state, outcome, event)

    activity.details = json.dumps(state)
    db.commit()

    return {
        "day": 1, "event": event, "outcome": outcome,
        "business_name": business["name"], "business_icon": business["icon"],
        "investment_label": investment["label"], "pricing_label": pricing["label"],
        "stock_bought": stock, "initial_cost": float(cost),
        "state": _summary(state),
    }


def advance_day(db: Session, child: Child) -> dict:
    """Advance to the next day. Returns result, decision prompt, or final."""
    activity = _get_latest_activity(db, child)
    if not activity:
        raise HTTPException(400, "No active experiment.")

    state = _load_state(activity)
    if state["phase"] != "running":
        raise HTTPException(400, "Experiment is not running.")

    current_day = state["day"]

    # Day 4 — return decision prompt (no simulation yet)
    if current_day == DECISION_DAY:
        return _decision_prompt(state)

    # Finish after Day 7
    if current_day >= TOTAL_DAYS:
        return _finalize_experiment(db, child, state, activity)

    # Simulate next day
    business = _find_business(state["business_id"])
    investment = _find_investment(state["investment_id"])
    pricing = _find_pricing(state["pricing_id"])
    next_day = current_day + 1
    event = _event_for_day(next_day)

    outcome = _simulate_day(state, business, pricing, investment, event)
    state["day"] = next_day
    state["daily_outcomes"].append(outcome)
    state["events_log"].append(event["id"])
    _apply_day(state, outcome, event)

    # Auto-finalize when Day 7 is reached
    if next_day >= TOTAL_DAYS:
        state["phase"] = "finished"
        activity.details = json.dumps(state)
        db.commit()
        final = _finalize_experiment(db, child, state, activity)
        final["day"] = next_day
        final["event"] = event
        final["outcome"] = outcome
        return final

    activity.details = json.dumps(state)
    db.commit()

    return {
        "day": next_day, "event": event, "outcome": outcome,
        "state": _summary(state),
    }


def submit_decision(db: Session, child: Child, decision_id: str) -> dict:
    """Apply Day 4 mid-game decision and advance to Day 5."""
    activity = _get_latest_activity(db, child)
    if not activity:
        raise HTTPException(400, "No active experiment.")

    state = _load_state(activity)
    if state["phase"] != "running" or state["day"] != DECISION_DAY:
        raise HTTPException(400, "Not decision time.")

    decision = next((d for d in DAY4_DECISIONS if d["id"] == decision_id), None)
    if not decision:
        raise HTTPException(400, "Invalid decision.")

    business = _find_business(state["business_id"])
    investment = _find_investment(state["investment_id"])
    pricing = _find_pricing(state["pricing_id"])
    unit_cost = float(Decimal(str(business["unit_cost"])) * Decimal(str(investment["multiplier"])))

    # Apply decision
    if decision_id == "buy_stock":
        restock_cost = unit_cost
        if Decimal(str(restock_cost)) > Decimal(str(state["cash"])):
            raise HTTPException(400, f"Rs. {restock_cost} chahiye, sirf Rs. {state['cash']} hain.")
        state["cash"] -= restock_cost
        state["stock"] += 10
        state["total_costs"] += restock_cost
    elif decision_id == "raise_price":
        state["current_price_multiplier"] = 1.25
    elif decision_id == "lower_price":
        state["current_price_multiplier"] = 0.80

    state["decision_made"] = decision_id

    # Simulate Day 5
    next_day = DECISION_DAY + 1
    event = _event_for_day(next_day)
    outcome = _simulate_day(state, business, pricing, investment, event)
    state["day"] = next_day
    state["daily_outcomes"].append(outcome)
    state["events_log"].append(event["id"])
    _apply_day(state, outcome, event)

    activity.details = json.dumps(state)
    db.commit()

    return {
        "day": next_day, "decision_applied": decision_id,
        "event": event, "outcome": outcome,
        "state": _summary(state),
    }


def submit_experiment_reflection(db: Session, child: Child, reflection_id: str) -> dict:
    """Record child's reflection on the experiment."""
    option = next((o for o in REFLECTION_OPTIONS if o["id"] == reflection_id), None)
    if not option:
        return {"bot_line": "Reflection recorded!"}

    activity = _get_latest_activity(db, child)
    if activity:
        state = _load_state(activity)
        state["phase"] = "reflected"
        state["reflection"] = reflection_id
        activity.details = json.dumps(state)
        db.commit()

    return {"bot_line": option["bot_line"]}


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def _simulate_day(state: dict, business: dict, pricing: dict,
                  investment: dict, event: dict) -> dict:
    """Compute one day's business outcome without mutating state."""
    low, high = _calc_demand(business, pricing["id"],
                              investment["multiplier"], event)
    actual_customers = (low + high) // 2

    price_mult = Decimal(str(state.get("current_price_multiplier", 1.0)))
    rev_per_unit = _round_money(
        Decimal(str(pricing["revenue_multiplier"])) * price_mult * Decimal("50")
    )
    units_sold = min(actual_customers, state["stock"])
    revenue = float(rev_per_unit * Decimal(str(units_sold)))

    ran_out = actual_customers > state["stock"]
    extra_cost = float(event.get("extra_cost", 0))

    # Build story text
    if ran_out and state["stock"] > 0:
        story = (f"{event['story']} {actual_customers} customers aaye lekin "
                 f"stock khatam! Sirf {units_sold} units bike.")
    elif state["stock"] == 0:
        story = f"{event['story']} Stock khatam — koi sale nahi hui!"
    else:
        story = f"{event['story']} {actual_customers} customers aaye! {units_sold} units bike."

    return {
        "customers": actual_customers,
        "potential_demand_low": low,
        "potential_demand_high": high,
        "units_sold": units_sold,
        "revenue": revenue,
        "revenue_per_unit": float(rev_per_unit),
        "stock_remaining": state["stock"] - units_sold,
        "ran_out_of_stock": ran_out,
        "extra_cost": extra_cost,
        "story": story,
    }


def _apply_day(state: dict, outcome: dict, event: dict):
    """Mutate running state with a day's outcome."""
    state["cash"] += outcome["revenue"] - outcome["extra_cost"]
    state["stock"] = outcome["stock_remaining"]
    state["total_revenue"] += outcome["revenue"]
    state["total_costs"] += outcome["extra_cost"]
    state["total_customers"] += outcome["customers"]
    state["total_units_sold"] += outcome["units_sold"]


def _summary(state: dict) -> dict:
    """Public-friendly state summary."""
    profit = state["cash"] - float(EXPERIMENT_START_MONEY)
    return {
        "phase": state["phase"], "day": state["day"],
        "cash": round(state["cash"], 2), "stock": state["stock"],
        "total_customers": state["total_customers"],
        "total_units_sold": state["total_units_sold"],
        "total_revenue": round(state["total_revenue"], 2),
        "total_costs": round(state["total_costs"], 2),
        "profit_loss": round(profit, 2),
    }


def _decision_prompt(state: dict) -> dict:
    business = _find_business(state["business_id"])
    investment = _find_investment(state["investment_id"])
    unit_cost = float(
        Decimal(str(business["unit_cost"])) * Decimal(str(investment["multiplier"]))
    )
    decisions = []
    for d in DAY4_DECISIONS:
        entry = dict(d)
        if d["id"] == "buy_stock":
            entry["cost"] = unit_cost
            entry["stock_gain"] = 10
            if Decimal(str(unit_cost)) > Decimal(str(state["cash"])):
                entry["disabled"] = True
        decisions.append(entry)

    return {
        "needs_decision": True, "day": DECISION_DAY,
        "decisions": decisions,
        "state": _summary(state),
    }


def _finalize_experiment(db: Session, child: Child,
                         state: dict, activity: GrowActivity) -> dict:
    """Calculate final P/L and settle to wallet."""
    wallet = child.wallet
    balance_before = float(wallet.balance)

    profit_loss = Decimal(str(state["cash"])) - EXPERIMENT_START_MONEY
    wallet.balance += profit_loss
    if wallet.balance < Decimal("0"):
        wallet.balance = Decimal("0")

    desc = f"Money Lab 7-Day: {state['business_id']} ({'+' if profit_loss >= 0 else ''}{profit_loss})"
    txn = Transaction(
        child_id=child.id, type="GROW",
        amount=abs(profit_loss), description=desc,
    )
    db.add(txn)

    state["phase"] = "finished"
    state["final_cash"] = round(state["cash"], 2)
    state["profit_loss"] = float(profit_loss)
    state["is_profit"] = profit_loss >= Decimal("0")

    activity.details = json.dumps(state)
    db.commit()
    db.refresh(wallet)

    business = _find_business(state["business_id"])
    return {
        "finished": True,
        "business_name": business["name"],
        "business_icon": business["icon"],
        "starting_money": float(EXPERIMENT_START_MONEY),
        "total_revenue": round(state["total_revenue"], 2),
        "total_costs": round(state["total_costs"], 2),
        "total_customers": state["total_customers"],
        "total_units_sold": state["total_units_sold"],
        "final_cash": round(state["cash"], 2),
        "profit_loss": float(profit_loss),
        "is_profit": profit_loss >= Decimal("0"),
        "balance_before": balance_before,
        "balance_after": float(wallet.balance),
        "days_completed": TOTAL_DAYS,
        "reflection": {
            "question": "Agar dobara try karo to kya badlo ge?",
            "options": REFLECTION_OPTIONS,
        },
        "real_world": {
            "title": "Real World",
            "text": (
                "Apple jaisi companies premium pricing use karti hain. "
                "Lekin zyada qeemat hamesha zyada profit nahi deti — "
                "customers ki demand bhi matter karti hai. "
                "Money Lab mein alag prices try karo!"
            ),
        },
    }
