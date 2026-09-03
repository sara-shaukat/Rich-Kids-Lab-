"""Vault service — Money Vault level progression logic."""

import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Child, VaultProgress, Transaction, GrowActivity, Goal
from app.services.wallet_service import get_active_goal, save_to_goal, create_goal


# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

# Each level has a list of required quest IDs
VAULT_LEVEL_QUESTS = {
    1: ["vq1_pocket_money", "vq1_spend_wisely", "vq1_first_save"],
    2: [],
    3: [],
    4: [],
    5: [],
    6: [],
    7: [],
    8: [],
}


# ---------------------------------------------------------------------------
# Vault Quest definitions (reusable engine — add quests per level)
# ---------------------------------------------------------------------------

VAULT_QUESTS = [
    {
        "id": "vq1_pocket_money",
        "level": 1,
        "title": "Kamai Ka Faisla",
        "icon": "💵",
        "concept": "Income & Earning",
        "scenario_lines": [
            "Chacha ne aap ki madad ke Rs. {earn} diye!",
            "Ab aapke paas total Rs. {balance} hain.",
            "Kamai ka matlab yeh nahi ke sab kharch karo — smart log pehle sochte hain!",
        ],
        "choices": [
            {
                "id": "save_most",
                "label": "💰 Rs. {save} save karo, Rs. {keep} rakho",
                "sub": "Zyadatar bachao — thora maze ke liye",
                "action": "save",
                "amount_key": "save",
                "was_wise": True,
                "verdict": "win",
                "headline": "Smart earning, smart saving!",
                "outcome_lines": [
                    "Rs. {save} goal '{goal}' mein gaye — ab {pct_after}% complete hai!",
                    "Rs. {keep} aap ke paas reh gaye — jab chaho kharch kar sakte ho.",
                    "Kamai ka asli secret yehi hai: pehle bachao, phir kharch karo!",
                ],
            },
            {
                "id": "spend_all",
                "label": "🍬 Sab kharch karo — Rs. {earn} snacks pe!",
                "sub": "Aaj maze karo!",
                "action": "spend",
                "amount_key": "earn",
                "spend_description": "Quest: Snacks & Treats",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "Maza aaya — lekin...",
                "outcome_lines": [
                    "Saari kamai snacks pe kharach di!",
                    "Snacks khatam ho gaye, aur goal '{goal}' ke liye kuch nahi bacha.",
                    "Yaad rakho: kamai ka paisa seedha kharch nahi karna chahiye — pehle bachana seekho!",
                ],
            },
        ],
        "reflection": {
            "question": "Kamai ka paisa kaise handle karna chahiye?",
            "options": [
                {
                    "id": "save_first",
                    "label": "💰 Pehle bachao, phir kharch karo",
                    "bot_line": "Bilkul sahi! Yehi smart earning ka formula hai! \U0001f916",
                },
                {
                    "id": "spend_first",
                    "label": "🍬 Pehle maze, bachat baad mein",
                    "bot_line": "Hmm... maze zaroori hain lekin bachat pehle aani chahiye! \U0001f916",
                },
            ],
        },
    },
    {
        "id": "vq1_spend_wisely",
        "level": 1,
        "title": "Kharch Ka Socho!",
        "icon": "🛍️",
        "concept": "Spending & Balance",
        "scenario_lines": [
            "Aapke paas Rs. {balance} hain.",
            "Dost ne naya video game dikhaya — Rs. {toy} ka hai!",
            "Agar khareedo ge to balance kam ho jayega... kya karo ge?",
        ],
        "choices": [
            {
                "id": "skip_toy",
                "label": "🚫 Nahi khareedo — goal pehle!",
                "sub": "Balance bacha rahega",
                "action": "none",
                "was_wise": True,
                "verdict": "win",
                "headline": "Self-control champion!",
                "outcome_lines": [
                    "Aap ne nahi khareeda — Rs. {balance} abhi bhi aap ke paas hain!",
                    "Har 'nahi' ek smart faisla hai jo aap ko goal ke qareeb le jata hai.",
                    "Spending ka matlab hai balance kam hona — aur is baar aap ne bacha liya!",
                ],
            },
            {
                "id": "buy_toy",
                "label": "🎮 Khareed lo — Rs. {toy}",
                "sub": "Maza aayega!",
                "action": "spend",
                "amount_key": "toy",
                "spend_description": "Quest: Video Game",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "Game mil gayi!",
                "outcome_lines": [
                    "Rs. {toy} chala gaya — ab aapke paas Rs. {balance_after} hain.",
                    "Game khelne mein maza aaya, lekin goal '{goal}' ke liye ab aur zyada time lagega.",
                    "Yaad rakho: jo kharch kiya wo wapas nahi aata — har khareed ka sochna zaroori hai!",
                ],
            },
        ],
        "reflection": {
            "question": "Kharidne se pehle kya sochna chahiye?",
            "options": [
                {
                    "id": "need_vs_want",
                    "label": "🤔 Yeh zaroorat hai ya khwahish?",
                    "bot_line": "Perfect! Need aur want ka farq samajhna bohat zaroori hai! \U0001f916",
                },
                {
                    "id": "just_buy",
                    "label": "🛒 Pasand aaya to khareed lo",
                    "bot_line": "Hmm... thora sochna chahiye pehle \u2014 paisay wapas nahi aate! \U0001f916",
                },
            ],
        },
    },
    {
        "id": "vq1_first_save",
        "level": 1,
        "title": "Pehla Qadam: Bachana Seekho!",
        "icon": "🎯",
        "concept": "Saving & Balance",
        "scenario_lines": [
            "Aapke paas Rs. {balance} hain.",
            "Goal '{goal}' ke liye Rs. {save} save karo!",
            "Bachana seekhna sab se important financial skill hai.",
        ],
        "choices": [
            {
                "id": "save_big",
                "label": "💰 Rs. {save} save karo — goal mein!",
                "sub": "Smart choice!",
                "action": "save",
                "amount_key": "save",
                "was_wise": True,
                "verdict": "win",
                "headline": "Shabash! Pehla save ho gaya!",
                "outcome_lines": [
                    "Rs. {save} goal '{goal}' mein chale gaye — ab {pct_after}% complete hai!",
                    "Jab aap save karte ho, aap apne future self ko gift dete ho.",
                    "Balance kam hua lekin goal ke qareeb ho gaye — yehi smart money management hai!",
                ],
            },
            {
                "id": "save_small",
                "label": "🪙 Thoda bachao — Rs. {small}",
                "sub": "Chota qadam bhi theek hai",
                "action": "save",
                "amount_key": "small",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "Theek hai — chalo chalta hai!",
                "outcome_lines": [
                    "Rs. {small} save huye — goal ab {pct_after}% complete hai.",
                    "Thoda bhi bachana acha hai, lekin zyada bachane se goal jaldi poora hota hai!",
                    "Agle baar thoda aur zyada save karne ki koshish karo.",
                ],
            },
        ],
        "reflection": {
            "question": "Bachana kyun zaroori hai?",
            "options": [
                {
                    "id": "future_goals",
                    "label": "🎯 Future goals ke liye",
                    "bot_line": "Bilkul sahi! Bachana future ki tayari hai! \U0001f916",
                },
                {
                    "id": "just_habit",
                    "label": "💪 Bas achi aadat hai",
                    "bot_line": "Haan! Achi aadatein wealth banati hain! \U0001f916",
                },
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round10(value) -> int:
    """Round to the nearest multiple of 10 (half up). Returns int."""
    d = Decimal(str(value))
    return int((d / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 10)


def _rs(value) -> str:
    """Format money for display: whole amounts without trailing decimals."""
    d = Decimal(str(value))
    if d == d.to_integral_value():
        return str(int(d))
    return str(d.normalize())


def _find_vault_quest(quest_id: str) -> dict:
    """Find a vault quest by ID."""
    quest = next((q for q in VAULT_QUESTS if q["id"] == quest_id), None)
    if not quest:
        raise HTTPException(status_code=400, detail="Invalid quest selected.")
    return quest


def _vault_quest_amounts(quest: dict, ctx: dict) -> dict:
    """Compute scenario amounts for a vault quest based on child context."""
    balance = ctx["balance"]
    remaining = ctx["remaining"]
    
    quest_id = quest["id"]
    
    if quest_id == "vq1_pocket_money":
        # Earned amount = 20% of balance (rounded to 10s), min Rs. 100
        earn = max(_round10(balance * Decimal("0.2")), 100)
        save = _round10(earn * Decimal("0.7"))  # Save 70% of earning
        save = min(save, int(remaining)) if remaining > 0 else 0
        keep = earn - save
        return {
            "earn": earn, "save": save, "keep": keep,
            "remaining": int(remaining),
        }
    
    if quest_id == "vq1_spend_wisely":
        # Toy costs ~40% of balance, rounded to 10s
        toy = max(_round10(balance * Decimal("0.4")), 50)
        balance_after = int(balance) - toy
        return {
            "toy": toy,
            "balance_after": max(balance_after, 0),
            "remaining": int(remaining),
        }
    
    if quest_id == "vq1_first_save":
        # Save 30% of balance (rounded to 10s), capped at goal remaining
        save = min(_round10(balance * Decimal("0.3")), int(remaining)) if remaining > 0 else 0
        small = max(_round10(balance * Decimal("0.1")), 10)  # At least Rs. 10
        return {"save": save, "small": small, "remaining": int(remaining)}
    
    # Default: return balance for formatting
    return {"balance": int(balance)}


def _vault_quest_context(db: Session, child: Child) -> dict:
    """Snapshot of child's state for vault quest availability."""
    balance = child.wallet.balance
    goal = get_active_goal(db, child.id)
    
    remaining = Decimal("0")
    goal_name = "Naya Goal"
    if goal:
        remaining = goal.target_amount - goal.saved_amount
        goal_name = goal.name
    
    # Get completed vault quests from VaultProgress
    progress_rows = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id)
        .all()
    )
    done_quest_ids = set()
    for row in progress_rows:
        if row.quests_done:
            done_quest_ids.update(json.loads(row.quests_done))
    
    return {
        "balance": balance,
        "goal": goal,
        "goal_name": goal_name,
        "remaining": remaining,
        "done_quest_ids": done_quest_ids,
    }


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def get_or_create_progress(db: Session, child: Child, level: int) -> VaultProgress:
    """Get or create a VaultProgress row for a child/level."""
    progress = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id, VaultProgress.level == level)
        .first()
    )
    if not progress:
        progress = VaultProgress(
            child_id=child.id,
            level=level,
            quests_done="[]",
            challenge_passed=0,
            best_challenge_score=0,
        )
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def get_level_status(child: Child, progress: VaultProgress | None) -> str:
    """Determine the status of a level for a child.
    
    Returns: locked | available | in_progress | completed
    """
    level = progress.level if progress else 1
    vault_level = child.vault_level or 0
    
    # Check if level is unlocked
    is_unlocked = vault_level >= (level - 1)
    
    if not is_unlocked:
        return "locked"
    
    # Check if completed
    if progress and progress.challenge_passed == 1 and progress.completed_at:
        return "completed"
    
    # Check if in progress
    quests_done = json.loads(progress.quests_done) if progress and progress.quests_done else []
    if quests_done or (progress and progress.challenge_passed):
        return "in_progress"
    
    return "available"


def check_level_complete(level: int, quests_done: list[str]) -> bool:
    """Check if all required quests for a level are done."""
    required = VAULT_LEVEL_QUESTS.get(level, [])
    return all(q in quests_done for q in required)


# ---------------------------------------------------------------------------
# Quest completion
# ---------------------------------------------------------------------------

def complete_quest(db: Session, child: Child, level: int, quest_id: str) -> dict:
    """Mark a quest as done within a level.
    
    Returns: {quests_done: [...], level_complete: bool}
    """
    # Validate level exists
    if level < 1 or level > 8:
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    # Get or create progress
    progress = get_or_create_progress(db, child, level)
    
    # Check if level already completed
    if progress.challenge_passed and progress.completed_at:
        raise HTTPException(status_code=400, detail=f"Level {level} is already completed.")
    
    # Check if quest is already done
    quests_done = json.loads(progress.quests_done) if progress.quests_done else []
    if quest_id in quests_done:
        return {"quests_done": quests_done, "level_complete": False}
    
    # Validate quest belongs to this level
    required_quests = VAULT_LEVEL_QUESTS.get(level, [])
    if quest_id not in required_quests:
        raise HTTPException(
            status_code=400, 
            detail=f"Quest '{quest_id}' is not part of Level {level}."
        )
    
    # Mark quest as done
    quests_done.append(quest_id)
    progress.quests_done = json.dumps(quests_done)
    
    # Check if all quests done (but don't auto-complete — need challenge)
    level_complete = check_level_complete(level, quests_done) and progress.challenge_passed == 1
    
    db.commit()
    db.refresh(progress)
    
    return {
        "quests_done": quests_done,
        "level_complete": level_complete,
    }


# ---------------------------------------------------------------------------
# Challenge completion
# ---------------------------------------------------------------------------

def pass_challenge(db: Session, child: Child, level: int, score: int = 100) -> dict:
    """Mark the level-end challenge as passed.
    
    Returns: {challenge_passed: bool, level_complete: bool, level_unlocked: int | None}
    """
    # Validate level
    if level < 1 or level > 8:
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    # Get or create progress
    progress = get_or_create_progress(db, child, level)
    
    # Check if already completed
    if progress.challenge_passed and progress.completed_at:
        return {
            "challenge_passed": True,
            "level_complete": True,
            "level_unlocked": None,
        }
    
    # Mark challenge as passed
    progress.challenge_passed = 1
    progress.best_challenge_score = max(progress.best_challenge_score or 0, score)
    
    # Check if level is now complete (all quests + challenge)
    quests_done = json.loads(progress.quests_done) if progress.quests_done else []
    all_quests_done = check_level_complete(level, quests_done)
    
    level_unlocked = None
    
    if all_quests_done:
        # Level complete!
        progress.completed_at = datetime.utcnow()
        
        # Unlock next level
        if level < 8:
            child.vault_level = level  # Level N complete → vault_level = N → Level N+1 unlocks
            level_unlocked = level + 1
        else:
            # Level 8 complete — final level
            child.vault_level = 8
    else:
        # Challenge passed but quests not all done yet
        # Note: For Phase 2, levels have no required quests, so this path
        # means the level should complete immediately if no quests required
        required_quests = VAULT_LEVEL_QUESTS.get(level, [])
        if len(required_quests) == 0:
            # No quests required — completing challenge completes the level
            progress.completed_at = datetime.utcnow()
            if level < 8:
                child.vault_level = level
                level_unlocked = level + 1
            else:
                child.vault_level = 8
    
    db.commit()
    db.refresh(progress)
    db.refresh(child)
    
    return {
        "challenge_passed": True,
        "level_complete": progress.completed_at is not None,
        "level_unlocked": level_unlocked,
    }


# ---------------------------------------------------------------------------
# Level reset (for retry)
# ---------------------------------------------------------------------------

def reset_level(db: Session, child: Child, level: int) -> dict:
    """Reset a level's progress (for replay). Not used in Phase 2."""
    progress = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id, VaultProgress.level == level)
        .first()
    )
    if progress:
        progress.quests_done = "[]"
        progress.challenge_passed = 0
        progress.best_challenge_score = 0
        progress.completed_at = None
        db.commit()
    return {"level": level, "reset": True}


