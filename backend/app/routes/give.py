"""Give route — simulated donation with impact cards.

Aligned with Alkhidmat Foundation's cause categories.
V1 is simulated only — no real donations.
Future versions may connect to real Alkhidmat donation system.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Child, Wallet, Transaction
from app.services.wallet_service import get_child_by_anonymous_id, validate_amount

router = APIRouter(prefix="/api/transactions", tags=["give"])


# ---------------------------------------------------------------------------
# Cause categories (Alkhidmat-aligned)
# ---------------------------------------------------------------------------

CAUSE_CATEGORIES = [
    {
        "id": "education",
        "name": "Education",
        "icon": "📚",
        "color": "#3498db",
        "description": "Bachon ko parhne ka mauqa dein",
    },
    {
        "id": "food",
        "name": "Food & Nutrition",
        "icon": "🍞",
        "color": "#e67e22",
        "description": "Bhookay bachon ka pait bharein",
    },
    {
        "id": "health",
        "name": "Health & Medicine",
        "icon": "💊",
        "color": "#e74c3c",
        "description": "Beemar logon ki madad karein",
    },
    {
        "id": "shelter",
        "name": "Shelter & Housing",
        "icon": "🏠",
        "color": "#9b59b6",
        "description": "Ghar ki zaroorat poori karein",
    },
    {
        "id": "water",
        "name": "Clean Water",
        "icon": "💧",
        "color": "#27ae60",
        "description": "dusron ko saaf pani dein",
    },
]


# ---------------------------------------------------------------------------
# Impact messages by amount range (from SPEC.md §12)
# ---------------------------------------------------------------------------

IMPACT_TIERS = [
    {
        "min": 10,
        "max": 50,
        "icon": "📓",
        "message": "Rs. {amount} se aap ne ek bachay ke liye notebook khareedny mein madad ki hai!",
        "impact_unit": "1 notebook",
        "impact_count": 1,
    },
    {
        "min": 51,
        "max": 100,
        "icon": "🍞",
        "message": "Rs. {amount} se aap ne ek family ko ek din ka ration deny mein madad ki hai!",
        "impact_unit": "1 family fed",
        "impact_count": 1,
    },
    {
        "min": 101,
        "max": 200,
        "icon": "🎒",
        "message": "Rs. {amount} se aap ne ek bachay ka school bag khareedny mein madad ki hai!",
        "impact_unit": "1 school bag",
        "impact_count": 1,
    },
    {
        "min": 201,
        "max": 500,
        "icon": "💊",
        "message": "Rs. {amount} se ek chhoti si medical help ho sakti hai!",
        "impact_unit": "1 medical aid",
        "impact_count": 1,
    },
    {
        "min": 501,
        "max": None,  # No upper limit
        "icon": "🌟",
        "message": "Rs. {amount} — bohot bara contribution! Aap ne dikhaya ke paisay sirf kharch karne ke liye nahi, madad ke liye bhi hain!",
        "impact_unit": "major contribution",
        "impact_count": 3,
    },
]

EDUCATIONAL_MESSAGE = (
    "Money sirf cheezen khareedne ke liye nahi, doosron ki madad ke liye bhi use ho sakta hai. "
    "Aap ne aaj ek acha kaam kiya!"
)


def get_impact_for_amount(amount: Decimal) -> dict:
    """Return the impact tier for a given amount."""
    amount_int = int(amount)
    for tier in IMPACT_TIERS:
        if tier["max"] is None:
            return tier
        if tier["min"] <= amount_int <= tier["max"]:
            return tier
    # Default to the lowest tier for amounts below Rs. 10
    return IMPACT_TIERS[0]


def get_cause_by_id(cause_id: str) -> dict | None:
    """Find a cause category by id."""
    for c in CAUSE_CATEGORIES:
        if c["id"] == cause_id:
            return c
    return None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GiveRequest(BaseModel):
    anonymous_id: str
    amount: float = Field(..., gt=0)
    cause_id: str | None = None


class GiveResponse(BaseModel):
    new_balance: Decimal
    given_amount: Decimal
    cause_name: str
    cause_icon: str
    impact_message: str
    impact_icon: str
    educational_message: str
    total_given: Decimal
    total_gives: int
    impact_unit: str
    impact_count: int


class CauseCategoryResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    description: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/give/causes", response_model=list[CauseCategoryResponse])
def get_causes():
    """Return available cause categories."""
    return [CauseCategoryResponse(**c) for c in CAUSE_CATEGORIES]


@router.post("/give", response_model=GiveResponse)
def give(request: GiveRequest, db: Session = Depends(get_db)):
    """Record a simulated donation — validate, deduct, record, return impact."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)
    amount = validate_amount(request.amount)

    # Check balance
    wallet: Wallet = child.wallet
    if amount > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Aapke paas sirf Rs. {wallet.balance} hain. Rs. {amount} donate nahi ho sakte.",
        )

    # Look up cause
    cause = get_cause_by_id(request.cause_id) if request.cause_id else None
    cause_name = cause["name"] if cause else "General Donation"
    cause_icon = cause["icon"] if cause else "❤️"

    # Deduct and record
    wallet.balance -= amount
    txn = Transaction(
        child_id=child.id,
        type="GIVE",
        amount=amount,
        description=f"Donated to {cause_name}",
    )
    db.add(txn)
    db.commit()
    db.refresh(wallet)

    # Calculate totals
    total_given = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.child_id == child.id, Transaction.type == "GIVE")
        .scalar()
    )
    total_gives = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.child_id == child.id, Transaction.type == "GIVE")
        .scalar()
    )

    # Get impact tier
    impact = get_impact_for_amount(amount)
    impact_message = impact["message"].format(amount=int(amount))

    return GiveResponse(
        new_balance=wallet.balance,
        given_amount=amount,
        cause_name=cause_name,
        cause_icon=cause_icon,
        impact_message=impact_message,
        impact_icon=impact["icon"],
        educational_message=EDUCATIONAL_MESSAGE,
        total_given=total_given,
        total_gives=total_gives,
        impact_unit=impact["impact_unit"],
        impact_count=impact["impact_count"],
    )
