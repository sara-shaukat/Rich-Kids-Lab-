"""Tests for wallet service and goal/savings logic.

Run with:  python -m pytest tests/ -v
(from the backend/ directory)
"""

import os
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal
from app.services.wallet_service import (
    validate_amount,
    create_goal,
    save_to_goal,
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


@pytest.fixture()
def child_with_wallet(db):
    """Create a child with Rs. 500 wallet."""
    child = Child(anonymous_id="RKL-TEST1")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


# ---- validate_amount tests ----

def test_validate_positive_amount():
    assert validate_amount(100) == Decimal("100")
    assert validate_amount("50") == Decimal("50")
    assert validate_amount(Decimal("99.99")) == Decimal("99.99")


def test_validate_zero_rejected():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_amount(0)
    assert exc_info.value.status_code == 400


def test_validate_negative_rejected():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_amount(-50)
    assert exc_info.value.status_code == 400


def test_validate_garbage_rejected():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        validate_amount("abc")
    assert exc_info.value.status_code == 400


# ---- create_goal tests ----

def test_create_goal_success(db, child_with_wallet):
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    assert goal.name == "Headphones"
    assert goal.target_amount == Decimal("8000.00")
    assert goal.saved_amount == Decimal("0.00")
    assert goal.status == "active"


def test_create_goal_empty_name_rejected(db, child_with_wallet):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        create_goal(db, child_with_wallet, "", 1000)


def test_create_goal_zero_target_rejected(db, child_with_wallet):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        create_goal(db, child_with_wallet, "Test", 0)


def test_only_one_active_goal(db, child_with_wallet):
    from fastapi import HTTPException
    create_goal(db, child_with_wallet, "Headphones", 8000)
    with pytest.raises(HTTPException) as exc_info:
        create_goal(db, child_with_wallet, "Bike", 50000)
    assert exc_info.value.status_code == 400


# ---- save_to_goal tests ----

def test_save_basic(db, child_with_wallet):
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    result = save_to_goal(db, child_with_wallet, goal, 200)

    assert result["wallet_balance"] == Decimal("300.00")
    assert result["goal_saved_amount"] == Decimal("200.00")
    assert result["goal_status"] == "active"
    assert result["saved_this_time"] == Decimal("200.00")


def test_save_multiple_times(db, child_with_wallet):
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)

    save_to_goal(db, child_with_wallet, goal, 200)
    db.refresh(child_with_wallet)
    result = save_to_goal(db, child_with_wallet, goal, 150)

    assert result["wallet_balance"] == Decimal("150.00")
    assert result["goal_saved_amount"] == Decimal("350.00")


def test_save_insufficient_balance(db, child_with_wallet):
    from fastapi import HTTPException
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    with pytest.raises(HTTPException) as exc_info:
        save_to_goal(db, child_with_wallet, goal, 600)
    assert exc_info.value.status_code == 400


def test_save_negative_rejected(db, child_with_wallet):
    from fastapi import HTTPException
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    with pytest.raises(HTTPException):
        save_to_goal(db, child_with_wallet, goal, -50)


def test_save_exact_balance(db, child_with_wallet):
    """Save exactly the wallet balance — should leave wallet at 0."""
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    result = save_to_goal(db, child_with_wallet, goal, 500)

    assert result["wallet_balance"] == Decimal("0.00")
    assert result["goal_saved_amount"] == Decimal("500.00")


def test_save_completes_goal(db, child_with_wallet):
    """When saved_amount >= target_amount, goal status becomes 'completed'."""
    child = child_with_wallet
    # Give more money
    child.wallet.balance = Decimal("10000.00")
    db.commit()
    db.refresh(child)

    goal = create_goal(db, child, "Headphones", 8000)
    result = save_to_goal(db, child, goal, 8000)

    assert result["goal_status"] == "completed"
    assert result["goal_saved_amount"] == Decimal("8000.00")


def test_save_records_transaction(db, child_with_wallet):
    """A SAVE transaction should be created."""
    goal = create_goal(db, child_with_wallet, "Headphones", 8000)
    save_to_goal(db, child_with_wallet, goal, 200)

    txns = db.query(Transaction).filter(
        Transaction.child_id == child_with_wallet.id,
        Transaction.type == "SAVE",
    ).all()
    assert len(txns) == 1
    assert txns[0].amount == Decimal("200.00")
    assert "Headphones" in txns[0].description


def test_consistency_invariant(db, child_with_wallet):
    """Total virtual money = wallet.balance + SUM(goals.saved_amount)."""
    child = child_with_wallet
    initial_money = child.wallet.balance  # 500

    goal = create_goal(db, child, "Headphones", 8000)
    save_to_goal(db, child, goal, 200)
    db.refresh(child)

    # Recalculate total
    total_saved = sum(
        (g.saved_amount for g in child.goals),
        Decimal("0"),
    )
    current_total = child.wallet.balance + total_saved

    assert current_total == initial_money, (
        f"Consistency invariant broken! "
        f"Expected {initial_money}, got {current_total} "
        f"(wallet={child.wallet.balance}, saved={total_saved})"
    )


def test_new_goal_after_completion(db, child_with_wallet):
    """After completing a goal, a new goal can be created."""
    child = child_with_wallet
    child.wallet.balance = Decimal("10000.00")
    db.commit()
    db.refresh(child)

    goal1 = create_goal(db, child, "Headphones", 1000)
    save_to_goal(db, child, goal1, 1000)
    assert goal1.status == "completed"

    # Now create a new goal — should succeed
    goal2 = create_goal(db, child, "Bike", 5000)
    assert goal2.status == "active"