# ---------------------------------------------------------------------------
# Level 1 — First Goal (goal-based progression instead of quests)
# ---------------------------------------------------------------------------

def get_level1_goal_status(db: Session, child: Child) -> dict:
    """Get the Level 1 goal status for the child.

    Returns goal info if one exists (active or completed), otherwise null.
    Also returns Level 1 completion state (reflection done / level unlocked).
    """
    progress = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id, VaultProgress.level == 1)
        .first()
    )

    # Level 1 already completed (reflection done)
    if progress and progress.goal_reflection_done == 1 and progress.completed_at:
        return {
            "has_goal": False,
            "goal": None,
            "level_complete": True,
            "reflection_done": True,
        }

    # Look for active goal first
    goal = get_active_goal(db, child.id)
    if goal:
        pct = int(goal.saved_amount / goal.target_amount * 100) if goal.target_amount else 0
        goal_reached = goal.saved_amount >= goal.target_amount
        return {
            "has_goal": True,
            "goal": {
                "id": goal.id,
                "name": goal.name,
                "target_amount": float(goal.target_amount),
                "saved_amount": float(goal.saved_amount),
                "progress_pct": min(pct, 100),
                "goal_reached": goal_reached,
            },
            "level_complete": False,
            "reflection_done": False,
        }

    # Look for most recently completed goal (goal reached but no reflection yet)
    completed_goal = (
        db.query(Goal)
        .filter(Goal.child_id == child.id, Goal.status == "completed")
        .order_by(Goal.created_at.desc())
        .first()
    )
    if completed_goal:
        return {
            "has_goal": True,
            "goal": {
                "id": completed_goal.id,
                "name": completed_goal.name,
                "target_amount": float(completed_goal.target_amount),
                "saved_amount": float(completed_goal.saved_amount),
                "progress_pct": 100,
                "goal_reached": True,
            },
            "level_complete": False,
            "reflection_done": False,
        }

    return {
        "has_goal": False,
        "goal": None,
        "level_complete": False,
        "reflection_done": False,
    }


