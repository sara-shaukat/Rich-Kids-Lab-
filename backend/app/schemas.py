"""Pydantic schemas for request/response validation."""

from decimal import Decimal
from pydantic import BaseModel, Field


# --- Session ---

class SessionCreateRequest(BaseModel):
    starting_balance: Decimal = Field(..., gt=0, description="Starting virtual money, must be > 0")


class WalletResponse(BaseModel):
    balance: Decimal

    class Config:
        from_attributes = True


class GoalResponse(BaseModel):
    id: int
    name: str
    target_amount: Decimal
    saved_amount: Decimal
    status: str
    target_date: str | None = None

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    anonymous_id: str
    wallet: WalletResponse
    active_goal: GoalResponse | None = None


class DashboardResponse(BaseModel):
    anonymous_id: str
    balance: Decimal
    total_saved: Decimal
    total_spent: Decimal
    total_grown: Decimal
    total_given: Decimal
    active_goal: GoalResponse | None = None

    # --- V2 fields: vibe makeover ---
    net_worth: Decimal = Decimal("0")
    assets: list[dict] = []
    liabilities: list[dict] = []
    business_history: list[dict] = []
    investment_history: list[dict] = []
    badges: list[dict] = []
    unearned_badges: list[dict] = []
    level: dict = {}
    mascot_line: str = ""
    mascot_mode: str = "hype"
    last_action_type: str | None = None
