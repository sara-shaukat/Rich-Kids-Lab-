"""Tests for the AI Mentor (Stage 6): context builder, mock provider,
Groq provider (mocked, no network), and the endpoint.

Run with:  python -m pytest tests/ -v
(from the backend/ directory)
"""

import os
import sys
import types

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity
from app.services.wallet_service import create_goal, save_to_goal
from app.services.mentor_context import build_mentor_context
from app.services.mentor_provider import (
    MockProvider,
    GroqProvider,
    get_mentor_provider,
    _T_DONT_KNOW,
    _T_TOPICS,
    _T_GOAL_PROGRESS,
    _T_NO_GOAL,
    _T_FRESH,
    _T_LOW_BALANCE,
    _T_DEFAULT,
)
from app.routes.mentor import ask_mentor, MentorRequest, HistoryItem


ALL_TEMPLATES = (
    [_T_DONT_KNOW, _T_GOAL_PROGRESS, _T_NO_GOAL, _T_FRESH, _T_LOW_BALANCE, _T_DEFAULT]
    + list(_T_TOPICS.values())
)

_URDU_CHARS = any("\u0600" <= ch <= "\u06FF" for ch in "ب")


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


def _make_child(db, balance=500):
    global _child_counter
    _child_counter += 1
    child = Child(anonymous_id=f"RKL-MTEST{_child_counter}")
    db.add(child)
    db.flush()
    db.add(Wallet(child_id=child.id, balance=Decimal(str(balance))))
    db.commit()
    db.refresh(child)
    return child


def _ctx(db, child):
    return build_mentor_context(db, child)


# ---- context builder tests ----

def test_context_fresh_child(db):
    child = _make_child(db, 500)
    ctx = _ctx(db, child)
    assert ctx["balance"] == 500.0
    assert ctx["goal"] is None
    assert ctx["totals"] == {"saved": 0.0, "spent": 0.0, "grown": 0.0, "given": 0.0}
    assert ctx["recent_transactions"] == []
    assert ctx["interests"] == []
    assert ctx["last_grow"] is None
    assert ctx["skills_completed"] == []
    assert ctx["level_name"] == "Newbie"
    assert ctx["total_actions"] == 0


def test_context_with_goal(db):
    child = _make_child(db, 10000)
    create_goal(db, child, "Cycle", 8000)
    save_to_goal(db, child, child.goals[0], 2000)
    db.refresh(child)

    ctx = _ctx(db, child)
    assert ctx["goal"]["name"] == "Cycle"
    assert ctx["goal"]["saved"] == 2000.0
    assert ctx["goal"]["target"] == 8000.0
    assert ctx["goal"]["remaining"] == 6000.0
    assert ctx["goal"]["progress_pct"] == 25


def test_context_totals_and_recent(db):
    child = _make_child(db, 2000)
    for t, amt, desc in [
        ("SPEND", 300, "Pizza"), ("SAVE", 200, "Saved toward Cycle"),
        ("GIVE", 50, "Donation"), ("GROW", 120, "Business"),
    ]:
        db.add(Transaction(child_id=child.id, type=t, amount=Decimal(str(amt)), description=desc))
    db.commit()

    ctx = _ctx(db, child)
    assert ctx["totals"] == {"saved": 200.0, "spent": 300.0, "grown": 120.0, "given": 50.0}
    assert len(ctx["recent_transactions"]) == 4


def test_context_skills_and_last_grow(db):
    child = _make_child(db, 500)
    db.add(GrowActivity(
        child_id=child.id, type="SKILL",
        details=json.dumps({"name": "Coding", "was_correct": True}),
        created_at=datetime(2026, 1, 1, 10, 0, 0),
    ))
    db.add(GrowActivity(
        child_id=child.id, type="INVESTMENT",
        details=json.dumps({"risk_level": "high", "profit_loss": -50.0}),
        created_at=datetime(2026, 1, 1, 11, 0, 0),
    ))
    db.commit()

    ctx = _ctx(db, child)
    assert ctx["skills_completed"] == ["Coding"]
    assert ctx["last_grow"]["type"] == "INVESTMENT"
    assert ctx["last_grow"]["profit_loss"] == -50.0


# ---- mock provider tests ----

def test_mock_dont_know_path(db):
    child = _make_child(db, 500)
    result = MockProvider().get_response(_ctx(db, child), "mujhe nahi pata, kya karun?", [])
    assert "Koi baat nahi" in result["response"]
    assert _URDU_CHARS  # sanity: Urdu char range works
    assert any("\u0600" <= c <= "\u06FF" for c in result["response_urdu"])


