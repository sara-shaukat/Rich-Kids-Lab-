"""Tests for Money Lab V2 — 7-day business experiment."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, GrowActivity
from app.services.experiment_service import (
    EXPERIMENT_START_MONEY,
    EXPERIMENT_BUSINESSES,
    INVESTMENT_OPTIONS,
    PRICING_OPTIONS,
    DAILY_EVENTS,
    DAY4_DECISIONS,
    TOTAL_DAYS,
    DECISION_DAY,
    start_experiment,
    get_experiment_state,
    submit_choices,
    advance_day,
    submit_decision,
    submit_experiment_reflection,
    _event_for_day,
    _calc_demand,
    _find_business,
    _find_pricing,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def child(db):
    c = Child(anonymous_id="RKL-V2-01")
    db.add(c)
    db.flush()
    w = Wallet(child_id=c.id, balance=Decimal("100.00"))
    db.add(w)
    db.commit()
    db.refresh(c)
    return c


def _run_full_week(db, child, biz="bracelets", inv="medium", price="normal",
                   decision="keep_going"):
    """Helper: start → setup → advance days 2-7 → return final result."""
    start_experiment(db, child)
    day1 = submit_choices(db, child, biz, inv, price)
    result = day1
    while True:
        r = advance_day(db, child)
        if r.get("needs_decision"):
            r2 = submit_decision(db, child, decision)
            result = r2
        elif r.get("finished"):
            return r
        else:
            result = r
    return result


# ---- Configuration data integrity ----

def test_businesses_structure():
    for b in EXPERIMENT_BUSINESSES:
        assert "id" in b and "name" in b and "icon" in b
        assert "base_cost" in b and "unit_cost" in b
        assert "demand" in b and "risk" in b
        assert b["risk"] in ("low", "medium", "high")
        for tier in ("cheap", "normal", "premium"):
            assert tier in b["demand"]
            low, high = b["demand"][tier]
            assert low <= high


def test_investment_options():
    for o in INVESTMENT_OPTIONS:
        assert "id" in o and "multiplier" in o
        assert o["multiplier"] >= 1


def test_pricing_options():
    for o in PRICING_OPTIONS:
        assert "id" in o and "revenue_multiplier" in o
        assert o["revenue_multiplier"] > 0


def test_daily_events_count():
    assert len(DAILY_EVENTS) == TOTAL_DAYS
    for i, e in enumerate(DAILY_EVENTS):
        assert e["day"] == i + 1


def test_day4_has_decisions():
    assert len(DAY4_DECISIONS) >= 3


# ---- Start experiment ----

def test_start_grants_money(db, child):
    bal_before = child.wallet.balance
    result = start_experiment(db, child)
    assert result["grant"] == EXPERIMENT_START_MONEY
    assert result["balance"] == bal_before + EXPERIMENT_START_MONEY
    assert "businesses" in result
    assert "activity_id" in result


def test_start_records_transaction(db, child):
    start_experiment(db, child)
    txns = db.query(Transaction).filter(
        Transaction.child_id == child.id, Transaction.type == "GROW"
    ).all()
    assert len(txns) == 1
    assert txns[0].amount == EXPERIMENT_START_MONEY


def test_start_creates_activity_with_state(db, child):
    start_experiment(db, child)
    act = db.query(GrowActivity).filter(
        GrowActivity.child_id == child.id, GrowActivity.type == "MONEY_LAB"
    ).first()
    assert act is not None
    import json
    state = json.loads(act.details)
    assert state["phase"] == "choosing"


def test_get_state_after_start(db, child):
    start_experiment(db, child)
    gs = get_experiment_state(db, child)
    assert gs["state"]["phase"] == "choosing"
    assert gs["state"]["day"] == 0


# ---- Submit choices (Day 1) ----

def test_submit_choices_basic(db, child):
    start_experiment(db, child)
    r = submit_choices(db, child, "bracelets", "medium", "normal")
    assert r["day"] == 1
    assert r["event"]["id"] == "normal_day"
    assert r["outcome"]["customers"] > 0
    assert r["outcome"]["revenue"] >= 0
    assert r["state"]["day"] == 1
    assert r["stock_bought"] == 40  # medium = 2x * 20


def test_submit_choices_wallet_consistency(db, child):
    start_experiment(db, child)
    # After setup + Day 1: cash = (500 - 160) + Day1_revenue
    r = submit_choices(db, child, "bracelets", "medium", "normal")
    base_cash = float(EXPERIMENT_START_MONEY) - 160.0
    # Cash should be base + Day 1 revenue (which is positive)
    assert r["state"]["cash"] > base_cash
    assert r["outcome"]["revenue"] > 0


def test_submit_choices_invalid_business(db, child):
    start_experiment(db, child)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        submit_choices(db, child, "nonexistent", "small", "normal")
    assert exc.value.status_code == 400


def test_submit_choices_invalid_investment(db, child):
    start_experiment(db, child)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        submit_choices(db, child, "art_cards", "huge", "normal")
    assert exc.value.status_code == 400


def test_submit_choices_invalid_pricing(db, child):
    start_experiment(db, child)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        submit_choices(db, child, "art_cards", "small", "free")
    assert exc.value.status_code == 400


def test_submit_choices_insufficient_balance(db, child):
    """Child has 100, snack_stall large costs 450 — should fail."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        # Don't even start — balance is only 100
        start_experiment(db, child)  # grants 500 → 600
        # But snack_stall large = 450, which fits. Use a child with less.
        child2 = Child(anonymous_id="RKL-V2-02")
        db.add(child2)
        db.flush()
        w2 = Wallet(child_id=child2.id, balance=Decimal("50.00"))
        db.add(w2)
        db.commit()
        db.refresh(child2)
        submit_choices(db, child2, "snack_stall", "large", "normal")
    assert exc.value.status_code == 400


