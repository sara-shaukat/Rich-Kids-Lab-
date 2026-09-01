"""Tests for Dashboard V2 — badges, level, assets, liabilities, mascot."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity

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
    BADGE_DEFINITIONS,
    LEVEL_DEFINITIONS,
)
from app.services.mascot_lines import get_mascot_line, get_welcome_line


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def child_500(db):
    child = Child(anonymous_id="RKL-VIBE1")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


def add_save_txn(db, child, amount):
    txn = Transaction(child_id=child.id, type="SAVE", amount=Decimal(str(amount)), description="Saved")
    db.add(txn)
    db.commit()


def add_spend_txn(db, child, amount):
    txn = Transaction(child_id=child.id, type="SPEND", amount=Decimal(str(amount)), description="Spent")
    db.add(txn)
    db.commit()


def add_give_txn(db, child, amount):
    txn = Transaction(child_id=child.id, type="GIVE", amount=Decimal(str(amount)), description="Donated")
    db.add(txn)
    db.commit()


def add_business_activity(db, child, idea="Test Business", profit=100, cost=50):
    details = {
        "idea": idea,
        "cost": cost,
        "expected_profit_min": 50,
        "expected_profit_max": 200,
        "actual_revenue": cost + profit,
        "actual_profit": profit,
        "skills": ["test"],
    }
    act = GrowActivity(child_id=child.id, type="BUSINESS", details=json.dumps(details))
    db.add(act)
    db.commit()


def add_investment_activity(db, child, risk="low", invested=100, profit_loss=10):
    outcome = invested + profit_loss
    details = {
        "initial_amount": invested,
        "risk_level": risk,
        "return_percentage": 5.0,
        "outcome_amount": outcome,
        "profit_loss": profit_loss,
    }
    act = GrowActivity(child_id=child.id, type="INVESTMENT", details=json.dumps(details))
    db.add(act)
    db.commit()


def add_skill_activity(db, child):
    details = {"name": "Drawing", "category": "art", "practice_answer": "test", "earning_potential": "good"}
    act = GrowActivity(child_id=child.id, type="SKILL", details=json.dumps(details))
    db.add(act)
    db.commit()


# ---- Badge Tests ----

def test_no_badges_initially(db, child_500):
    earned = compute_badges(db, child_500)
    assert len(earned) == 0


def test_first_save_badge(db, child_500):
    add_save_txn(db, child_500, 50)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "first_save" in ids


def test_first_business_badge(db, child_500):
    add_business_activity(db, child_500)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "first_business" in ids


def test_first_give_badge(db, child_500):
    add_give_txn(db, child_500, 50)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "first_give" in ids


def test_big_spender_badge(db, child_500):
    child_500.wallet.balance -= Decimal("250")
    db.commit()
    add_spend_txn(db, child_500, 250)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "big_spender" in ids


def test_big_spender_not_earned_under_200(db, child_500):
    child_500.wallet.balance -= Decimal("100")
    db.commit()
    add_spend_txn(db, child_500, 100)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "big_spender" not in ids


def test_profit_maker_badge(db, child_500):
    for i in range(3):
        add_business_activity(db, child_500, idea=f"Business {i}")
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "profit_maker" in ids


def test_explorer_badge(db, child_500):
    add_business_activity(db, child_500)
    add_investment_activity(db, child_500)
    add_skill_activity(db, child_500)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "explorer" in ids


def test_explorer_missing_one_type(db, child_500):
    add_business_activity(db, child_500)
    add_investment_activity(db, child_500)
    earned = compute_badges(db, child_500)
    ids = [b["id"] for b in earned]
    assert "explorer" not in ids


def test_unearned_badges(db, child_500):
    unearned = compute_unearned_badges(db, child_500)
    assert len(unearned) == len(BADGE_DEFINITIONS)
    for b in unearned:
        assert b["earned"] is False
        assert "condition_desc" in b


def test_badge_has_meme_line(db, child_500):
    add_save_txn(db, child_500, 50)
    earned = compute_badges(db, child_500)
    save_badge = next(b for b in earned if b["id"] == "first_save")
    assert "meme_line" in save_badge
    assert len(save_badge["meme_line"]) > 0


# ---- Level Tests ----

def test_level_newbie_initially(db, child_500):
    level = compute_level(db, child_500)
    assert level["level"] == 1
    assert level["name"] == "Newbie"
    assert level["total_actions"] == 0


def test_level_progression(db, child_500):
    # 3 actions = Level 2
    add_save_txn(db, child_500, 50)
    add_spend_txn(db, child_500, 30)
    add_give_txn(db, child_500, 20)
    level = compute_level(db, child_500)
    assert level["level"] == 2
    assert level["name"] == "Seekhne Wala"


def test_level_has_progress_to_next(db, child_500):
    level = compute_level(db, child_500)
    assert "progress_to_next" in level
    assert 0 <= level["progress_to_next"] <= 100


def test_level_max(db, child_500):
    # 11+ actions = Level 4
    for i in range(12):
        add_save_txn(db, child_500, 10)
    level = compute_level(db, child_500)
    assert level["level"] == 4
    assert level["name"] == "Paisa Pro"
    assert level["progress_to_next"] == 100
    assert level["next_level_name"] is None


# ---- Net Worth Tests ----

def test_net_worth_initial(db, child_500):
    net_worth = compute_net_worth(db, child_500)
    assert net_worth == Decimal("500.00")


def test_net_worth_with_goal(db, child_500):
    child_500.wallet.balance -= Decimal("100")
    goal = Goal(child_id=child_500.id, name="Test", target_amount=Decimal("500"), saved_amount=Decimal("100"), status="active")
    db.add(goal)
    db.commit()
    db.refresh(child_500)
    net_worth = compute_net_worth(db, child_500)
    assert net_worth == Decimal("500.00")  # 400 balance + 100 saved


def test_net_worth_with_business_profit(db, child_500):
    add_business_activity(db, child_500, profit=120)
    net_worth = compute_net_worth(db, child_500)
    assert net_worth == Decimal("620.00")  # 500 + 120 profit


# ---- Assets & Liabilities Tests ----

def test_assets_empty_initially(db, child_500):
    assets = compute_assets(db, child_500)
    assert len(assets) == 0


def test_assets_with_profitable_business(db, child_500):
    add_business_activity(db, child_500, idea="Test Biz", profit=100)
    assets = compute_assets(db, child_500)
    assert len(assets) == 1
    assert assets[0]["name"] == "Test Biz"
    assert assets[0]["amount"] == Decimal("100")


def test_assets_with_winning_investment(db, child_500):
    add_investment_activity(db, child_500, profit_loss=20)
    assets = compute_assets(db, child_500)
    assert len(assets) == 1
    assert assets[0]["type"] == "investment"


def test_liabilities_with_losing_investment(db, child_500):
    add_investment_activity(db, child_500, profit_loss=-15)
    liabilities = compute_liabilities(db, child_500)
    inv_loss = [l for l in liabilities if l["type"] == "investment_loss"]
    assert len(inv_loss) == 1
    assert inv_loss[0]["amount"] == Decimal("15")


def test_liabilities_includes_spending(db, child_500):
    add_spend_txn(db, child_500, 100)
    liabilities = compute_liabilities(db, child_500)
    spent = [l for l in liabilities if l["type"] == "spent"]
    assert len(spent) == 1
    assert spent[0]["amount"] == Decimal("100")


# ---- Business & Investment History Tests ----

def test_business_history(db, child_500):
    add_business_activity(db, child_500, idea="Biz A", profit=100)
    add_business_activity(db, child_500, idea="Biz B", profit=50)
    history = compute_business_history(db, child_500)
    assert len(history) == 2
    names = [h["name"] for h in history]
    assert "Biz A" in names
    assert "Biz B" in names


def test_business_history_verdict(db, child_500):
    add_business_activity(db, child_500, profit=100)
    history = compute_business_history(db, child_500)
    assert history[0]["is_profit"] is True
    assert "kaam kiya" in history[0]["verdict"]


def test_investment_history(db, child_500):
    add_investment_activity(db, child_500, profit_loss=20)
    history = compute_investment_history(db, child_500)
    assert len(history) == 1
    assert history[0]["is_profit"] is True


def test_investment_history_loss(db, child_500):
    add_investment_activity(db, child_500, profit_loss=-10)
    history = compute_investment_history(db, child_500)
    assert len(history) == 1
    assert history[0]["is_profit"] is False


# ---- Last Action Type Tests ----

def test_last_action_none_initially(db, child_500):
    assert get_last_action_type(db, child_500) is None


def test_last_action_after_save(db, child_500):
    add_save_txn(db, child_500, 50)
    assert get_last_action_type(db, child_500) == "SAVE"


def test_last_action_after_business(db, child_500):
    add_business_activity(db, child_500)
    last = get_last_action_type(db, child_500)
    assert last == "GROW_BUSINESS"


# ---- Mascot Line Tests ----

def test_mascot_line_zero_balance():
    result = get_mascot_line(None, 0, False, False, 0)
    assert result["mode"] == "roast"
    assert len(result["line"]) > 0


def test_mascot_line_low_balance():
    result = get_mascot_line(None, 30, True, False, 0)
    # Should likely be roast (70% chance) but could be hype
    assert result["mode"] in ("hype", "roast")
    assert len(result["line"]) > 0


def test_mascot_line_after_save():
    # Save can be hype or roast (random), line should be non-empty
    result = get_mascot_line("SAVE", 500, True, False, 0)
    assert result["mode"] in ("hype", "roast")
    assert len(result["line"]) > 0


def test_mascot_line_after_give():
    # Give can be hype or roast (random), but line should be non-empty
    result = get_mascot_line("GIVE", 400, True, False, 0)
    assert result["mode"] in ("hype", "roast")
    assert len(result["line"]) > 0


def test_welcome_line():
    result = get_welcome_line()
    assert result["mode"] == "hype"
    assert len(result["line"]) > 0


# ---- Badge Definitions Tests ----

def test_all_badge_definitions_have_required_fields():
    for b in BADGE_DEFINITIONS:
        assert "id" in b
        assert "name" in b
        assert "icon" in b
        assert "condition_desc" in b
        assert "meme_line" in b
        # No piggy!
        assert "piggy" not in b["icon"].lower()
        assert b["id"] not in ("piggy",)


def test_level_definitions_ordered():
    for i in range(len(LEVEL_DEFINITIONS) - 1):
        assert LEVEL_DEFINITIONS[i]["min_actions"] < LEVEL_DEFINITIONS[i + 1]["min_actions"]
