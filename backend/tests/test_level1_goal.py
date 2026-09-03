"""Tests for Level 1 — Your First Goal flow.

Covers: goal status retrieval, goal creation, goal completion,
reflection, Level 2 unlock, idempotency, and map integration.

Run with:  python -m pytest tests/test_level1_goal.py -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, VaultProgress
from app.services.wallet_service import create_goal, save_to_goal
from app.services import vault_service


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
def child(db):
    """Create a child with Rs. 1000 wallet and no goal."""
    child = Child(anonymous_id="RKL-L1TEST", vault_level=0)
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("1000.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


# ── 1. No goal exists → status shows no goal ────────────────────

class TestLevel1GoalStatusNoGoal:
    def test_no_goal_returns_empty(self, db, child):
        result = vault_service.get_level1_goal_status(db, child)
        assert result["has_goal"] is False
        assert result["goal"] is None
        assert result["level_complete"] is False
        assert result["reflection_done"] is False


# ── 2. Active goal exists → status shows goal + progress ─────────

class TestLevel1GoalStatusActive:
    def test_active_goal_returned(self, db, child):
        create_goal(db, child, "New Football", Decimal("2000"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["has_goal"] is True
        assert result["goal"]["name"] == "New Football"
        assert result["goal"]["target_amount"] == 2000.0
        assert result["goal"]["saved_amount"] == 0.0
        assert result["goal"]["progress_pct"] == 0
        assert result["goal"]["goal_reached"] is False
        assert result["level_complete"] is False

    def test_partial_progress(self, db, child):
        goal = create_goal(db, child, "Headphones", Decimal("3000"))
        save_to_goal(db, child, goal, Decimal("500"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["has_goal"] is True
        assert result["goal"]["saved_amount"] == 500.0
        assert result["goal"]["progress_pct"] == 16  # 500/3000 = 16%
        assert result["goal"]["goal_reached"] is False

    def test_goal_reached(self, db, child):
        goal = create_goal(db, child, "Art Supplies", Decimal("1000"))
        save_to_goal(db, child, goal, Decimal("1000"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["has_goal"] is True
        assert result["goal"]["goal_reached"] is True
        assert result["goal"]["progress_pct"] == 100
        assert result["level_complete"] is False  # no reflection yet


# ── 3. Completed goal (no reflection) → status shows reached ─────

class TestLevel1CompletedGoalNoReflection:
    def test_completed_goal_shows_reached(self, db, child):
        """Goal with status=completed but no reflection → shows reached, not level complete."""
        goal = create_goal(db, child, "Game", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("500"))
        # Goal should now be completed
        assert goal.status == "completed"
        result = vault_service.get_level1_goal_status(db, child)
        assert result["has_goal"] is True
        assert result["goal"]["goal_reached"] is True
        assert result["level_complete"] is False
        assert result["reflection_done"] is False


# ── 4. Complete Level 1 → reflection + unlock ────────────────────

class TestCompleteLevel1:
    def test_complete_level1_success(self, db, child):
        goal = create_goal(db, child, "Bicycle", Decimal("1000"))
        save_to_goal(db, child, goal, Decimal("1000"))
        result = vault_service.complete_level1(db, child, "saved")
        assert result["level_complete"] is True
        assert result["level_unlocked"] == 2
        assert result["already_completed"] is False

        # Verify child.vault_level updated
        db.refresh(child)
        assert child.vault_level == 1

    def test_complete_level1_idempotent(self, db, child):
        goal = create_goal(db, child, "Football", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("500"))
        vault_service.complete_level1(db, child, "earned")
        # Second call should be idempotent
        result = vault_service.complete_level1(db, child, "earned")
        assert result["level_complete"] is True
        assert result["already_completed"] is True
        assert result["level_unlocked"] is None

    def test_complete_level1_without_goal_reached_fails(self, db, child):
        create_goal(db, child, "Bicycle", Decimal("5000"))
        # Goal exists but saved_amount = 0, target = 5000
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            vault_service.complete_level1(db, child, "saved")
        assert exc_info.value.status_code == 400

    def test_complete_level1_no_goal_fails(self, db, child):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            vault_service.complete_level1(db, child, "saved")
        assert exc_info.value.status_code == 400


# ── 5. Level 1 completion unlocks Level 2 ───────────────────────

class TestLevel2Unlock:
    def test_level2_unlocked_after_complete(self, db, child):
        goal = create_goal(db, child, "Headphones", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("500"))
        vault_service.complete_level1(db, child, "careful")

        db.refresh(child)
        # vault_level = 1 means Level 2 is unlocked (L2 unlocks when vault_level >= 1)
        assert child.vault_level >= 1

        # Verify Level 2 status
        progress_l2 = vault_service.get_or_create_progress(db, child, 2)
        status_l2 = vault_service.get_level_status(child, progress_l2)
        assert status_l2 in ("available", "in_progress")
        assert status_l2 != "locked"

    def test_level1_shows_completed_after_refresh(self, db, child):
        goal = create_goal(db, child, "Game", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("500"))
        vault_service.complete_level1(db, child, "mistake")

        # After completion, status should show level complete
        result = vault_service.get_level1_goal_status(db, child)
        assert result["level_complete"] is True
        assert result["reflection_done"] is True


# ── 6. Progress calculation accuracy ─────────────────────────────

class TestProgressCalculation:
    def test_zero_saved(self, db, child):
        create_goal(db, child, "Test", Decimal("1000"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["goal"]["progress_pct"] == 0

    def test_half_saved(self, db, child):
        goal = create_goal(db, child, "Test", Decimal("1000"))
        save_to_goal(db, child, goal, Decimal("500"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["goal"]["progress_pct"] == 50

    def test_full_saved(self, db, child):
        goal = create_goal(db, child, "Test", Decimal("1000"))
        save_to_goal(db, child, goal, Decimal("1000"))
        result = vault_service.get_level1_goal_status(db, child)
        assert result["goal"]["progress_pct"] == 100

    def test_over_saved_caps_at_100(self, db, child):
        """If somehow saved_amount > target, pct should cap at 100."""
        goal = create_goal(db, child, "Test", Decimal("100"))
        # Manually set saved_amount > target (edge case)
        goal.saved_amount = Decimal("200")
        goal.status = "active"
        db.commit()
        db.refresh(goal)
        result = vault_service.get_level1_goal_status(db, child)
        assert result["goal"]["progress_pct"] == 100


# ── 7. No double-counting / duplicate rewards ────────────────────

class TestNoDoubleCounting:
    def test_money_not_duplicated_on_refresh(self, db, child):
        """Saving to goal reduces wallet. Re-reading status doesn't change amounts."""
        goal = create_goal(db, child, "Test", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("300"))

        wallet_balance = child.wallet.balance
        goal_saved = goal.saved_amount

        # Read status multiple times — should not change anything
        for _ in range(3):
            result = vault_service.get_level1_goal_status(db, child)

        db.refresh(child)
        assert child.wallet.balance == wallet_balance
        assert goal.saved_amount == goal_saved

    def test_complete_does_not_grant_extra_money(self, db, child):
        goal = create_goal(db, child, "Test", Decimal("500"))
        save_to_goal(db, child, goal, Decimal("500"))

        balance_before = child.wallet.balance
        vault_service.complete_level1(db, child, "saved")
        db.refresh(child)
        assert child.wallet.balance == balance_before


# ── 8. Existing quest/challenge APIs remain compatible ──────────

class TestBackwardCompatibility:
    def test_vault_map_still_works(self, db, child):
        """The vault progress system should still work for non-Level-1 levels."""
        progress = vault_service.get_or_create_progress(db, child, 1)
        assert progress.level == 1
        assert progress.challenge_passed == 0

    def test_existing_quest_system_untouched(self, db, child):
        """Quest system for Level 1 should still be queryable."""
        quests = vault_service.get_vault_quests_for_level(1)
        assert len(quests) == 3  # Still 3 quests defined

    def test_level_status_still_works(self, db, child):
        progress = vault_service.get_or_create_progress(db, child, 1)
        status = vault_service.get_level_status(child, progress)
        assert status in ("available", "in_progress", "completed", "locked")
