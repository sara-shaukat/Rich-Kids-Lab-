"""Tests for GROW logic — business, investment, skill."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal, ROUND_HALF_UP
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity
from app.services.grow_service import (
    BUSINESS_TEMPLATES,
    SKILL_CARDS,
    INVESTMENT_SCENARIOS,
    get_templates_for_budget,
    start_business,
    invest,
    explore_skill,
)
from app.services.wallet_service import validate_amount


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
    child = Child(anonymous_id="RKL-GROW1")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("500.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


@pytest.fixture()
def child_50(db):
    child = Child(anonymous_id="RKL-GROW2")
    db.add(child)
    db.flush()
    wallet = Wallet(child_id=child.id, balance=Decimal("50.00"))
    db.add(wallet)
    db.commit()
    db.refresh(child)
    return child


# ---- Template data integrity tests ----

def test_business_templates_structure():
    for t in BUSINESS_TEMPLATES:
        assert "id" in t
        assert "name" in t
        assert "min_budget" in t
        assert "cost" in t
        assert "expected_profit_min" in t
        assert "expected_profit_max" in t
        assert "skills" in t
        assert t["expected_profit_min"] <= t["expected_profit_max"]


def test_skill_cards_structure():
    for s in SKILL_CARDS:
        assert "id" in s
        assert "name" in s
        assert "icon" in s
        assert "why" in s
        assert "practice_question" in s
        assert "discover" in s
        assert "challenge" in s
        assert "connect_text" in s
        assert "linked_business_ids" in s
        # Challenge must have question + 4 options
        ch = s["challenge"]
        assert "question" in ch
        assert len(ch["options"]) == 4
        # Exactly one correct option
        correct_count = sum(1 for o in ch["options"] if o["correct"])
        assert correct_count == 1, f"{s['id']} has {correct_count} correct options"


def test_investment_scenarios_structure():
    for key, s in INVESTMENT_SCENARIOS.items():
        assert "name" in s
        assert "min_return" in s
        assert "max_return" in s
        assert s["min_return"] <= s["max_return"]


# ---- Budget filtering tests ----

def test_budget_filter_high_balance(child_500):
    templates = get_templates_for_budget(child_500.wallet.balance)
    assert len(templates) == len(BUSINESS_TEMPLATES)


def test_budget_filter_low_balance(child_50):
    templates = get_templates_for_budget(child_50.wallet.balance)
    # Only templates with min_budget <= 50
    for t in templates:
        assert t["min_budget"] <= 50
    assert len(templates) >= 1  # homework has min_budget=50


def test_budget_filter_zero_balance():
    templates = get_templates_for_budget(Decimal("0"))
    assert len(templates) == 0


# ---- Business simulation tests ----

def test_business_basic(db, child_500):
    """Start Homework Helper: cost Rs. 30, profit randomized within 80-160."""
    initial = child_500.wallet.balance  # 500
    result = start_business(db, child_500, "homework")

    assert result["idea"] == "Homework Helper"
    # Actual profit should be within expected range
    assert Decimal("80") <= result["actual_profit"] <= Decimal("160")
    # Wallet should increase by actual_profit (revenue = cost + profit)
    expected_balance = initial + result["actual_profit"]
    assert result["wallet_balance"] == expected_balance


def test_business_insufficient_balance(db, child_50):
    """Cannot start Art Cards (cost Rs. 150) with Rs. 50."""
    with pytest.raises(Exception) as exc_info:
        start_business(db, child_50, "art_cards")
    assert exc_info.value.status_code == 400


def test_business_invalid_template(db, child_500):
    with pytest.raises(Exception) as exc_info:
        start_business(db, child_500, "spaceship_shop")
    assert exc_info.value.status_code == 400


def test_business_records_activity(db, child_500):
    start_business(db, child_500, "homework")
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "BUSINESS",
    ).all()
    assert len(activities) == 1


def test_business_records_transaction(db, child_500):
    start_business(db, child_500, "homework")
    txns = db.query(Transaction).filter(
        Transaction.child_id == child_500.id,
        Transaction.type == "GROW",
    ).all()
    assert len(txns) == 1
    # Actual profit is randomized but should be within range
    assert Decimal("80") <= txns[0].amount <= Decimal("160")


# ---- Investment simulation tests ----

def test_invest_low_risk(db, child_500):
    """Low risk: -3% to +8%. Invest Rs. 200."""
    result = invest(db, child_500, 200, "low")
    assert result["invested_amount"] == Decimal("200")
    assert -3 <= result["return_percentage"] <= 8
    # Wallet should reflect the outcome
    db.refresh(child_500)
    assert result["wallet_balance"] == child_500.wallet.balance


def test_invest_insufficient_balance(db, child_50):
    """Cannot invest Rs. 100 with only Rs. 50."""
    with pytest.raises(Exception) as exc_info:
        invest(db, child_50, 100, "low")
    assert exc_info.value.status_code == 400


def test_invest_invalid_risk(db, child_500):
    with pytest.raises(Exception) as exc_info:
        invest(db, child_500, 100, "extreme")
    assert exc_info.value.status_code == 400


def test_invest_loss_cap(db, child_500):
    """Wallet balance must never go below zero."""
    # Invest entire balance on high risk (up to -15%)
    # Even worst case, balance should be >= 0
    for _ in range(10):  # Run multiple times to catch randomness
        # Reset wallet for each iteration
        child_500.wallet.balance = Decimal("100.00")
        db.commit()
        result = invest(db, child_500, 100, "high")
        assert result["wallet_balance"] >= Decimal("0")


def test_invest_records_activity(db, child_500):
    invest(db, child_500, 100, "medium")
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "INVESTMENT",
    ).all()
    assert len(activities) == 1


def test_invest_medium_risk_range(db, child_500):
    """Medium risk: -15% to +25%."""
    result = invest(db, child_500, 100, "medium")
    assert -15 <= result["return_percentage"] <= 25
    assert result["risk_name"] == "Growing Company"


def test_invest_high_risk_range(db, child_500):
    """High risk: -50% to +60%."""
    result = invest(db, child_500, 100, "high")
    assert -50 <= result["return_percentage"] <= 60
    assert result["risk_name"] == "New Startup"


def test_invest_scenario_names_are_fictional(db, child_500):
    """Ensure no real company/product names are used."""
    for key in ["low", "medium", "high"]:
        result = invest(db, child_500, 50, key)
        name = result["risk_name"]
        # Must NOT contain real financial terms
        real_terms = ["bitcoin", "crypto", "apple", "tesla", "stock", "mutual fund"]
        for term in real_terms:
            assert term not in name.lower()
        # Reset wallet for next iteration
        child_500.wallet.balance = Decimal("500.00")
        db.commit()


def test_invest_profit_calculation(db, child_500):
    """Verify outcome = invested * (1 + return_pct/100)."""
    result = invest(db, child_500, 200, "medium")
    expected = Decimal("200") * (1 + Decimal(str(result["return_percentage"])) / Decimal("100"))
    expected = expected.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # Due to loss cap, actual outcome might differ — but if no cap hit, should match
    if result["wallet_balance"] > Decimal("0"):
        assert result["outcome_amount"] == expected


def test_invest_repeated_no_money_duplication(db, child_500):
    """Repeated investment should not create free money — each invest deducts first."""
    initial = child_500.wallet.balance
    # Invest 100 three times
    for _ in range(3):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = invest(db, child_500, 100, "low")
        # Each time, the wallet changes by outcome - invested (net)
        # but no free money is created
        assert result["wallet_balance"] <= Decimal("500") + Decimal("8")  # max +8%


def test_invest_records_all_details(db, child_500):
    """Investment activity should record all necessary details for history."""
    import json
    result = invest(db, child_500, 150, "medium")
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "INVESTMENT",
    ).all()
    assert len(activities) == 1
    details = json.loads(activities[0].details)
    assert "initial_amount" in details
    assert "risk_level" in details
    assert "return_percentage" in details
    assert "outcome_amount" in details
    assert "profit_loss" in details
    assert details["risk_level"] == "medium"
    assert details["initial_amount"] == 150.0


def test_invest_scenario_has_icon_and_description():
    """Each investment scenario must have icon and description for UI."""
    for key, scenario in INVESTMENT_SCENARIOS.items():
        assert "icon" in scenario, f"{key} missing icon"
        assert "description" in scenario, f"{key} missing description"
        assert len(scenario["icon"]) > 0
        assert len(scenario["description"]) > 0


# ---- Skill exploration tests ----

def test_skill_basic(db, child_500):
    result = explore_skill(db, child_500, "ai_prompting")
    assert result["skill_name"] == "AI Prompt Engineering"
    assert result["category"] == "tech"
    assert "earning_potential" in result


def test_skill_records_interest(db, child_500):
    explore_skill(db, child_500, "ai_prompting")
    db.refresh(child_500)
    assert child_500.interests is not None
    import json
    interests = json.loads(child_500.interests)
    assert "tech" in interests


def test_skill_records_activity(db, child_500):
    explore_skill(db, child_500, "coding", practice_answer="My cool app")
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "SKILL",
    ).all()
    assert len(activities) == 1
    import json
    details = json.loads(activities[0].details)
    assert details["practice_answer"] == "My cool app"


def test_skill_challenge_correct_answer(db, child_500):
    """Submit correct challenge answer for ai_prompting (option 'b')."""
    result = explore_skill(db, child_500, "ai_prompting", challenge_answer="b")
    assert result["is_correct"] is True
    assert len(result["explanation"]) > 0


def test_skill_challenge_wrong_answer(db, child_500):
    """Submit wrong challenge answer for ai_prompting (option 'a')."""
    result = explore_skill(db, child_500, "ai_prompting", challenge_answer="a")
    assert result["is_correct"] is False
    assert len(result["explanation"]) > 0


def test_skill_challenge_records_details(db, child_500):
    """Verify GrowActivity JSON has challenge_answer, was_correct, practice_text."""
    import json
    explore_skill(
        db, child_500, "writing",
        challenge_answer="b",
        practice_text="Ye bookmark aapki kitaab ki kahani hai.",
    )
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "SKILL",
    ).all()
    assert len(activities) == 1
    details = json.loads(activities[0].details)
    assert details["challenge_answer"] == "b"
    assert details["was_correct"] is True
    assert details["practice_text"] == "Ye bookmark aapki kitaab ki kahani hai."


def test_skill_has_linked_business():
    """Each skill must have at least one linked business ID."""
    for s in SKILL_CARDS:
        assert len(s.get("linked_business_ids", [])) >= 1, f"{s['id']} has no linked business"


def test_skill_connect_text_present():
    """Each skill must have non-empty connect_text."""
    for s in SKILL_CARDS:
        assert len(s.get("connect_text", "")) > 0, f"{s['id']} has empty connect_text"


def test_skill_no_income_guarantee():
    """Verify earning_potential doesn't contain guaranteed amounts."""
    for s in SKILL_CARDS:
        ep = s["earning_potential"].lower()
        assert "guaranteed" not in ep, f"{s['id']} has 'guaranteed' in earning_potential"
        assert "100%" not in ep, f"{s['id']} has '100%' in earning_potential"