def complete_level1(db: Session, child: Child, reflection_answer: str) -> dict:
    """Mark Level 1 complete after the child submits their goal reflection.

    Requirements:
    - A goal must exist with saved_amount >= target_amount.
    - Reflection must not already be done.

    On success:
    - Records the reflection answer.
    - Marks VaultProgress.challenge_passed = 1.
    - Sets completed_at.
    - Unlocks Level 2 via child.vault_level = 1.
    """
    progress = get_or_create_progress(db, child, 1)

    # Already completed — idempotent
    if progress.goal_reflection_done == 1 and progress.completed_at:
        return {
            "level_complete": True,
            "level_unlocked": None,
            "already_completed": True,
        }

    # Find a goal that reached its target
    goal = get_active_goal(db, child.id)
    if not goal or goal.saved_amount < goal.target_amount:
        goal = (
            db.query(Goal)
            .filter(Goal.child_id == child.id, Goal.status == "completed")
            .order_by(Goal.created_at.desc())
            .first()
        )

    if not goal or goal.saved_amount < goal.target_amount:
        raise HTTPException(
            status_code=400,
            detail="Goal abhi complete nahi hua — pehle target amount tak paise bachao!",
        )

    # Record reflection
    progress.goal_reflection_done = 1
    progress.challenge_passed = 1
    progress.best_challenge_score = 100

    level_unlocked = None
    if not progress.completed_at:
        progress.completed_at = datetime.utcnow()
        child.vault_level = max(child.vault_level or 0, 1)  # Unlocks Level 2
        level_unlocked = 2

    db.commit()
    db.refresh(progress)
    db.refresh(child)

    return {
        "level_complete": True,
        "level_unlocked": level_unlocked,
        "already_completed": False,
    }


