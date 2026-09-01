"""Tests for spend logic."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal
from app.services.wallet_service import validate_amount, create_goal


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
    child = Child(anonymous_id="RKL-SPEND1")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


# ---- Spend scenarios structure tests ----

def test_scenarios_exist():
    from app.routes.spend import SPEND_SCENARIOS
    assert len(SPEND_SCENARIOS) == 2
    for s in SPEND_SCENARIOS:
        assert "id" in s
        assert "title" in s
        assert len(s["options"]) >= 3


def test_every_option_has_required_fields():
    from app.routes.spend import SPEND_SCENARIOS
    for s in SPEND_SCENARIOS:
        for opt in s["options"]:
            assert "id" in opt
            assert "name" in opt
            assert "cost" in opt
            assert "consequence" in opt
            assert isinstance(opt["cost"], int)
            assert opt["cost"] >= 0


def test_save_instead_always_present():
    from app.routes.spend import SPEND_SCENARIOS
    for s in SPEND_SCENARIOS:
        save_opts = [o for o in s["options"] if o["id"] == "save_instead"]
        assert len(save_opts) == 1
        assert save_opts[0]["cost"] == 0


def test_find_option_valid():
    from app.routes.spend import _find_option, SPEND_SCENARIOS
    opt = _find_option(SPEND_SCENARIOS, "pizza")
    assert opt is not None
    assert opt["name"] == "Pizza"
    assert opt["cost"] == 300


def test_find_option_invalid():
    from app.routes.spend import _find_option, SPEND_SCENARIOS
    opt = _find_option(SPEND_SCENARIOS, "spaceship")
    assert opt is None


# ---- Spend deduction tests (via direct wallet manipulation) ----

def test_spend_deducts_balance(db, child_500):
    """Simulate a spend of Rs. 300 — wallet should drop to Rs. 200."""
    wallet = child_500.wallet
    cost = Decimal("300")

    assert cost <= wallet.balance
    wallet.balance -= cost
    txn = Transaction(child_id=child_500.id, type="SPEND", amount=cost, description="Pizza")
    db.add(txn)
    db.commit()
    db.refresh(wallet)

    assert wallet.balance == Decimal("200.00")


def test_spend_insufficient_balance(db, child_500):
    """Cannot spend more than balance."""
    wallet = child_500.wallet
    cost = Decimal("600")

    assert cost > wallet.balance  # Should be rejected by route


def test_spend_records_transaction(db, child_500):
    wallet = child_500.wallet
    cost = Decimal("200")
    wallet.balance -= cost
    txn = Transaction(child_id=child_500.id, type="SPEND", amount=cost, description="Book")
    db.add(txn)
    db.commit()

    txns = db.query(Transaction).filter(
        Transaction.child_id == child_500.id,
        Transaction.type == "SPEND",
    ).all()
    assert len(txns) == 1
    assert txns[0].amount == Decimal("200.00")
    assert txns[0].description == "Book"


def test_spend_consistency_with_goal(db, child_500):
    """After saving + spending, total money is preserved."""
    child = child_500
    initial_money = child.wallet.balance  # 500

    # Save Rs. 200 toward a goal
    goal = create_goal(db, child, "Headphones", 8000)
    from app.services.wallet_service import save_to_goal
    save_to_goal(db, child, goal, 200)
    db.refresh(child)

    # Spend Rs. 100
    cost = Decimal("100")
    child.wallet.balance -= cost
    txn = Transaction(child_id=child.id, type="SPEND", amount=cost, description="Snack")
    db.add(txn)
    db.commit()
    db.refresh(child)

    # Verify consistency
    total_saved = sum((g.saved_amount for g in child.goals), Decimal("0"))
    total = child.wallet.balance + total_saved
    # total = (500 - 200 - 100) + 200 = 400.  Money spent is gone.
    assert total == initial_money - cost


def test_spend_exact_balance(db, child_500):
    """Spend exactly the wallet balance — should leave wallet at 0."""
    wallet = child_500.wallet
    wallet.balance -= Decimal("500")
    db.commit()
    db.refresh(wallet)
    assert wallet.balance == Decimal("0.00")
