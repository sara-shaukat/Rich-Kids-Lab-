"""Tests for the Money Report Card service."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity
from app.services.report_card_service import (
    compute_report_card,
    generate_commentary,
    _FALLBACK_COMMENTARY,
    _to_grade,
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
    child = Child(anonymous_id="RKL-RCTEST", vault_level=0)
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


def _add_txn(db, child, type_, amount, desc=""):
    txn = Transaction(child_id=child.id, type=type_, amount=Decimal(str(amount)), description=desc)
    db.add(txn)
    db.commit()


def _add_business(db, child, template_id, profit):
    details = json.dumps({"template_id": template_id, "actual_profit": profit, "cost": 200})
    activity = GrowActivity(child_id=child.id, type="BUSINESS", details=details)
    db.add(activity)
    db.commit()


# ---------------------------------------------------------------------------
# Grade conversion
# ---------------------------------------------------------------------------

class TestGradeConversion:
    def test_grade_a(self):
        assert _to_grade(95) == "A"
        assert _to_grade(90) == "A"

    def test_grade_b(self):
        assert _to_grade(80) == "B"
        assert _to_grade(75) == "B"

    def test_grade_c(self):
        assert _to_grade(60) == "C"
        assert _to_grade(55) == "C"

    def test_grade_d(self):
        assert _to_grade(40) == "D"

    def test_grade_f(self):
        assert _to_grade(0) == "F"
        assert _to_grade(10) == "F"


# ---------------------------------------------------------------------------
# Report card computation
# ---------------------------------------------------------------------------

class TestComputeReportCard:
    def test_empty_child(self, db, child):
        """A child with no activity should get low scores (spending gets neutral 50)."""
        card = compute_report_card(db, child)
        assert len(card["categories"]) == 5
        # Spending gets a neutral 50 even with no data
        assert card["overall_gpa"] <= 1.0
        assert card["stats"]["total_transactions"] == 0

    def test_saving_grade(self, db, child):
        """Child who saves a lot should get a high saving grade."""
        for i in range(10):
            _add_txn(db, child, "SAVE", 50)
        _add_txn(db, child, "SPEND", 20)
        card = compute_report_card(db, child)
        saving = next(c for c in card["categories"] if c["id"] == "saving")
        assert saving["score"] >= 50
        assert saving["grade"] in ("A", "B")

    def test_business_grade_with_profit(self, db, child):
        """Child with profitable businesses should score well."""
        _add_business(db, child, "sticker_shop", 300)
        _add_business(db, child, "bakery", 200)
        card = compute_report_card(db, child)
        biz = next(c for c in card["categories"] if c["id"] == "business")
        assert biz["score"] > 0

    def test_business_grade_with_loss(self, db, child):
        """Child with losses should still get some score (risk bonus)."""
        _add_business(db, child, "phone_accessories", -50)
        card = compute_report_card(db, child)
        biz = next(c for c in card["categories"] if c["id"] == "business")
        assert biz["score"] > 0  # Risk bonus

    def test_giving_grade(self, db, child):
        """Child who gives should score in giving."""
        _add_txn(db, child, "GIVE", 100)
        _add_txn(db, child, "SAVE", 50)
        card = compute_report_card(db, child)
        giving = next(c for c in card["categories"] if c["id"] == "giving")
        assert giving["score"] > 0

    def test_growth_grade_with_skills(self, db, child):
        """Child who learns skills should score in growth."""
        skill = GrowActivity(child_id=child.id, type="SKILL", details=json.dumps({"skill_id": "cooking"}))
        db.add(skill)
        db.commit()
        card = compute_report_card(db, child)
        growth = next(c for c in card["categories"] if c["id"] == "growth")
        assert growth["score"] > 0
        assert card["stats"]["skills_learned"] == 1

    def test_stats_totals(self, db, child):
        """Stats should reflect actual transaction totals."""
        _add_txn(db, child, "SAVE", 100)
        _add_txn(db, child, "SAVE", 50)
        _add_txn(db, child, "SPEND", 30)
        card = compute_report_card(db, child)
        assert card["stats"]["total_saved"] == 150.0
        assert card["stats"]["total_spent"] == 30.0
        assert card["stats"]["total_transactions"] == 3

    def test_all_categories_have_required_fields(self, db, child):
        """Each category should have id, name, icon, score, grade, detail."""
        card = compute_report_card(db, child)
        for cat in card["categories"]:
            assert "id" in cat
            assert "name" in cat
            assert "icon" in cat
            assert "score" in cat
            assert "grade" in cat
            assert "detail" in cat


# ---------------------------------------------------------------------------
# AI Commentary
# ---------------------------------------------------------------------------

class TestCommentary:
    def test_fallback_without_api_key(self, db, child, monkeypatch):
        """Without GROQ_API_KEY, commentary should be the fallback template."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        card = compute_report_card(db, child)
        commentary = generate_commentary(card)
        assert commentary == _FALLBACK_COMMENTARY

    def test_fallback_is_roman_urdu(self):
        """Fallback commentary should be in Roman Urdu."""
        assert "acha" in _FALLBACK_COMMENTARY.lower() or "bahut" in _FALLBACK_COMMENTARY.lower()