def get_certificate_data(db: Session, child: Child) -> dict:
    """Build certificate data for Level 1 completion.

    Returns child info, goal details, earned badges, transaction stats,
    and completion timestamp for rendering a certificate.
    """
    progress = (
        db.query(VaultProgress)
        .filter(VaultProgress.child_id == child.id, VaultProgress.level == 1)
        .first()
    )

    if not progress or progress.goal_reflection_done != 1:
        raise HTTPException(
            status_code=400,
            detail="Level 1 abhi complete nahi hua!",
        )

    # Get the completed goal
    goal = (
        db.query(Goal)
        .filter(Goal.child_id == child.id, Goal.status == "completed")
        .order_by(Goal.created_at.desc())
        .first()
    )

    goal_info = None
    if goal:
        goal_info = {
            "name": goal.name,
            "target_amount": float(goal.target_amount),
            "saved_amount": float(goal.saved_amount),
        }

    # Earned badges
    from app.services.badge_service import compute_badges
    badges = compute_badges(db, child)
    earned_badges = [
        {"name": b["name"], "icon": b["icon"], "description": b.get("condition_desc", "")}
        for b in badges if b["earned"]
    ]

    # Transaction stats
    transactions = (
        db.query(Transaction)
        .filter(Transaction.child_id == child.id)
        .all()
    )
    total_saved = sum(
        float(t.amount) for t in transactions if t.type == "SAVE"
    )
    total_spent = sum(
        float(t.amount) for t in transactions if t.type == "SPEND"
    )
    total_earned = sum(
        float(t.amount) for t in transactions if t.type == "EARN"
    )

    # Businesses completed
    businesses_count = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "BUSINESS")
        .count()
    )

    return {
        "child_id": child.anonymous_id,
        "child_name": child.anonymous_id,
        "goal": goal_info,
        "badges": earned_badges,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "reflection": "",
        "stats": {
            "total_saved": total_saved,
            "total_spent": total_spent,
            "total_earned": total_earned,
            "businesses_completed": businesses_count,
            "transaction_count": len(transactions),
        },
        "wallet_balance": float(child.wallet.balance) if child.wallet else 0,
    }