def test_skill_writing_practice_stored(db, child_500):
    """Writing skill stores optional practice text in GrowActivity even with no challenge answer."""
    import json
    explore_skill(
        db, child_500, "writing",
        practice_text="Mera bookmark colorful hai.",
    )
    activities = db.query(GrowActivity).filter(
        GrowActivity.child_id == child_500.id,
        GrowActivity.type == "SKILL",
    ).all()
    assert len(activities) == 1
    details = json.loads(activities[0].details)
    assert details["practice_text"] == "Mera bookmark colorful hai."
    assert details["was_correct"] is None  # no challenge submitted


def test_skill_result_has_connect_and_business(db, child_500):
    """explore_skill returns connect_text and linked_business_ids."""
    result = explore_skill(db, child_500, "crafts", challenge_answer="b")
    assert len(result["connect_text"]) > 0
    assert len(result["linked_business_ids"]) >= 1


def test_skill_no_wallet_change(db, child_500):
    initial = child_500.wallet.balance
    explore_skill(db, child_500, "photography")
    db.refresh(child_500)
    assert child_500.wallet.balance == initial


def test_skill_invalid(db, child_500):
    with pytest.raises(Exception) as exc_info:
        explore_skill(db, child_500, "astronomy")
    assert exc_info.value.status_code == 400


