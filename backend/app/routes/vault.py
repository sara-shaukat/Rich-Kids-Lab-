"""Vault routes — Money Vault map and level endpoints."""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Child, VaultProgress
from app.services.wallet_service import get_child_by_anonymous_id, get_active_goal
from app.services import vault_service
from app.services import experiment_service

router = APIRouter(prefix="/api/vault", tags=["vault"])


# ---------------------------------------------------------------------------
# Level metadata (static content — same for all children)
# ---------------------------------------------------------------------------

VAULT_LEVELS = [
    {
        "level": 1,
        "name": "Your First Goal",
        "icon": "🎯",
        "description": "Apna pehla financial goal set karo aur poora karo!",
        "concepts": ["goal setting", "saving", "earning", "spending", "planning"],
    },
    {
        "level": 2,
        "name": "Needs vs Wants",
        "icon": "🎯",
        "description": "Zaroorat aur khwahish mein farq samjho",
        "concepts": ["needs", "wants", "priorities", "limited money"],
    },
    {
        "level": 3,
        "name": "Goals & Budgeting",
        "icon": "📊",
        "description": "Goal set karo aur budget banao",
        "concepts": ["goals", "budgeting", "planning", "tracking"],
    },
    {
        "level": 4,
        "name": "Trade-Offs",
        "icon": "⚖️",
        "description": "Har faislay ki ek qeemat hoti hai",
        "concepts": ["opportunity cost", "trade-offs", "consequences"],
    },
    {
        "level": 5,
        "name": "Business & Profit",
        "icon": "🚀",
        "description": "Business shuru karo aur profit kamao",
        "concepts": ["cost", "revenue", "profit", "loss", "skills"],
    },
    {
        "level": 6,
        "name": "Investing & Risk",
        "icon": "📈",
        "description": "Investment aur risk samajhna seekho",
        "concepts": ["investing", "risk", "return", "diversification"],
    },
    {
        "level": 7,
        "name": "Money Management",
        "icon": "🏦",
        "description": "Save, Spend, Grow, Give — sab balance karo",
        "concepts": ["saving", "spending", "investing", "giving", "balancing"],
    },
    {
        "level": 8,
        "name": "Final Challenge",
        "icon": "🏆",
        "description": "Jo seekha wo apply karo — final test!",
        "concepts": ["all concepts", "decision-making", "financial literacy"],
    },
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VaultLevelResponse(BaseModel):
    level: int
    name: str
    icon: str
    description: str
    concepts: list[str]
    status: str  # locked | available | in_progress | completed
    quests_done: list[str] = []
    challenge_passed: bool = False
    completed_at: str | None = None
    goal_progress_pct: int | None = None  # Level 1 only
    goal_name: str | None = None  # Level 1 only


class VaultMapResponse(BaseModel):
    anonymous_id: str
    vault_level: int  # highest unlocked level (0 = only L1)
    levels: list[VaultLevelResponse]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/map/{anonymous_id}", response_model=VaultMapResponse)
def get_vault_map(anonymous_id: str, db: Session = Depends(get_db)):
    """Return the Money Vault map state for a child.
    
    Shows all 8 levels with their lock/unlock/complete status.
    Level 1 is always unlocked (vault_level >= 0).
    Level N is unlocked if vault_level >= N-1.
    """
    child = get_child_by_anonymous_id(db, anonymous_id)
    vault_level = child.vault_level or 0

    # Fetch all VaultProgress rows for this child
    progress_rows = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id)
        .all()
    )
    progress_by_level = {row.level: row for row in progress_rows}

    levels_response = []
    for level_meta in VAULT_LEVELS:
        lvl = level_meta["level"]
        progress = progress_by_level.get(lvl)

        # Determine status
        is_unlocked = vault_level >= (lvl - 1)  # L1 unlocked when vault_level >= 0
        is_completed = progress and progress.challenge_passed == 1 and progress.completed_at

        if is_completed:
            status = "completed"
        elif is_unlocked:
            # For Level 1, check goal progress instead of quests
            if lvl == 1:
                goal = get_active_goal(db, child.id)
                has_progress = bool(goal)
            else:
                quests_done = json.loads(progress.quests_done) if progress and progress.quests_done else []
                has_progress = bool(quests_done)
            status = "in_progress" if has_progress else "available"
        else:
            status = "locked"

        # Goal progress for Level 1 only
        goal_progress_pct = None
        goal_name = None
        if lvl == 1 and is_unlocked:
            goal = get_active_goal(db, child.id)
            if goal:
                goal_name = goal.name
                goal_progress_pct = int(goal.saved_amount / goal.target_amount * 100) if goal.target_amount else 0

        levels_response.append(VaultLevelResponse(
            level=lvl,
            name=level_meta["name"],
            icon=level_meta["icon"],
            description=level_meta["description"],
            concepts=level_meta["concepts"],
            status=status,
            quests_done=json.loads(progress.quests_done) if progress and progress.quests_done else [],
            challenge_passed=bool(progress and progress.challenge_passed),
            completed_at=str(progress.completed_at) if progress and progress.completed_at else None,
            goal_progress_pct=goal_progress_pct,
            goal_name=goal_name,
        ))

    return VaultMapResponse(
        anonymous_id=child.anonymous_id,
        vault_level=vault_level,
        levels=levels_response,
    )