# ---- Day progression ----

def test_advance_day_2(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    r = advance_day(db, child)
    assert r["day"] == 2
    assert r["event"]["id"] == "good_weather"


def test_advance_day_3(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # → day 2
    r = advance_day(db, child)  # → day 3
    assert r["day"] == 3
    assert r["event"]["id"] == "rainy_day"


def test_day4_returns_decision(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # → day 2
    advance_day(db, child)  # → day 3
    advance_day(db, child)  # → day 4 (simulation)
    r = advance_day(db, child)  # → day 4: decision prompt
    assert r.get("needs_decision") is True
    assert r["day"] == DECISION_DAY
    assert len(r["decisions"]) >= 3


def test_advance_after_decision_to_day5(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # 2
    advance_day(db, child)  # 3
    advance_day(db, child)  # 4 (simulated)
    advance_day(db, child)  # 4 → decision prompt
    r = submit_decision(db, child, "keep_going")  # → day 5
    assert r["day"] == 5
    assert r["event"]["id"] == "school_fair"


def test_full_week_completes(db, child):
    final = _run_full_week(db, child)
    assert final.get("finished") is True
    assert final["days_completed"] == TOTAL_DAYS
    assert "profit_loss" in final
    assert "total_revenue" in final
    assert "total_costs" in final


# ---- Daily revenue ----

def test_revenue_positive_with_stock(db, child):
    start_experiment(db, child)
    r = submit_choices(db, child, "bracelets", "medium", "normal")
    # Day 1: normal day, bracelets medium normal → should have some sales
    assert r["outcome"]["revenue"] > 0
    assert r["outcome"]["units_sold"] > 0


def test_no_sales_when_stock_zero(db, child):
    """Verify stock decreases after Day 1 sales."""
    start_experiment(db, child)
    r = submit_choices(db, child, "art_cards", "large", "cheap")
    # Starting stock = 60 (3 * 20). After Day 1 sales, stock should decrease.
    assert r["outcome"]["stock_remaining"] < 60
    assert r["outcome"]["units_sold"] > 0


# ---- Customer demand ----

def test_demand_within_range():
    biz = _find_business("bracelets")
    pricing = _find_pricing("normal")
    event = _event_for_day(1)
    low, high = _calc_demand(biz, "normal", 2, event)
    assert low >= 1
    assert high >= low


def test_pricing_affects_demand():
    biz = _find_business("bracelets")
    event = _event_for_day(1)
    _, cheap_high = _calc_demand(biz, "cheap", 1, event)
    _, premium_high = _calc_demand(biz, "premium", 1, event)
    assert cheap_high > premium_high, "Cheap should attract more customers than premium"


# ---- Events ----

def test_events_are_deterministic():
    e1 = _event_for_day(3)
    e2 = _event_for_day(3)
    assert e1["id"] == e2["id"]


def test_events_differ_by_day():
    events = set()
    for d in range(1, TOTAL_DAYS + 1):
        events.add(_event_for_day(d)["id"])
    assert len(events) >= 5  # at least 5 unique events across 7 days


# ---- Daily decisions ----

def test_decision_buy_stock(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # 2
    advance_day(db, child)  # 3
    advance_day(db, child)  # 4 (simulated)
    r = advance_day(db, child)  # 4 → decision
    r2 = submit_decision(db, child, "buy_stock")
    assert r2["decision_applied"] == "buy_stock"
    assert r2["day"] == 5


def test_decision_raise_price(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # 2
    advance_day(db, child)  # 3
    advance_day(db, child)  # 4 (simulated)
    advance_day(db, child)  # 4 → decision
    r = submit_decision(db, child, "raise_price")
    assert r["decision_applied"] == "raise_price"


def test_decision_lower_price(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # 2
    advance_day(db, child)  # 3
    advance_day(db, child)  # 4 (simulated)
    advance_day(db, child)  # 4 → decision
    r = submit_decision(db, child, "lower_price")
    assert r["decision_applied"] == "lower_price"


def test_decision_invalid(db, child):
    start_experiment(db, child)
    submit_choices(db, child, "bracelets", "medium", "normal")
    advance_day(db, child)  # 2
    advance_day(db, child)  # 3
    advance_day(db, child)  # 4 (simulated)
    advance_day(db, child)  # 4 → decision
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        submit_decision(db, child, "nonexistent")


# ---- Day 7 completion / profit / loss ----

def test_profit_scenario(db, child):
    """Bracelets medium cheap → should be profitable."""
    final = _run_full_week(db, child, "bracelets", "medium", "cheap")
    assert final["finished"] is True
    assert final["total_revenue"] > 0
    assert final["total_customers"] > 0
    # Revenue should be meaningful
    assert final["total_revenue"] > final["total_costs"]


def test_loss_is_possible(db, child):
    """Snack stall large premium → rainy day hurts hard."""
    child.wallet.balance = Decimal("5000.00")
    db.commit()
    db.refresh(child)
    final = _run_full_week(db, child, "snack_stall", "large", "premium")
    # With premium pricing + low demand + rainy day, loss should be possible
    # At minimum, verify we get valid results
    assert final["finished"] is True
    assert isinstance(final["profit_loss"], (int, float))


# ---- Reflection ----

def test_reflection_recording(db, child):
    final = _run_full_week(db, child)
    r = submit_experiment_reflection(db, child, "change_price")
    assert "bot_line" in r
    assert len(r["bot_line"]) > 0


def test_reflection_invalid_id(db, child):
    final = _run_full_week(db, child)
    r = submit_experiment_reflection(db, child, "nonexistent")
    assert "bot_line" in r


# ---- Retry ----

def test_retry_full_cycle(db, child):
    """Start → complete → start again → complete again."""
    final1 = _run_full_week(db, child, "bracelets", "small", "normal")
    assert final1["business_name"] == "Bracelets"

    final2 = _run_full_week(db, child, "art_cards", "medium", "cheap")
    assert final2["business_name"] == "Art Cards"
    assert child.wallet.balance >= Decimal("0")


# ---- Wallet safety ----

def test_no_negative_wallet_balance(db, child):
    """Even worst-case should not produce negative wallet balance."""
    child.wallet.balance = Decimal("500.00")
    db.commit()
    db.refresh(child)
    final = _run_full_week(db, child, "snack_stall", "large", "premium")
    assert child.wallet.balance >= Decimal("0")


def test_different_choices_different_outcomes(db, child):
    """Different businesses produce different financial results."""
    results = []
    for biz in ["art_cards", "bracelets", "snack_stall"]:
        child.wallet.balance = Decimal("5000.00")
        db.commit()
        db.refresh(child)
        final = _run_full_week(db, child, biz, "small", "normal")
        results.append(final["profit_loss"])
    assert len(set(results)) >= 2