# ---- AI Provider tests ----

def test_ai_score_matching():
    from app.services.ai_provider import score_template
    # "art" maps to bookmarks, art_cards, sticker_shop
    assert score_template(["art"], "bookmarks") == 1
    assert score_template(["art", "design"], "bookmarks") == 2
    assert score_template([], "bookmarks") == 0
    assert score_template(["food"], "bookmarks") == 0


def test_ai_rank_templates():
    from app.services.ai_provider import rank_templates
    templates = [
        {"id": "homework", "name": "Homework Helper"},
        {"id": "bookmarks", "name": "Handmade Bookmarks"},
    ]
    ranked = rank_templates(["art"], templates)
    # bookmarks should rank higher (art maps to bookmarks)
    assert ranked[0]["id"] == "bookmarks"
    assert ranked[0]["match_score"] >= ranked[1]["match_score"]
    assert "pitch" in ranked[0]


def test_ai_generate_pitch_has_business_name():
    from app.services.ai_provider import generate_pitch
    pitch = generate_pitch(["art"], "bookmarks", "Handmade Bookmarks")
    assert "Handmade Bookmarks" in pitch


def test_ai_default_pitch_no_interest():
    from app.services.ai_provider import generate_pitch
    pitch = generate_pitch([], "homework", "Homework Helper")
    assert "Homework Helper" in pitch