# ---------------------------------------------------------------------------
# Level progression endpoints
# ---------------------------------------------------------------------------

class QuestCompleteRequest(BaseModel):
    anonymous_id: str


class ChallengePassRequest(BaseModel):
    anonymous_id: str
    score: int = 100  # Optional score for the challenge


class LevelStatusResponse(BaseModel):
    level: int
    name: str
    icon: str
    description: str
    status: str
    quests_done: list[str]
    challenge_passed: bool
    completed_at: str | None
    required_quests: list[str]


class QuestCompleteResponse(BaseModel):
    quests_done: list[str]
    level_complete: bool


class ChallengePassResponse(BaseModel):
    challenge_passed: bool
    level_complete: bool
    level_unlocked: int | None


@router.get("/level/{anonymous_id}/{level}", response_model=LevelStatusResponse)
def get_level_status(anonymous_id: str, level: int, db: Session = Depends(get_db)):
    """Get the current status of a specific level."""
    if level < 1 or level > 8:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    child = get_child_by_anonymous_id(db, anonymous_id)
    progress = vault_service.get_or_create_progress(db, child, level)
    status = vault_service.get_level_status(child, progress)
    
    level_meta = VAULT_LEVELS[level - 1]
    quests_done = json.loads(progress.quests_done) if progress.quests_done else []
    required_quests = vault_service.VAULT_LEVEL_QUESTS.get(level, [])
    
    return LevelStatusResponse(
        level=level,
        name=level_meta["name"],
        icon=level_meta["icon"],
        description=level_meta["description"],
        status=status,
        quests_done=quests_done,
        challenge_passed=bool(progress.challenge_passed),
        completed_at=str(progress.completed_at) if progress.completed_at else None,
        required_quests=required_quests,
    )


@router.post("/level/{level}/quest/{quest_id}", response_model=QuestCompleteResponse)
def complete_quest(level: int, quest_id: str, req: QuestCompleteRequest, db: Session = Depends(get_db)):
    """Mark a quest as done within a level.
    
    This does NOT auto-complete the level — challenge must also be passed.
    """
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.complete_quest(db, child, level, quest_id)
    return QuestCompleteResponse(
        quests_done=result["quests_done"],
        level_complete=result["level_complete"],
    )


@router.post("/level/{level}/challenge", response_model=ChallengePassResponse)
def pass_challenge(level: int, req: ChallengePassRequest, db: Session = Depends(get_db)):
    """Mark the level-end challenge as passed.
    
    If all quests are also done, the level completes and next level unlocks.
    """
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.pass_challenge(db, child, level, req.score)
    return ChallengePassResponse(
        challenge_passed=result["challenge_passed"],
        level_complete=result["level_complete"],
        level_unlocked=result["level_unlocked"],
    )


# ---------------------------------------------------------------------------
# Vault Quest Engine endpoints (scenario → choice → consequence → reflection)
# ---------------------------------------------------------------------------

class VaultQuestView(BaseModel):
    id: str
    title: str
    icon: str
    concept: str
    scenario_lines: list[str]
    choices: list[dict]
    is_done: bool


class VaultQuestListResponse(BaseModel):
    level: int
    quests: list[VaultQuestView]


class VaultQuestResolveRequest(BaseModel):
    anonymous_id: str
    quest_id: str
    choice_id: str


class VaultQuestResolveResponse(BaseModel):
    quest_id: str
    choice_id: str
    headline: str
    outcome_lines: list[str]
    was_wise: bool
    verdict: str
    reflection: dict | None


class VaultReflectionRequest(BaseModel):
    anonymous_id: str
    quest_id: str
    answer_id: str


