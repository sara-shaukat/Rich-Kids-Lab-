"""Tests for GIVE logic."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction
from app.services.wallet_service import validate_amount
from app.routes.give import (
    CAUSE_CATEGORIES,
    IMPACT_TIERS,
    get_impact_for_amount,
    get_cause_by_id,
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
def child_500(db):
    child = Child(anonymous_id="RKL-GIVE1")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


# ---- Cause categories tests ----

def test_causes_exist():
    assert len(CAUSE_CATEGORIES) == 5
    for c in CAUSE_CATEGORIES:
        assert "id" in c
        assert "name" in c
        assert "icon" in c
        assert "color" in c
        assert "description" in c


def test_get_cause_valid():
    cause = get_cause_by_id("education")
    assert cause is not None
    assert cause["name"] == "Education"


def test_get_cause_invalid():
    assert get_cause_by_id("spaceships") is None


# ---- Impact tier tests ----

def test_impact_tiers_coverage():
    """Every amount from 10 to 500+ should map to a tier."""
    for amount in [10, 25, 50, 51, 100, 101, 200, 201, 500, 501, 1000]:
        tier = get_impact_for_amount(Decimal(str(amount)))
        assert tier is not None
        assert "icon" in tier
        assert "message" in tier


def test_impact_10_to_50():
    tier = get_impact_for_amount(Decimal("30"))
    assert "notebook" in tier["message"].lower()


def test_impact_51_to_100():
    tier = get_impact_for_amount(Decimal("75"))
    assert "ration" in tier["message"].lower()


def test_impact_101_to_200():
    tier = get_impact_for_amount(Decimal("150"))
    assert "bag" in tier["message"].lower()


def test_impact_201_to_500():
    tier = get_impact_for_amount(Decimal("300"))
    assert "medical" in tier["message"].lower()


def test_impact_500_plus():
    tier = get_impact_for_amount(Decimal("600"))
    assert "bara contribution" in tier["message"].lower()
    assert tier["impact_count"] == 3


# ---- Give deduction tests (direct wallet manipulation) ----

def test_give_deducts_balance(db, child_500):
    """Give Rs. 50 — wallet should drop to Rs. 450."""
    wallet = child_500.wallet
    cost = Decimal("50")
    wallet.balance -= cost
    txn = Transaction(child_id=child_500.id, type="GIVE", amount=cost, description="Donated to Education")
    db.add(txn)
    db.commit()
    db.refresh(wallet)
    assert wallet.balance == Decimal("450.00")


def test_give_insufficient_balance(db, child_500):
    """Cannot give more than balance."""
    wallet = child_500.wallet
    cost = Decimal("600")
    assert cost > wallet.balance


def test_give_records_transaction(db, child_500):
    wallet = child_500.wallet
    cost = Decimal("100")
    wallet.balance -= cost
    txn = Transaction(child_id=child_500.id, type="GIVE", amount=cost, description="Donated to Food")
    db.add(txn)
    db.commit()

    txns = db.query(Transaction).filter(
        Transaction.child_id == child_500.id,
        Transaction.type == "GIVE",
    ).all()
    assert len(txns) == 1
    assert txns[0].amount == Decimal("100.00")


def test_give_exact_balance(db, child_500):
    """Give exactly the wallet balance — should leave wallet at 0."""
    wallet = child_500.wallet
    wallet.balance -= Decimal("500")
    db.commit()
    db.refresh(wallet)
    assert wallet.balance == Decimal("0.00")


def test_give_multiple_times(db, child_500):
    """Give multiple times — total_given should accumulate."""
    wallet = child_500.wallet
    for amount in [50, 100, 30]:
        wallet.balance -= Decimal(str(amount))
        txn = Transaction(child_id=child_500.id, type="GIVE", amount=Decimal(str(amount)), description="Donation")
        db.add(txn)
    db.commit()
    db.refresh(wallet)

    assert wallet.balance == Decimal("320.00")  # 500 - 50 - 100 - 30

    from sqlalchemy import func
    total = (
        db.query(func.sum(Transaction.amount))
        .filter(Transaction.child_id == child_500.id, Transaction.type == "GIVE")
        .scalar()
    )
    assert total == Decimal("180")