def test_mock_topic_routing(db):
    child = _make_child(db, 500)
    create_goal(db, child, "Cycle", 8000)
    db.refresh(child)
    ctx = _ctx(db, child)
    provider = MockProvider()

    assert "Bachat ka sawal" in provider.get_response(ctx, "paisay kaise bachaun?", [])["response"]
    assert "smart spending" in provider.get_response(ctx, "kharch karna chahiye?", [])["response"]
    assert "Investment ka matlab" in provider.get_response(ctx, "investment kya hoti hai?", [])["response"]
    assert "business ideas" in provider.get_response(ctx, "business shuru karna hai", [])["response"]
    assert "SKILL LAB" in provider.get_response(ctx, "kaun si skill seekhoon?", [])["response"]
    assert "GIVE" in provider.get_response(ctx, "donate karna chahiye?", [])["response"]


def test_mock_urdu_script_voice_input(db):
    """Voice input arrives in Urdu script — keywords must still route."""
    child = _make_child(db, 500)
    ctx = _ctx(db, child)
    provider = MockProvider()

    assert "smart spending" in provider.get_response(ctx, "میں خرچ کرنا چاہتا ہوں", [])["response"]
    assert "Bachat ka sawal" in provider.get_response(ctx, "پیسے کیسے بچاؤں؟", [])["response"]
    assert "Koi baat nahi" in provider.get_response(ctx, "مجھے پتا نہیں کیا کروں", [])["response"]


def test_mock_goal_progress(db):
    child = _make_child(db, 10000)
    create_goal(db, child, "Cycle", 8000)
    save_to_goal(db, child, child.goals[0], 2000)
    db.refresh(child)

    result = MockProvider().get_response(_ctx(db, child), "mera goal kaisa hai?", [])
    assert "Cycle" in result["response"]
    assert "2000 / 8000" in result["response"]
    assert "6000" in result["response"]
    assert "25%" in result["response"]


def test_mock_no_goal_suggestion(db):
    child = _make_child(db, 500)
    db.add(Transaction(child_id=child.id, type="SPEND", amount=Decimal("100"), description="Pizza"))
    db.commit()
    result = MockProvider().get_response(_ctx(db, child), "hello", [])
    assert "goal" in result["response"].lower()
    assert "SAVE" in result["response"]


def test_mock_fresh_greeting(db):
    child = _make_child(db, 500)
    result = MockProvider().get_response(_ctx(db, child), "hello", [])
    assert "Assalamu Alaikum" in result["response"]
    assert "Paisa Bot" in result["response"]


def test_mock_low_balance(db):
    child = _make_child(db, 30)
    create_goal(db, child, "Cycle", 8000)
    db.add(Transaction(child_id=child.id, type="SPEND", amount=Decimal("10"), description="Snack"))
    db.commit()
    db.refresh(child)
    result = MockProvider().get_response(_ctx(db, child), "hello", [])
    assert "Rs. 30" in result["response"]
    assert "GROW" in result["response"]


def test_mock_default_fallback(db):
    child = _make_child(db, 700)
    create_goal(db, child, "Cycle", 8000)
    db.refresh(child)
    result = MockProvider().get_response(_ctx(db, child), "random xyz message", [])
    assert "Rs. 700" in result["response"]


def test_mock_no_income_guarantees():
    blob = json.dumps([t["text"] + t["text_ur"] for t in ALL_TEMPLATES]).lower()
    assert "guarantee" not in blob


def test_mock_placeholders_filled(db):
    """With and without a goal — no leftover {placeholders} in either script."""
    child = _make_child(db, 500)
    provider = MockProvider()

    messages = ["mujhe nahi pata", "paisay kaise bachaun", "goal kaisa hai", "hello", "kharch"]
    for msg in messages:
        result = provider.get_response(_ctx(db, child), msg, [])
        assert "{" not in result["response"], f"unfilled placeholder: {result['response']}"
        assert "{" not in result["response_urdu"], f"unfilled placeholder: {result['response_urdu']}"

    create_goal(db, child, "Cycle", 8000)
    db.refresh(child)
    for msg in messages:
        result = provider.get_response(_ctx(db, child), msg, [])
        assert "{" not in result["response"]
        assert "{" not in result["response_urdu"]