class VaultReflectionResponse(BaseModel):
    bot_line: str


@router.get("/quests/{anonymous_id}/{level}", response_model=VaultQuestListResponse)
def get_vault_level_quests(anonymous_id: str, level: int, db: Session = Depends(get_db)):
    """Get all quests for a specific level with current state."""
    if level < 1 or level > 8:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    child = get_child_by_anonymous_id(db, anonymous_id)
    quests = vault_service.get_vault_level_quests(db, child, level)
    
    return VaultQuestListResponse(
        level=level,
        quests=[VaultQuestView(**q) for q in quests],
    )


@router.post("/quest/{level}/resolve", response_model=VaultQuestResolveResponse)
def resolve_vault_quest(level: int, req: VaultQuestResolveRequest, db: Session = Depends(get_db)):
    """Resolve a vault quest choice.
    
    Executes wallet mutations, records GrowActivity, updates VaultProgress.
    Returns outcome data for display.
    """
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.resolve_vault_quest(db, child, level, req.quest_id, req.choice_id)
    return VaultQuestResolveResponse(
        quest_id=result["quest_id"],
        choice_id=result["choice_id"],
        headline=result["headline"],
        outcome_lines=result["outcome_lines"],
        was_wise=result["was_wise"],
        verdict=result["verdict"],
        reflection=result.get("reflection"),
    )


@router.post("/quest/reflect", response_model=VaultReflectionResponse)
def submit_vault_reflection(req: VaultReflectionRequest, db: Session = Depends(get_db)):
    """Submit a reflection answer for a vault quest."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.submit_vault_reflection(db, child, req.quest_id, req.answer_id)
    return VaultReflectionResponse(bot_line=result["bot_line"])


# ---------------------------------------------------------------------------
# Level Challenge endpoints (scenario-based questions, no wallet mutation)
# ---------------------------------------------------------------------------

class ChallengeQuestionOption(BaseModel):
    id: str
    label: str


class ChallengeQuestion(BaseModel):
    id: str
    question: str
    options: list[ChallengeQuestionOption]


class ChallengeGetResponse(BaseModel):
    level: int
    title: str
    pass_threshold: int
    questions: list[ChallengeQuestion]


class ChallengeSubmitRequest(BaseModel):
    anonymous_id: str
    answers: dict  # {question_id: answer_id}


class ChallengeResultItem(BaseModel):
    question_id: str
    question: str
    your_answer: str
    correct: bool
    explanation: str


class ChallengeSubmitResponse(BaseModel):
    passed: bool
    score: int
    correct: int
    total: int
    results: list[ChallengeResultItem]
    level_complete: bool
    level_unlocked: int | None
    already_completed: bool


@router.get("/challenge/{anonymous_id}/{level}", response_model=ChallengeGetResponse)
def get_level_challenge(anonymous_id: str, level: int, db: Session = Depends(get_db)):
    """Get the challenge questions for a level (without correct answers)."""
    if level < 1 or level > 8:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    child = get_child_by_anonymous_id(db, anonymous_id)
    
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    challenge = vault_service.get_challenge_for_level(level)
    
    # Return questions without correct answers
    questions = []
    for q in challenge["questions"]:
        questions.append(ChallengeQuestion(
            id=q["id"],
            question=q["question"],
            options=[ChallengeQuestionOption(id=o["id"], label=o["label"]) for o in q["options"]],
        ))
    
    return ChallengeGetResponse(
        level=level,
        title=challenge["title"],
        pass_threshold=challenge["pass_threshold"],
        questions=questions,
    )


@router.post("/challenge/{level}/submit", response_model=ChallengeSubmitResponse)
def submit_level_challenge(level: int, req: ChallengeSubmitRequest, db: Session = Depends(get_db)):
    """Submit answers for a level challenge.
    
    No wallet mutation. Returns score, pass/fail, and explanations.
    """
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.submit_level_challenge(db, child, level, req.answers)
    return ChallengeSubmitResponse(
        passed=result["passed"],
        score=result["score"],
        correct=result["correct"],
        total=result["total"],
        results=[ChallengeResultItem(**r) for r in result["results"]],
        level_complete=result["level_complete"],
        level_unlocked=result["level_unlocked"],
        already_completed=result["already_completed"],
    )


# ---------------------------------------------------------------------------
# Money Lab V2 — 7-day experiment endpoints
# ---------------------------------------------------------------------------

class LabSetupRequest(BaseModel):
    anonymous_id: str
    business_id: str
    investment: str
    pricing: str


class LabAdvanceRequest(BaseModel):
    anonymous_id: str


class LabDecisionRequest(BaseModel):
    anonymous_id: str
    decision_id: str


class LabReflectRequest(BaseModel):
    anonymous_id: str
    reflection_id: str


@router.get("/lab/start/{anonymous_id}")
def start_money_lab(anonymous_id: str, db: Session = Depends(get_db)):
    """Start a Money Lab experiment — grants Rs. 500 virtual money."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    return experiment_service.start_experiment(db, child)