# ---------------------------------------------------------------------------
# Vault Quest Engine (reusable for all levels)
# ---------------------------------------------------------------------------

def get_vault_quests_for_level(level: int) -> list[dict]:
    """Get all quest definitions for a specific level."""
    return [q for q in VAULT_QUESTS if q.get("level") == level]


def get_vault_quest_view(quest: dict, ctx: dict) -> dict:
    """Build the API view of a vault quest for the child's current state."""
    amounts = _vault_quest_amounts(quest, ctx)
    
    # Format scenario lines with context values
    fmt = {
        "balance": _rs(ctx["balance"]),
        "goal": ctx["goal_name"],
        "remaining": _rs(ctx["remaining"]),
        **amounts,
    }
    
    scenario_lines = [
        line.format(**fmt) for line in quest["scenario_lines"]
    ]
    
    # Build choices with formatted labels
    choices = []
    for choice in quest["choices"]:
        choices.append({
            "id": choice["id"],
            "label": choice["label"].format(**fmt),
            "sub": choice.get("sub", ""),
        })
    
    # Check if quest is done
    is_done = quest["id"] in ctx["done_quest_ids"]
    
    return {
        "id": quest["id"],
        "title": quest["title"],
        "icon": quest["icon"],
        "concept": quest["concept"],
        "scenario_lines": scenario_lines,
        "choices": choices,
        "is_done": is_done,
    }