def test_business_profit_randomized(db, child_500):
    """Run business 10 times and check profit varies within range."""
    profits = set()
    for _ in range(10):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = start_business(db, child_500, "homework")
        profit = result["actual_profit"]
        assert Decimal("80") <= profit <= Decimal("160")
        profits.add(profit)
    # With 10 runs, we should see at least 2 different values
    assert len(profits) >= 2


# ---------------------------------------------------------------------------
# Phone Accessories (loss-making template)
# ---------------------------------------------------------------------------

def test_phone_accessories_template_exists():
    """Phone Accessories should be in templates with negative expected_profit_min."""
    ids = [t["id"] for t in BUSINESS_TEMPLATES]
    assert "phone_accessories" in ids
    template = next(t for t in BUSINESS_TEMPLATES if t["id"] == "phone_accessories")
    assert template["expected_profit_min"] < 0
    assert template["expected_profit_max"] > 0


def test_phone_accessories_can_lose_money(db, child_500):
    """Run phone accessories 50 times — at least one loss should occur."""
    losses = 0
    for _ in range(50):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = start_business(db, child_500, "phone_accessories")
        if result["actual_profit"] < 0:
            losses += 1
    assert losses >= 1, "Phone Accessories should produce at least 1 loss in 50 runs"


def test_lemonade_can_lose_money(db, child_500):
    """Lemonade Stand should sometimes lose money (range: -50 to 310)."""
    losses = 0
    for _ in range(100):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = start_business(db, child_500, "lemonade")
        if result["actual_profit"] < 0:
            losses += 1
    assert losses >= 1, "Lemonade Stand should produce at least 1 loss in 100 runs"


def test_sticker_shop_can_lose_money(db, child_500):
    """Sticker Shop should sometimes lose money (range: -80 to 400)."""
    losses = 0
    for _ in range(100):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = start_business(db, child_500, "sticker_shop")
        if result["actual_profit"] < 0:
            losses += 1
    assert losses >= 1, "Sticker Shop should produce at least 1 loss in 100 runs"


def test_homework_never_loses(db, child_500):
    """Homework Helper should NEVER lose money (safe for kids)."""
    for _ in range(50):
        child_500.wallet.balance = Decimal("500.00")
        db.commit()
        result = start_business(db, child_500, "homework")
        assert result["actual_profit"] >= 0, "Homework Helper should never lose money"


def test_phone_accessories_has_explanation(db, child_500):
    """Business result should include result_explanation."""
    result = start_business(db, child_500, "phone_accessories")
    assert "result_explanation" in result
    assert len(result["result_explanation"]) > 10


# ---------------------------------------------------------------------------
# Business explanation generation
# ---------------------------------------------------------------------------

def test_business_explanation_loss(db, child_500):
    """Explanation should mention 'loss' when profit is negative."""
    from app.services.grow_service import _generate_business_explanation
    template = next(t for t in BUSINESS_TEMPLATES if t["id"] == "phone_accessories")
    explanation = _generate_business_explanation(template, Decimal("-50"), Decimal("250"))
    assert "loss" in explanation.lower()
    assert "risk" in explanation.lower()


def test_business_explanation_small_profit(db, child_500):
    """Explanation should mention 'small' or 'chhota' for low profit."""
    from app.services.grow_service import _generate_business_explanation
    template = next(t for t in BUSINESS_TEMPLATES if t["id"] == "phone_accessories")
    explanation = _generate_business_explanation(template, Decimal("30"), Decimal("250"))
    assert "chhota" in explanation.lower() or "small" in explanation.lower()


def test_business_explanation_great_profit(db, child_500):
    """Explanation should praise when profit is near the upper end."""
    from app.services.grow_service import _generate_business_explanation
    template = next(t for t in BUSINESS_TEMPLATES if t["id"] == "phone_accessories")
    explanation = _generate_business_explanation(template, Decimal("380"), Decimal("250"))
    assert "zabardast" in explanation.lower() or "smart" in explanation.lower()


def test_business_explanation_normal_profit(db, child_500):
    """Explanation should mention 'profit margin' for normal profit."""
    from app.services.grow_service import _generate_business_explanation
    template = next(t for t in BUSINESS_TEMPLATES if t["id"] == "phone_accessories")
    explanation = _generate_business_explanation(template, Decimal("150"), Decimal("250"))
    assert "profit margin" in explanation.lower() or "margin" in explanation.lower()