@router.get("/lab/state/{anonymous_id}")
def get_lab_state(anonymous_id: str, db: Session = Depends(get_db)):
    """Get current experiment state (for recovery / polling)."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    return experiment_service.get_experiment_state(db, child)


@router.post("/lab/setup")
def setup_money_lab(req: LabSetupRequest, db: Session = Depends(get_db)):
    """Submit choices and get Day 1 result."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    return experiment_service.submit_choices(
        db, child, req.business_id, req.investment, req.pricing
    )


@router.post("/lab/advance")
def advance_money_lab(req: LabAdvanceRequest, db: Session = Depends(get_db)):
    """Advance to next day — returns result, decision prompt, or final."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    return experiment_service.advance_day(db, child)


@router.post("/lab/decide")
def decide_money_lab(req: LabDecisionRequest, db: Session = Depends(get_db)):
    """Apply mid-game decision and advance to next day."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    return experiment_service.submit_decision(db, child, req.decision_id)


@router.post("/lab/reflect")
def reflect_money_lab(req: LabReflectRequest, db: Session = Depends(get_db)):
    """Submit reflection after experiment."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    return experiment_service.submit_experiment_reflection(
        db, child, req.reflection_id
    )


# ---------------------------------------------------------------------------
# Level 1 — First Goal endpoints
# ---------------------------------------------------------------------------

class Level1GoalStatusResponse(BaseModel):
    has_goal: bool
    goal: dict | None = None
    level_complete: bool = False
    reflection_done: bool = False


class Level1CompleteRequest(BaseModel):
    anonymous_id: str
    reflection_answer: str


class Level1CompleteResponse(BaseModel):
    level_complete: bool
    level_unlocked: int | None = None
    already_completed: bool = False


class CertificateResponse(BaseModel):
    child_id: str
    child_name: str
    goal: dict | None = None
    badges: list[dict] = []
    completed_at: str | None = None
    reflection: str = ""
    stats: dict = {}
    wallet_balance: float = 0


class ReportCardResponse(BaseModel):
    categories: list[dict] = []
    overall_gpa: float = 0
    stats: dict = {}
    commentary: str = ""
    ai_generated: bool = False


@router.get("/goal/{anonymous_id}", response_model=Level1GoalStatusResponse)
def get_level1_goal(anonymous_id: str, db: Session = Depends(get_db)):
    """Get the Level 1 goal status for the child."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    result = vault_service.get_level1_goal_status(db, child)
    return Level1GoalStatusResponse(**result)


@router.post("/goal/complete", response_model=Level1CompleteResponse)
def complete_level1_goal(req: Level1CompleteRequest, db: Session = Depends(get_db)):
    """Complete Level 1 after goal reflection."""
    child = get_child_by_anonymous_id(db, req.anonymous_id)
    result = vault_service.complete_level1(db, child, req.reflection_answer)
    return Level1CompleteResponse(**result)


@router.get("/certificate/{anonymous_id}", response_model=CertificateResponse)
def get_certificate(anonymous_id: str, db: Session = Depends(get_db)):
    """Get the Level 1 completion certificate data."""
    child = get_child_by_anonymous_id(db, anonymous_id)
    result = vault_service.get_certificate_data(db, child)
    return CertificateResponse(**result)


@router.get("/reportcard/{anonymous_id}", response_model=ReportCardResponse)
def get_report_card(anonymous_id: str, db: Session = Depends(get_db)):
    """Get the AI Money Report Card for a child."""
    from app.services.report_card_service import compute_report_card, generate_commentary
    child = get_child_by_anonymous_id(db, anonymous_id)
    card = compute_report_card(db, child)

    # Generate AI commentary — one Groq call, template fallback
    commentary = generate_commentary(card)
    card["commentary"] = commentary
    # Only mark as AI-generated if commentary differs from the default template
    from app.services.report_card_service import _FALLBACK_COMMENTARY
    card["ai_generated"] = commentary != _FALLBACK_COMMENTARY

    return ReportCardResponse(**card)