def get_vault_level_quests(db: Session, child: Child, level: int) -> list[dict]:
    """Get the quest view for all quests in a level."""
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    ctx = _vault_quest_context(db, child)
    quests = get_vault_quests_for_level(level)
    
    return [get_vault_quest_view(q, ctx) for q in quests]


def resolve_vault_quest(
    db: Session, 
    child: Child, 
    level: int, 
    quest_id: str, 
    choice_id: str
) -> dict:
    """Resolve a vault quest choice.
    
    Executes wallet mutations, records GrowActivity, updates VaultProgress.
    Returns outcome data for display.
    """
    quest = _find_vault_quest(quest_id)
    
    # Verify quest belongs to this level
    if quest.get("level") != level:
        raise HTTPException(
            status_code=400, 
            detail=f"Quest '{quest_id}' is not part of Level {level}."
        )
    
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    ctx = _vault_quest_context(db, child)
    
    # Check if quest already done
    if quest_id in ctx["done_quest_ids"]:
        raise HTTPException(status_code=400, detail="Ye quest already complete ho chuki hai.")
    
    # Find the choice
    choice = next((c for c in quest["choices"] if c["id"] == choice_id), None)
    if not choice:
        raise HTTPException(status_code=400, detail="Invalid choice selected.")
    
    # Compute amounts
    amounts = _vault_quest_amounts(quest, ctx)
    goal = ctx["goal"]
    balance_before = ctx["balance"]
    
    # Record the activity
    details = {
        "quest_id": quest_id,
        "level": level,
        "choice_id": choice_id,
        "was_wise": choice["was_wise"],
        "verdict": choice["verdict"],
        "headline": choice.get("headline", ""),
        "snapshot": {
            "balance_before": float(balance_before),
            "goal_name": ctx["goal_name"],
        },
    }
    activity = GrowActivity(
        child_id=child.id,
        type="VAULT_QUEST",
        details=json.dumps(details),
    )
    db.add(activity)
    
    # Execute the action
    pct_after = None
    try:
        if choice["action"] == "spend":
            amount = Decimal(str(amounts[choice["amount_key"]]))
            wallet = child.wallet
            if amount > wallet.balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"Aapke paas sirf Rs. {wallet.balance} hain.",
                )
            wallet.balance -= amount
            db.add(Transaction(
                child_id=child.id,
                type="SPEND",
                amount=amount,
                description=f"Vault Quest: {quest['title']}",
            ))
            db.commit()
            db.refresh(wallet)
            
        elif choice["action"] == "save":
            if not goal:
                raise HTTPException(
                    status_code=400,
                    detail="Goal chahiye — pehle SAVE mein ek goal banao!",
                )
            amount = Decimal(str(amounts[choice["amount_key"]]))
            save_to_goal(db, child, goal, amount)
            
        elif choice["action"] == "none":
            # No wallet mutation — purely educational choice
            db.commit()
            
    except HTTPException:
        db.rollback()
        raise
    
    # Calculate pct_after for display
    if goal and goal.target_amount:
        pct_after = int(goal.saved_amount / goal.target_amount * 100)
    
    # Update VaultProgress.quests_done
    progress = get_or_create_progress(db, child, level)
    quests_done = json.loads(progress.quests_done) if progress.quests_done else []
    if quest_id not in quests_done:
        quests_done.append(quest_id)
        progress.quests_done = json.dumps(quests_done)
        db.commit()
    
    # Build outcome
    fmt = {
        "balance": _rs(balance_before),
        "goal": ctx["goal_name"],
        "remaining": _rs(ctx["remaining"]),
        "pct_after": pct_after if pct_after is not None else 0,
        **amounts,
    }
    outcome_lines = [line.format(**fmt) for line in choice["outcome_lines"]]
    
    return {
        "quest_id": quest_id,
        "choice_id": choice_id,
        "headline": choice.get("headline", ""),
        "outcome_lines": outcome_lines,
        "was_wise": choice["was_wise"],
        "verdict": choice["verdict"],
        "reflection": quest.get("reflection"),
    }


