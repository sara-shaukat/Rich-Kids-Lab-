"""Spend routes — predefined scenarios and spend transactions."""

import random
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Child, Wallet, Transaction
from app.services.wallet_service import get_child_by_anonymous_id, validate_amount

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# ---------------------------------------------------------------------------
# Predefined spend scenario sets (from SPEC.md §10)
# ---------------------------------------------------------------------------

SPEND_SCENARIOS = [
    {
        "id": "everyday",
        "title": "Aapke paas paise hain. Aap kya choose karoge?",
        "options": [
            {
                "id": "pizza",
                "name": "Pizza",
                "cost": 300,
                "consequence": "Mazedaar pizza! Lekin ab aapke paas kam paisay hain.",
            },
            {
                "id": "book",
                "name": "Book",
                "cost": 200,
                "consequence": "Kitab parhna ek achi aadat hai! Aapne seekhne mein invest kiya.",
            },
            {
                "id": "game",
                "name": "Game",
                "cost": 250,
                "consequence": "Game khelna mazedaar hai! Lekin yaad rakho, entertainment bhi budget mein hona chahiye.",
            },
            {
                "id": "save_instead",
                "name": "Save Instead",
                "cost": 0,
                "consequence": "Bohot acha faisla! Kabhi kabhi na khareedna bhi ek smart choice hai.",
            },
        ],
    },
    {
        "id": "weekend",
        "title": "Weekend aa gaya! Aap kya karoge?",
        "options": [
            {
                "id": "cinema",
                "name": "Cinema",
                "cost": 400,
                "consequence": "Cinema ka maza! Lekin ye ek luxury hai — zaroorat nahi.",
            },
            {
                "id": "snack",
                "name": "Snack",
                "cost": 100,
                "consequence": "Chota snack, chota kharcha. Smart choice!",
            },
            {
                "id": "toy",
                "name": "Toy",
                "cost": 350,
                "consequence": "Khilona khareedna acha hai, lekin kya ye zaroori tha?",
            },
            {
                "id": "save_instead",
                "name": "Save Instead",
                "cost": 0,
                "consequence": "Aapne paise bachaye. Ye discipline hai!",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SpendRequest(BaseModel):
    anonymous_id: str
    option_id: str = Field(..., min_length=1)


class SpendOptionResponse(BaseModel):
    id: str
    name: str
    cost: int
    affordable: bool
    consequence: str


class SpendScenarioResponse(BaseModel):
    scenario_id: str
    title: str
    options: list[SpendOptionResponse]


class SpendResultResponse(BaseModel):
    new_balance: Decimal
    spent_amount: Decimal
    option_name: str
    consequence: str
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/spend/scenarios/{anonymous_id}", response_model=SpendScenarioResponse)
def get_spend_scenarios(anonymous_id: str, db: Session = Depends(get_db)):
    """Return a random spend scenario set with affordability flags."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    balance = child.wallet.balance

    # Pick a random scenario set
    scenario = random.choice(SPEND_SCENARIOS)

    options = []
    for opt in scenario["options"]:
        cost = Decimal(str(opt["cost"]))
        affordable = cost <= balance or cost == Decimal("0")
        options.append(SpendOptionResponse(
            id=opt["id"],
            name=opt["name"],
            cost=opt["cost"],
            affordable=affordable,
            consequence=opt["consequence"],
        ))

    return SpendScenarioResponse(
        scenario_id=scenario["id"],
        title=scenario["title"],
        options=options,
    )


def _find_option(scenario_options: list[dict], option_id: str) -> dict | None:
    """Find an option by id across all scenario sets."""
    for scenario in SPEND_SCENARIOS:
        for opt in scenario["options"]:
            if opt["id"] == option_id:
                return opt
    return None


@router.post("/spend", response_model=SpendResultResponse)
def spend(request: SpendRequest, db: Session = Depends(get_db)):
    """Record a spend — validate, deduct from wallet, record transaction."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)

    # Look up the selected option
    option = _find_option(SPEND_SCENARIOS, request.option_id)
    if not option:
        raise HTTPException(status_code=400, detail="Invalid option selected.")

    cost = Decimal(str(option["cost"]))

    # "Save Instead" costs nothing — no transaction needed
    if cost == Decimal("0"):
        return SpendResultResponse(
            new_balance=child.wallet.balance,
            spent_amount=Decimal("0"),
            option_name=option["name"],
            consequence=option["consequence"],
            message=option["consequence"],
        )

    # Validate balance
    wallet: Wallet = child.wallet
    if cost > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Aapke paas sirf Rs. {wallet.balance} hain. Rs. {cost} spend nahi ho sakte.",
        )

    # Deduct and record
    wallet.balance -= cost
    txn = Transaction(
        child_id=child.id,
        type="SPEND",
        amount=cost,
        description=option["name"],
    )
    db.add(txn)
    db.commit()
    db.refresh(wallet)

    # Build consequence message
    remaining_for_goal = ""
    # Check if there's an active goal — add educational nudge
    from app.models import Goal
    active_goal = (
        db.query(Goal)
        .filter(Goal.child_id == child.id, Goal.status == "active")
        .first()
    )
    if active_goal:
        remaining = active_goal.target_amount - active_goal.saved_amount
        remaining_for_goal = (
            f" Aapke goal '{active_goal.name}' ke liye save karne mein "
            f"ab thora zyada waqt lag sakta hai."
        )

    message = option["consequence"] + remaining_for_goal

    return SpendResultResponse(
        new_balance=wallet.balance,
        spent_amount=cost,
        option_name=option["name"],
        consequence=option["consequence"],
        message=message,
    )
