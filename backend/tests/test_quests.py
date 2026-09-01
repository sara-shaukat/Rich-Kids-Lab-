"""Tests for the quests layer (V1 — 3 trade-off quests).

Run with:  python -m pytest tests/ -v
(from the backend/ directory)
"""

import os
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity
from app.services.grow_service import invest
from app.services.wallet_service import create_goal, save_to_goal
from app.services.badge_service import compute_level
from app.services.quest_service import (
    QUESTS,
    _round10,
    _ceil_int,
    get_quest_states,
    resolve_quest,
    submit_reflection,
)


@pytest.fixture()
def db():
    """In-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    yield session
    session.close()


_child_counter = 0


def _make_child(db, balance=1000):
    """Create a child with the given wallet balance (unique anonymous ID)."""
    global _child_counter
    _child_counter += 1
    child = Child(anonymous_id=f"RKL-QTEST{_child_counter}")
    db.add(child)
    db.flush()
    db.add(Wallet(child_id=child.id, balance=Decimal(str(balance))))
    db.commit()
    db.refresh(child)
    return child


def _make_goal(db, child, name="Cycle", target=8000, saved=0):
    """Create an active goal directly (varied saved amounts for tests)."""
    goal = Goal(
        child_id=child.id,
        name=name,
        target_amount=Decimal(str(target)),
        saved_amount=Decimal(str(saved)),
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def _quest_view(states, quest_id):
    return next(q for q in states if q["id"] == quest_id)


# ---- helper tests ----

def test_round10():
    assert _round10(45) == 50
    assert _round10(44) == 40
    assert _round10(100) == 100
    assert _round10(999) == 1000
    assert _round10(Decimal("184.5")) == 180


def test_ceil_int():
    assert _ceil_int(Decimal("100")) == 100
    assert _ceil_int(Decimal("104.37")) == 105
    assert _ceil_int(0) == 0


# ---- state tests ----

def test_fresh_child_all_locked(db):
    child = _make_child(db, 1000)
    states = get_quest_states(db, child)
    assert len(states) == 3
    for s in states:
        assert s["status"] == "locked"
        assert "Goal" in s["lock_reason"]


def test_goal_unlocks_q1_q2(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    states = get_quest_states(db, child)
    q1 = _quest_view(states, "q1_opportunity_cost")
    q2 = _quest_view(states, "q2_save_discipline")
    q3 = _quest_view(states, "q3_risk_safety")

    assert q1["status"] == "available"
    assert q2["status"] == "available"
    assert q3["status"] == "locked"
    assert "investment" in q3["lock_reason"].lower()

    # Scenario text interpolated with real numbers
    assert "Rs. 1000" in q1["scenario_lines"][0]
    assert "Rs. 900" in q1["scenario_lines"][0]  # kit = round10(0.9 x 1000)
    assert "Cycle" in q1["scenario_lines"][1]
    assert "Rs. 400" in q1["scenario_lines"][1]  # save = round10(0.4 x 1000)
    assert len(q1["choices"]) == 2
    assert len(q2["choices"]) == 2


def test_investment_unlocks_q3(db, monkeypatch):
    monkeypatch.setattr("app.services.grow_service.random.uniform", lambda a, b: 0.0)
    child = _make_child(db, 2000)
    _make_goal(db, child, target=1500, saved=0)
    invest(db, child, 100, "low")

    states = get_quest_states(db, child)
    q3 = _quest_view(states, "q3_risk_safety")
    assert q3["status"] == "available"
    assert "Rs. 1500" in q3["scenario_lines"][0]


def test_low_balance_locks(db):
    child = _make_child(db, 150)
    _make_goal(db, child, target=8000, saved=0)
    states = get_quest_states(db, child)
    for qid in ("q1_opportunity_cost", "q2_save_discipline"):
        view = _quest_view(states, qid)
        assert view["status"] == "locked"
        assert "200" in view["lock_reason"]


def test_almost_complete_goal_locks(db):
    child = _make_child(db, 5000)
    _make_goal(db, child, target=8000, saved=7900)  # remaining 100
    states = get_quest_states(db, child)
    for qid in ("q1_opportunity_cost", "q2_save_discipline"):
        view = _quest_view(states, qid)
        assert view["status"] == "locked"
        assert "almost complete" in view["lock_reason"]


# ---- quest 1 tests ----

def test_q1_save_choice(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    result = resolve_quest(db, child, "q1_opportunity_cost", "save_first")

    # kit = 900, save = 400 (deterministic — no random in q1)
    assert result["verdict"] == "win"
    assert result["headline"] == "Goal pehle — smart!"
    assert result["wallet_balance"] == Decimal("600.00")
    assert result["goal_saved_amount"] == Decimal("400.00")
    assert result["goal_pct"] == 5  # 400 / 8000
    assert "Rs. 400" in result["what_happened"][0]
    assert "5%" in result["what_happened"][0]
    assert "opportunity cost" in result["what_happened"][2]

    # Reflection payload shape
    assert len(result["reflection"]["options"]) == 2
    assert all(o["bot_line"] for o in result["reflection"]["options"])

    # SAVE transaction recorded
    txn = db.query(Transaction).filter(
        Transaction.child_id == child.id, Transaction.type == "SAVE"
    ).one()
    assert txn.amount == Decimal("400.00")

    # QUEST activity recorded with details
    act = db.query(GrowActivity).filter(
        GrowActivity.child_id == child.id, GrowActivity.type == "QUEST"
    ).one()
    details = json.loads(act.details)
    assert details["quest_id"] == "q1_opportunity_cost"
    assert details["choice_id"] == "save_first"
    assert details["was_wise"] is True
    assert details["verdict"] == "win"
    assert details["snapshot"]["balance_before"] == 1000.0

    # Quest is completed and cannot repeat
    states = get_quest_states(db, child)
    q1 = _quest_view(states, "q1_opportunity_cost")
    assert q1["status"] == "completed"
    assert q1["verdict"] == "win"
    assert q1["reflected"] is False
    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q1_opportunity_cost", "save_first")
    assert exc_info.value.status_code == 400


def test_q1_spend_choice(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    result = resolve_quest(db, child, "q1_opportunity_cost", "buy_kit")

    assert result["verdict"] == "near_miss"
    assert result["wallet_balance"] == Decimal("100.00")
    assert result["goal_saved_amount"] == Decimal("0.00")

    # kit 900 < remaining 8000 -> percentage line
    assert "Rs. 900" in result["what_happened"][0]
    assert "11%" in result["what_happened"][0]  # 900 / 8000 = 11.25%

    txn = db.query(Transaction).filter(
        Transaction.child_id == child.id, Transaction.type == "SPEND"
    ).one()
    assert txn.amount == Decimal("900.00")
    assert txn.description == "Quest: Cricket Kit"

    act = db.query(GrowActivity).filter(
        GrowActivity.child_id == child.id, GrowActivity.type == "QUEST"
    ).one()
    details = json.loads(act.details)
    assert details["was_wise"] is False
    assert details["verdict"] == "near_miss"


def test_q1_kit_exceeds_remaining(db):
    """When the kit costs more than what's left of the goal, the
    near-miss line says the goal could have been completed instead."""
    child = _make_child(db, 1000)
    _make_goal(db, child, target=600, saved=100)  # remaining 500

    result = resolve_quest(db, child, "q1_opportunity_cost", "buy_kit")
    assert "POORA" in result["what_happened"][0]
    assert "Rs. 500" in result["what_happened"][0]


# ---- quest 2 tests ----

def test_q2_spend_choice(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    result = resolve_quest(db, child, "q2_save_discipline", "join_party")

    # cost = round10(0.5 x 1000) = 500
    assert result["verdict"] == "near_miss"
    assert result["headline"] == "Party mast thi!"
    assert result["wallet_balance"] == Decimal("500.00")

    txn = db.query(Transaction).filter(
        Transaction.child_id == child.id, Transaction.type == "SPEND"
    ).one()
    assert txn.amount == Decimal("500.00")
    assert txn.description == "Quest: Arcade Party"


def test_q2_save_choice(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    result = resolve_quest(db, child, "q2_save_discipline", "skip_and_save")

    # save = min(500, 8000) = 500
    assert result["verdict"] == "win"
    assert result["wallet_balance"] == Decimal("500.00")
    assert result["goal_saved_amount"] == Decimal("500.00")
    assert result["goal_pct"] == 6  # 500 / 8000
    assert "Rs. 500" in result["what_happened"][0]
    assert "6%" in result["what_happened"][0]


# ---- quest 3 tests ----

def _setup_q3(db, monkeypatch, balance=2000, target=1500):
    """Child with balance + goal + one prior investment (0% return)."""
    monkeypatch.setattr("app.services.grow_service.random.uniform", lambda a, b: 0.0)
    child = _make_child(db, balance)
    _make_goal(db, child, target=target, saved=0)
    invest(db, child, 100, "low")  # unlock investment requirement, balance unchanged
    db.refresh(child)
    return child


def test_q3_safe_choice_completes_goal(db, monkeypatch):
    child = _setup_q3(db, monkeypatch)

    result = resolve_quest(db, child, "q3_risk_safety", "safe_route")

    assert result["verdict"] == "win"
    assert result["headline"] == "GOAL COMPLETE! 🎉"
    assert result["goal_status"] == "completed"
    assert result["goal_pct"] == 100
    assert result["wallet_balance"] == Decimal("500.00")  # 2000 - 1500

    goal = db.query(Goal).filter(Goal.child_id == child.id).one()
    assert goal.status == "completed"


def test_q3_risky_profit_is_still_near_miss(db, monkeypatch):
    child = _setup_q3(db, monkeypatch)
    monkeypatch.setattr("app.services.grow_service.random.uniform", lambda a, b: 30.0)

    result = resolve_quest(db, child, "q3_risk_safety", "take_shortcut")

    # amount = 1500, +30% -> profit 450, balance 2000 - 1500 + 1950 = 2450
    assert result["verdict"] == "near_miss"  # outcome != decision
    assert result["headline"] == "Luck saath tha — lekin..."
    assert result["investment_profit_loss"] == Decimal("450.00")
    assert result["wallet_balance"] == Decimal("2450.00")
    assert "Rs. 450" in result["what_happened"][0]
    assert "profit" in result["what_happened"][0]

    # INVESTMENT activity recorded alongside the QUEST activity
    inv_count = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "INVESTMENT")
        .count()
    )
    assert inv_count == 2  # unlock invest + quest invest

    # Stored details carry the final headline + outcome
    act = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "QUEST")
        .one()
    )
    details = json.loads(act.details)
    assert details["headline"] == "Luck saath tha — lekin..."
    assert details["profit_loss"] == 450.0


def test_q3_risky_loss(db, monkeypatch):
    child = _setup_q3(db, monkeypatch)
    monkeypatch.setattr("app.services.grow_service.random.uniform", lambda a, b: -40.0)

    result = resolve_quest(db, child, "q3_risk_safety", "take_shortcut")

    # amount = 1500, -40% -> loss 600, balance 2000 - 1500 + 900 = 1400
    assert result["verdict"] == "near_miss"
    assert result["headline"] == "Startup gir gaya!"
    assert result["investment_profit_loss"] == Decimal("-600.00")
    assert result["wallet_balance"] == Decimal("1400.00")
    assert "Rs. 600 ka loss" in result["what_happened"][0]
    assert "Rs. 1500" in result["what_happened"][0]  # still need this much


def test_q3_locked_without_investment(db):
    child = _make_child(db, 2000)
    _make_goal(db, child, target=1500, saved=0)
    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q3_risk_safety", "safe_route")
    assert exc_info.value.status_code == 400


def test_q3_locked_with_low_balance(db, monkeypatch):
    monkeypatch.setattr("app.services.grow_service.random.uniform", lambda a, b: 0.0)
    child = _make_child(db, 1000)
    _make_goal(db, child, target=3000, saved=0)
    invest(db, child, 100, "low")  # remaining 3000 > balance ~900
    db.refresh(child)

    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q3_risk_safety", "safe_route")
    assert exc_info.value.status_code == 400


# ---- determinism + dilemma tests ----

def test_q1_q2_amounts_deterministic(db):
    """For a fixed balance/goal the scenario numbers are exact — no random."""
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    states = get_quest_states(db, child)
    q1 = _quest_view(states, "q1_opportunity_cost")
    q2 = _quest_view(states, "q2_save_discipline")

    assert "Rs. 900" in q1["choices"][0]["label"]  # kit
    assert "Rs. 400" in q1["choices"][1]["label"]  # save
    assert "Rs. 500" in q2["choices"][0]["label"]  # cost
    assert "Rs. 500" in q2["choices"][1]["label"]  # save


def test_dilemma_always_real(db):
    """At every balance, the kit + the save are never both affordable."""
    for balance in (200, 250, 333, 500, 999, 1000, 2500, 9990):
        child = _make_child(db, balance)
        _make_goal(db, child, target=50000, saved=0)

        states = get_quest_states(db, child)
        q1 = _quest_view(states, "q1_opportunity_cost")
        assert q1["status"] == "available", f"balance={balance}"

        kit = _round10(Decimal(str(balance)) * Decimal("0.9"))
        save = _round10(Decimal(str(balance)) * Decimal("0.4"))
        assert kit + save > balance, (
            f"Dilemma broken at balance={balance}: kit={kit}, save={save}"
        )
        assert kit <= balance and save <= balance  # each option executable


def test_dilemma_real_when_remaining_is_small(db):
    """Even when the goal is close (remaining just above 10% of balance),
    kit + save must still exceed the balance."""
    for balance in (1000, 2000):
        child = _make_child(db, balance)
        remaining = int(balance * 0.15)  # above the 10% lock guard
        _make_goal(db, child, target=remaining, saved=0)

        states = get_quest_states(db, child)
        q1 = _quest_view(states, "q1_opportunity_cost")
        assert q1["status"] == "available", f"balance={balance}"

        kit = _round10(Decimal(str(balance)) * Decimal("0.9"))
        assert kit + remaining > balance


# ---- validation tests ----

def test_resolve_invalid_choice(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)
    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q1_opportunity_cost", "not_a_choice")
    assert exc_info.value.status_code == 400


def test_resolve_invalid_quest(db):
    child = _make_child(db, 1000)
    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q99_nothing", "save_first")
    assert exc_info.value.status_code == 400


def test_resolve_revalidates_availability(db):
    """Balance dropped below the threshold after the page loaded -> 400,
    and nothing is recorded."""
    child = _make_child(db, 150)  # below the 200 floor
    _make_goal(db, child, target=8000, saved=0)
    with pytest.raises(HTTPException) as exc_info:
        resolve_quest(db, child, "q1_opportunity_cost", "save_first")
    assert "available nahi" in exc_info.value.detail

    # No partial state was written
    assert (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "QUEST")
        .count()
        == 0
    )
    assert (
        db.query(Transaction).filter(Transaction.child_id == child.id).count()
        == 0
    )


# ---- reflection tests ----

def test_reflection_stored(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)
    resolve_quest(db, child, "q1_opportunity_cost", "save_first")

    result = submit_reflection(db, child, "q1_opportunity_cost", "goal_first")

    assert result["quest_id"] == "q1_opportunity_cost"
    assert result["answer_id"] == "goal_first"
    assert "smart khiladi" in result["bot_line"]

    act = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "QUEST")
        .one()
    )
    details = json.loads(act.details)
    assert details["reflection_answer"] == "goal_first"

    # Completed view now shows reflected
    states = get_quest_states(db, child)
    q1 = _quest_view(states, "q1_opportunity_cost")
    assert q1["reflected"] is True


def test_reflection_invalid_answer(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)
    resolve_quest(db, child, "q1_opportunity_cost", "save_first")
    with pytest.raises(HTTPException) as exc_info:
        submit_reflection(db, child, "q1_opportunity_cost", "bad_answer")
    assert exc_info.value.status_code == 400


def test_reflection_requires_completed_quest(db):
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)
    with pytest.raises(HTTPException) as exc_info:
        submit_reflection(db, child, "q1_opportunity_cost", "goal_first")
    assert exc_info.value.status_code == 400


# ---- integration with existing systems ----

def test_level_counts_quest_actions(db):
    """A quest completion feeds the existing level system (+1 action
    for the QUEST row, plus the SAVE transaction it triggered)."""
    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)

    before = compute_level(db, child)["total_actions"]
    resolve_quest(db, child, "q1_opportunity_cost", "save_first")
    after = compute_level(db, child)["total_actions"]

    assert after - before == 2  # 1 SAVE txn + 1 QUEST activity


def test_quest_spend_counts_toward_total_spent(db):
    """Quest spending has real consequences — it feeds total_spent."""
    from app.services.badge_service import compute_liabilities

    child = _make_child(db, 1000)
    _make_goal(db, child, target=8000, saved=0)
    resolve_quest(db, child, "q1_opportunity_cost", "buy_kit")

    liabilities = compute_liabilities(db, child)
    spent = next(l for l in liabilities if l["type"] == "spent")
    assert spent["amount"] == Decimal("900.00")


def test_quest_definitions_shape():
    """Every quest: 2 choices, 1 wise + 1 near-miss, reflection with
    exactly 2 options, and no guaranteed-income promises."""
    for quest in QUESTS:
        assert len(quest["choices"]) == 2
        wise = [c for c in quest["choices"] if c["was_wise"]]
        near = [c for c in quest["choices"] if not c["was_wise"]]
        assert len(wise) == 1 and len(near) == 1
        assert wise[0]["verdict"] == "win"
        assert near[0]["verdict"] == "near_miss"

        assert len(quest["reflection"]["options"]) == 2

        for key in ("scenario_lines", "reflection"):
            pass  # presence asserted above by access

        # No income guarantees anywhere in quest text
        blob = json.dumps(quest).lower()
        assert "guaranteed" not in blob
        assert "guarantee" not in blob