def submit_vault_reflection(
    db: Session, 
    child: Child, 
    quest_id: str, 
    answer_id: str
) -> dict:
    """Record a reflection answer for a vault quest.
    
    Returns the bot response line.
    """
    quest = _find_vault_quest(quest_id)
    reflection = quest.get("reflection")
    
    if not reflection:
        return {"bot_line": "Quest complete!"}
    
    # Find the answer
    answer = next((o for o in reflection["options"] if o["id"] == answer_id), None)
    if not answer:
        return {"bot_line": "Reflection recorded!"}
    
    # Record in GrowActivity (append to existing quest activity)
    activity = (
        db.query(GrowActivity)
        .filter(
            GrowActivity.child_id == child.id,
            GrowActivity.type == "VAULT_QUEST",
        )
        .order_by(GrowActivity.id.desc())
        .first()
    )
    
    if activity and activity.details:
        details = json.loads(activity.details)
        if details.get("quest_id") == quest_id:
            details["reflection_answer"] = answer_id
            activity.details = json.dumps(details)
            db.commit()
    
    return {"bot_line": answer["bot_line"]}


# ---------------------------------------------------------------------------
# Level Challenges (scenario-based questions, no wallet mutation)
# ---------------------------------------------------------------------------

VAULT_CHALLENGES = {
    1: {
        "level": 1,
        "title": "Level 1 Challenge: Save & Earn",
        "pass_threshold": 2,  # 2 out of 3 correct to pass
        "questions": [
            {
                "id": "l1q1",
                "question": "Ali ne Rs. 500 kamaye aur Rs. 400 snacks pe kharch diye. Us ne kitne paise bachaye?",
                "options": [
                    {"id": "a", "label": "Rs. 100", "correct": True},
                    {"id": "b", "label": "Rs. 500", "correct": False},
                    {"id": "c", "label": "Rs. 400", "correct": False},
                ],
                "explanation": "500 - 400 = 100. Jo kamaya us mein se jo kharch kiya wo minus karo!",
            },
            {
                "id": "l1q2",
                "question": "Aap ke paas Rs. 1000 hain aur aap Rs. 300 ka khilona khareedna chahte ho. Khareedne ke baad kitne paise bachein ge?",
                "options": [
                    {"id": "a", "label": "Rs. 1000", "correct": False},
                    {"id": "b", "label": "Rs. 700", "correct": True},
                    {"id": "c", "label": "Rs. 300", "correct": False},
                ],
                "explanation": "1000 - 300 = 700. Jab kharch karte ho to balance kam hota hai!",
            },
            {
                "id": "l1q3",
                "question": "Kamai ka paisa kaise handle karna chahiye?",
                "options": [
                    {"id": "a", "label": "Sab kuch snacks pe kharch karo", "correct": False},
                    {"id": "b", "label": "Pehle save karo, phir kharch karo", "correct": True},
                    {"id": "c", "label": "Sab paisay dost ko de do", "correct": False},
                ],
                "explanation": "Smart log pehle save karte hain, phir kharch karte hain — yehi earning ka secret hai!",
            },
        ],
    },
    # Challenges for levels 2-8 will be added in future phases
}


