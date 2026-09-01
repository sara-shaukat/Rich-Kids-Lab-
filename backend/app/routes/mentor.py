"""Mentor routes — AI Mentor chat endpoint (Stage 6).

Chat history lives client-side per SPEC §16 (no persistent storage).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.wallet_service import get_child_by_anonymous_id
from app.services.mentor_context import build_mentor_context
from app.services.mentor_provider import get_mentor_provider

router = APIRouter(prefix="/api/mentor", tags=["mentor"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class HistoryItem(BaseModel):
    role: str  # "child" | "mentor"
    text: str = Field(default="", max_length=500)


class MentorRequest(BaseModel):
    anonymous_id: str
    message: str = ""
    history: list[HistoryItem] = []


class MentorResponse(BaseModel):
    response: str          # Roman Urdu — displayed in chat bubble
    response_urdu: str     # Urdu script — spoken via speechSynthesis
    provider: str          # "mock" | "groq"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=MentorResponse)
def ask_mentor(request: MentorRequest, db: Session = Depends(get_db)):
    """Answer a child's message with contextual guidance."""
    child = get_child_by_anonymous_id(db, request.anonymous_id)

    message = (request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message zaroori hai.")
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="Message 500 characters se chhota hona chahiye.")

    # Validate + truncate history (last 10 turns, newest last)
    history = []
    for item in request.history[-10:]:
        role = item.role if item.role in ("child", "mentor") else "child"
        history.append({"role": role, "text": (item.text or "")[:500]})

    context = build_mentor_context(db, child)
    provider = get_mentor_provider()
    result = provider.get_response(context, message, history)

    provider_name = "groq" if provider.__class__.__name__ == "GroqProvider" else "mock"
    return MentorResponse(
        response=result["response"],
        response_urdu=result["response_urdu"],
        provider=provider_name,
    )