def test_mock_dual_script_for_all_templates():
    """Every template has a non-empty Urdu-script twin."""
    for template in ALL_TEMPLATES:
        assert template["text"].strip(), "empty Roman text"
        assert template["text_ur"].strip(), f"empty Urdu twin for: {template['text'][:40]}"
        assert any("\u0600" <= c <= "\u06FF" for c in template["text_ur"]), (
            f"Urdu twin has no Urdu script: {template['text_ur'][:40]}"
        )


# ---- Groq provider tests (no network — httpx faked) ----

def _fake_httpx(response_content="Sahi sawal! Chalo bachat karein.###\nسہی سوال! چلو بچت کریں۔", fail=False):
    """Build a fake httpx module for lazy import inside GroqProvider."""
    class FakeResponse:
        def raise_for_status(self):
            if fail:
                raise RuntimeError("HTTP 500")
        def json(self):
            return {"choices": [{"message": {"content": response_content}}]}

    class FakeClient:
        def __init__(self, timeout=None): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, json=None, headers=None):
            if fail:
                raise RuntimeError("connection error")
            return FakeResponse()

    module = types.ModuleType("httpx")
    module.Client = FakeClient
    return module


def test_groq_success(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx())
    provider = GroqProvider()
    result = provider.get_response({"balance": 500, "goal": None}, "hello", [])
    assert result["response"] == "Sahi sawal! Chalo bachat karein."
    assert "بچت" in result["response_urdu"]


def test_groq_single_part_response(monkeypatch):
    """If Groq ignores the ### format, Roman text is used for both."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx(response_content="Sirf Roman jawab"))
    result = GroqProvider().get_response({"balance": 500, "goal": None}, "hello", [])
    assert result["response"] == "Sirf Roman jawab"
    assert result["response_urdu"] == "Sirf Roman jawab"


def test_groq_error_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "httpx", _fake_httpx(fail=True))
    result = GroqProvider().get_response({"balance": 500, "goal": None}, "hello", [])
    # Mock default template responds with the balance
    assert "Rs. 500" in result["response"]


def test_groq_missing_key_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = GroqProvider().get_response({"balance": 500, "goal": None}, "hello", [])
    assert "Rs. 500" in result["response"]


def test_groq_missing_httpx_falls_back_to_mock(monkeypatch):
    """httpx not installed -> import error -> mock fallback, app never breaks."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "httpx", None)  # forces ImportError on import
    result = GroqProvider().get_response({"balance": 500, "goal": None}, "hello", [])
    assert "Rs. 500" in result["response"]


def test_factory_default_mock(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert isinstance(get_mentor_provider(), MockProvider)


def test_factory_groq(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assert isinstance(get_mentor_provider(), GroqProvider)


def test_factory_groq_without_key_is_mock(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert isinstance(get_mentor_provider(), MockProvider)


# ---- endpoint tests ----

def test_endpoint_valid(db):
    child = _make_child(db, 500)
    req = MentorRequest(anonymous_id=child.anonymous_id, message="paisay kaise bachaun?")
    resp = ask_mentor(req, db=db)
    assert resp.provider == "mock"
    assert "Bachat" in resp.response
    assert any("\u0600" <= c <= "\u06FF" for c in resp.response_urdu)


def test_endpoint_unknown_child(db):
    req = MentorRequest(anonymous_id="RKL-NOPE", message="hello")
    with pytest.raises(HTTPException) as exc_info:
        ask_mentor(req, db=db)
    assert exc_info.value.status_code == 404


def test_endpoint_empty_message(db):
    child = _make_child(db, 500)
    req = MentorRequest(anonymous_id=child.anonymous_id, message="   ")
    with pytest.raises(HTTPException) as exc_info:
        ask_mentor(req, db=db)
    assert exc_info.value.status_code == 400


def test_endpoint_too_long_message(db):
    child = _make_child(db, 500)
    req = MentorRequest(anonymous_id=child.anonymous_id, message="a" * 501)
    with pytest.raises(HTTPException) as exc_info:
        ask_mentor(req, db=db)
    assert exc_info.value.status_code == 400


def test_endpoint_history_accepted(db):
    child = _make_child(db, 500)
    create_goal(db, child, "Cycle", 8000)
    db.refresh(child)
    req = MentorRequest(
        anonymous_id=child.anonymous_id,
        message="mera goal kaisa hai?",
        history=[
            HistoryItem(role="child", text="hello"),
            HistoryItem(role="mentor", text="Assalamu Alaikum!"),
        ],
    )
    resp = ask_mentor(req, db=db)
    assert "Cycle" in resp.response