def get_challenge_for_level(level: int) -> dict:
    """Get the challenge definition for a level."""
    challenge = VAULT_CHALLENGES.get(level)
    if not challenge:
        raise HTTPException(status_code=404, detail=f"No challenge available for Level {level}.")
    return challenge


def submit_level_challenge(
    db: Session,
    child: Child,
    level: int,
    answers: dict[str, str],  # {question_id: answer_id}
) -> dict:
    """Submit answers for a level challenge.
    
    No wallet mutation. Returns score and pass/fail.
    If passed AND all quests done, completes the level.
    """
    # Validate level
    if level < 1 or level > 8:
        raise HTTPException(status_code=400, detail="Invalid level number.")
    
    # Check level is unlocked
    vault_level = child.vault_level or 0
    if vault_level < (level - 1):
        raise HTTPException(status_code=403, detail=f"Level {level} is locked.")
    
    challenge = get_challenge_for_level(level)
    questions = challenge["questions"]
    pass_threshold = challenge["pass_threshold"]
    
    # Score the answers
    correct_count = 0
    results = []
    for q in questions:
        answer_id = answers.get(q["id"], "")
        selected_option = next((o for o in q["options"] if o["id"] == answer_id), None)
        is_correct = selected_option and selected_option.get("correct", False)
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "your_answer": selected_option["label"] if selected_option else "N/A",
            "correct": is_correct,
            "explanation": q["explanation"],
        })
    
    passed = correct_count >= pass_threshold
    score = int((correct_count / len(questions)) * 100)
    
    level_complete = False
    level_unlocked = None
    
    if passed:
        # Get or create progress
        progress = get_or_create_progress(db, child, level)
        
        # Check if already completed
        if progress.challenge_passed and progress.completed_at:
            return {
                "passed": True,
                "score": score,
                "correct": correct_count,
                "total": len(questions),
                "results": results,
                "level_complete": True,
                "level_unlocked": None,
                "already_completed": True,
            }
        
        # Mark challenge as passed
        progress.challenge_passed = 1
        progress.best_challenge_score = max(progress.best_challenge_score or 0, score)
        
        # Check if level is now complete
        quests_done = json.loads(progress.quests_done) if progress.quests_done else []
        all_quests_done = check_level_complete(level, quests_done)
        
        if all_quests_done:
            progress.completed_at = datetime.utcnow()
            if level < 8:
                child.vault_level = level
                level_unlocked = level + 1
            else:
                child.vault_level = 8
            level_complete = True
        
        db.commit()
        db.refresh(progress)
        db.refresh(child)
    
    return {
        "passed": passed,
        "score": score,
        "correct": correct_count,
        "total": len(questions),
        "results": results,
        "level_complete": level_complete,
        "level_unlocked": level_unlocked,
        "already_completed": False,
    }
