"""Quest service — V1 trade-off quests (3 quests).

Each quest centers on ONE real financial trade-off. Quest state,
progress, and completion are checked deterministically against existing
wallet / transaction / GrowActivity data — no AI anywhere in this module.

Quest completions are recorded as GrowActivity rows with type="QUEST"
(the same pattern SKILL uses), so no new tables are needed and every
completion automatically counts toward the existing level system.
"""

import json
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Child, Transaction, GrowActivity
from app.services.wallet_service import get_active_goal, save_to_goal
from app.services.grow_service import invest


# ---------------------------------------------------------------------------
# Quest definitions (static content — same pattern as SPEND_SCENARIOS)
# ---------------------------------------------------------------------------

QUESTS = [
    {
        "id": "q1_opportunity_cost",
        "title": "Cricket Kit Ya Goal?",
        "icon": "🏏",
        "concept": "Opportunity Cost",
        "scenario_lines": [
            "Aapke paas Rs. {balance} hain aur cricket kit Rs. {kit} ki hai — dono chahiye!",
            "Lekin goal '{goal}' ke liye bhi Rs. {save} save karna hai.",
            "Dono ek saath mumkin nahi. Ek chunna hai — kya karo ge?",
        ],
        "choices": [
            {
                "id": "buy_kit",
                "label": "🏏 Kit le lo — Rs. {kit}",
                "sub": "Goal ruk jayega",
                "action": "spend",
                "amount_key": "kit",
                "spend_description": "Quest: Cricket Kit",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "Kit mil gayi — maza aaya!",
                "outcome_lines": [
                    "Kit mil gayi — maza aaya! {kit_line}",
                    "kit se aap ko waqti khushi mili ab aap ko goal acheive karny mein or time lagay ga.",
                    "kabhi kabhi baray goal acheive karny k liye aap ko temporary khushi bardasht karni parhti hai.",
                    "Is se aap ne opportunity cost ka concept seekha — aap ko iski value samajhni parhti hai.",   
                ],
            },
            {
                "id": "save_first",
                "label": "🎯 Goal pehle — Rs. {save} save",
                "sub": "Kit agle mahine",
                "action": "save",
                "amount_key": "save",
                "was_wise": True,
                "verdict": "win",
                "headline": "Goal pehle — smart!",
                "outcome_lines": [
                    "Smart! Rs. {save} goal mein chale gaye — ab {pct_after}% complete hai.",
                    "Kit ke paisay kaam nahi aaye, lekin goal strong hua.",
                    "Jo cheez humne NAHI li, uski bhi ek qeemat hoti hai — isi ko opportunity cost kehte hain.",
                ],
            },
        ],
        "reflection": {
            "question": "Agle mahine phir same problem ho to kya karoge?",
            "options": [
                {
                    "id": "goal_first",
                    "label": "🎯 Goal pehle, wish baad mein",
                    "bot_line": "Wah! Yahi hai smart khiladi wali soch! 🤖",
                },
                {
                    "id": "wish_first",
                    "label": "🏏 Wish pehle, goal baad mein",
                    "bot_line": "Theek hai bhai — bas cost samajh ke lena! 🤖",
                },
            ],
        },
    },
    {
        "id": "q2_save_discipline",
        "title": "Party Ya Paisay?",
        "icon": "🎉",
        "concept": "Saving Discipline",
        "scenario_lines": [
            "Kal sab dost arcade ja rahe hain — Rs. {cost} per head.",
            "Aapke paas bilkul itne hi hain, aur isi hafte goal '{goal}' ka installment bhi dena hai.",
            "Dost pressure mein: \"Chal yaar, ek baar ki baat hai!\"",
        ],
        "choices": [
            {
                "id": "join_party",
                "label": "🎉 Doston ke saath jao — Rs. {cost}",
                "sub": "Installment agle hafte",
                "action": "spend",
                "amount_key": "cost",
                "spend_description": "Quest: Arcade Party",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "Party mast thi!",
                "outcome_lines": [
                    "Party mast thi, dost bhi khush! Lekin goal ka installment reh gaya.",
                    "\"Ek baar ki baat\" har hafte ho jaye, to goal kabhi poora nahi hota.",
                    "Agli party ka plan ab pehle se banao — aur uske liye alag bachao.",
                ],
            },
            {
                "id": "skip_and_save",
                "label": "💪 Is baar skip — Rs. {save} goal mein",
                "sub": "Agle mahine sab ke saath",
                "action": "save",
                "amount_key": "save",
                "was_wise": True,
                "verdict": "win",
                "headline": "Discipline jeet gayi!",
                "outcome_lines": [
                    "Discipline jeet gayi! Rs. {save} goal mein — ab {pct_after}% complete hai.",
                    "Dost agle mahine bhi dost rahenge, lekin aaj ka installment wapas nahi aata.",
                    "\"Nahi\" bolna bhi ek money superpower hai.",
                ],
            },
        ],
        "reflection": {
            "question": "Is baar asal mein kaun jeeta?",
            "options": [
                {
                    "id": "friends_feeling",
                    "label": "🎂 Doston wali feeling",
                    "bot_line": "Sach boltay ho — ijazat hai! 🤖",
                },
                {
                    "id": "goal_joy",
                    "label": "🎯 Goal wali khushi",
                    "bot_line": "Shabash! Asli champion! 🤖",
                },
            ],
        },
    },
    {
        "id": "q3_risk_safety",
        "title": "Shortcut Ya Safe Raasta?",
        "icon": "⚡",
        "concept": "Risk vs Safety",
        "scenario_lines": [
            "Goal '{goal}' ke liye sirf Rs. {need} aur chahiye — bilkul qareeb ho!",
            "Dost kehta hai: \"Rs. {amount} startup mein laga do — 60% tak profit ho sakta hai!\"",
            "Lekin startup gir bhi sakta hai — 50% tak loss. Faisla tumhara hai.",
        ],
        "choices": [
            {
                "id": "safe_route",
                "label": "🎯 Safe raasta — Rs. {need} save karo",
                "sub": "Goal aaj hi complete!",
                "action": "save",
                "amount_key": "need",
                "was_wise": True,
                "verdict": "win",
                "headline": "GOAL COMPLETE! 🎉",
                "outcome_lines": [
                    "GOAL COMPLETE! 🎉 Safe raaste ne kaam kiya.",
                    "Rule yaad rakho: jis paisay ki jald zaroorat ho, usay risk mein nahi dalte.",
                    "Baray investors bhi yahi pehly seekhta hai.",
                ],
            },
            {
                "id": "take_shortcut",
                "label": "⚡ Shortcut — Rs. {amount} startup mein",
                "sub": "Double ka chance, girne ka risk",
                "action": "invest",
                "amount_key": "amount",
                "was_wise": False,
                "verdict": "near_miss",
                "headline": "",
                "outcome_lines_profit": [
                    "Is baar luck saath thi — Rs. {profit} profit! Lekin smart choice ye nahi thi.",
                    "Agar startup girta, to goal poora mahina aur late hota.",
                    "Acha result aur acha faisla — dono alag cheezein hain.",
                ],
                "outcome_lines_loss": [
                    "Startup gir gaya — Rs. {loss} ka loss. Ab goal ke liye Rs. {need} aur chahiye.",
                    "Yahi risk ka asal chehra hai — jitna bara chance, utna bara nuksan.",
                    "Zaroorat ke paisay ko risk mein dalna jua hai, investment nahi.",
                ],
            },
        ],
        "reflection": {
            "question": "Jis paisay ki jald zaroorat ho, wo...",
            "options": [
                {
                    "id": "risk_it",
                    "label": "⚡ Risk mein lagao — barha do",
                    "bot_line": "Himmat hai! Lekin zaroorat ka paisa alag rakho, hero! 🤖",
                },
                {
                    "id": "stay_safe",
                    "label": "🌱 Safe rakho — zaroorat pehle",
                    "bot_line": "Bilkul sahi! Ab tum investor ki tarah sochte ho! 🤖",
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


def _ceil_int(value) -> int:
    """Round a Decimal up to the next whole number. Returns int."""
    return int(Decimal(str(value)).to_integral_value(rounding=ROUND_CEILING))


def _rs(value) -> str:
    """Format money for display: whole amounts without trailing decimals."""
    d = Decimal(str(value))
    if d == d.to_integral_value():
        return str(int(d))
    return str(d.normalize())


def _find_quest(quest_id: str) -> dict:
    quest = next((q for q in QUESTS if q["id"] == quest_id), None)
    if not quest:
        raise HTTPException(status_code=400, detail="Invalid quest selected.")
    return quest


def _quest_context(db: Session, child: Child) -> dict:
    """Snapshot of the child's state relevant to quest availability."""
    balance = child.wallet.balance
    goal = get_active_goal(db, child.id)

    remaining = Decimal("0")
    goal_name = ""
    if goal:
        remaining = goal.target_amount - goal.saved_amount
        goal_name = goal.name

    has_investment = (
        db.query(GrowActivity.id)
        .filter(
            GrowActivity.child_id == child.id,
            GrowActivity.type == "INVESTMENT",
        )
        .first()
        is not None
    )

    done_details: dict[str, dict] = {}
    quest_activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "QUEST")
        .all()
    )
    for act in quest_activities:
        if act.details:
            details = json.loads(act.details)
            qid = details.get("quest_id")
            if qid:
                done_details[qid] = details

    return {
        "balance": balance,
        "goal": goal,
        "goal_name": goal_name,
        "remaining": remaining,
        "has_investment": has_investment,
        "done_details": done_details,
    }


def _quest_amounts(quest_id: str, ctx: dict) -> dict:
    """Compute the scenario amounts from the child's current state.

    Formulas keep the trade-off real at every balance:
    - q1: kit + save ≈ 1.3 x balance -> both are never affordable together
    - q2: cost = half the balance   -> the outing money IS the goal money
    - q3: the safe option completes the goal exactly; the shortcut stakes it
    """
    balance = ctx["balance"]
    remaining = ctx["remaining"]

    if quest_id == "q1_opportunity_cost":
        kit = _round10(balance * Decimal("0.9"))
        save = min(_round10(balance * Decimal("0.4")), _ceil_int(remaining))
        return {"kit": kit, "save": save, "remaining": _ceil_int(remaining)}

    if quest_id == "q2_save_discipline":
        cost = _round10(balance * Decimal("0.5"))
        save = min(cost, _ceil_int(remaining))
        return {"cost": cost, "save": save, "remaining": _ceil_int(remaining)}

    if quest_id == "q3_risk_safety":
        need = _ceil_int(remaining)
        amount = _round10(need)
        return {"need": need, "amount": amount, "remaining": need}

    return {}


def _availability(quest_id: str, ctx: dict) -> tuple[bool, str]:
    """Return (is_available, lock_reason) for a quest given child context."""
    balance = ctx["balance"]
    remaining = ctx["remaining"]

    if ctx["goal"] is None:
        return False, "Goal chahiye — SAVE mein banao"

    if quest_id in ("q1_opportunity_cost", "q2_save_discipline"):
        if balance < Decimal("200"):
            return False, "Rs. 200+ balance chahiye"
        # Below Rs. 100 left, or within 10% of the balance, the goal is
        # close enough to just complete normally in SAVE.
        if remaining < Decimal("100") or remaining <= balance * Decimal("0.1"):
            return False, "Goal almost complete hai — bas complete karo!"

    if quest_id == "q3_risk_safety":
        if remaining < Decimal("100"):
            return False, "Goal almost complete hai — bas complete karo!"
        if not ctx["has_investment"]:
            return False, "Pehle GROW mein ek investment try karo"
        need = _ceil_int(remaining)
        amount = _round10(need)
        if balance < Decimal(str(max(need, amount))):
            return False, f"Rs. {need} balance chahiye — pehle paisay jama karo"

    return True, ""


def _build_quest_view(quest: dict, ctx: dict) -> dict:
    """Build the API view of one quest for the child's current state."""
    view = {
        "id": quest["id"],
        "title": quest["title"],
        "icon": quest["icon"],
        "concept": quest["concept"],
    }

    done = ctx["done_details"].get(quest["id"])
    if done:
        view["status"] = "completed"
        view["verdict"] = done.get("verdict", "")
        view["headline"] = done.get("headline", "")
        view["reflected"] = bool(done.get("reflection_answer"))
        return view

    available, reason = _availability(quest["id"], ctx)
    if not available:
        view["status"] = "locked"
        view["lock_reason"] = reason
        return view

    amounts = _quest_amounts(quest["id"], ctx)
    fmt = {
        "balance": _rs(ctx["balance"]),
        "goal": ctx["goal_name"],
        "remaining": _rs(amounts.get("remaining", ctx["remaining"])),
    }
    fmt.update({key: _rs(value) for key, value in amounts.items()})

    view["status"] = "available"
    view["scenario_lines"] = [line.format_map(fmt) for line in quest["scenario_lines"]]
    view["choices"] = [
        {"id": c["id"], "label": c["label"].format_map(fmt), "sub": c["sub"]}
        for c in quest["choices"]
    ]
    return view


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_quest_states(db: Session, child: Child) -> list[dict]:
    """Return the current view of all 3 quests for a child."""
    ctx = _quest_context(db, child)
    return [_build_quest_view(q, ctx) for q in QUESTS]


def resolve_quest(db: Session, child: Child, quest_id: str, choice_id: str) -> dict:
    """Resolve a quest choice and execute its real wallet/goal action.

    Deterministic: availability is re-validated, amounts are recomputed,
    and the verdict depends only on the chosen option. Completion is
    recorded as a GrowActivity(type="QUEST") row so it feeds the
    existing level system automatically.
    """
    quest = _find_quest(quest_id)
    ctx = _quest_context(db, child)

    if quest_id in ctx["done_details"]:
        raise HTTPException(status_code=400, detail="Ye quest already complete ho chuki hai.")

    available, _reason = _availability(quest_id, ctx)
    if not available:
        raise HTTPException(
            status_code=400, detail="Paisay kam ho gaye — quest abhi available nahi"
        )

    choice = next((c for c in quest["choices"] if c["id"] == choice_id), None)
    if not choice:
        raise HTTPException(status_code=400, detail="Invalid choice selected.")

    amounts = _quest_amounts(quest_id, ctx)
    goal = ctx["goal"]
    balance_before = ctx["balance"]
    remaining_before = _ceil_int(ctx["remaining"])

    details = {
        "quest_id": quest_id,
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
        type="QUEST",
        details=json.dumps(details),
    )
    db.add(activity)

    investment_result = None

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
                description=choice["spend_description"],
            ))
            db.commit()
            db.refresh(wallet)
        elif choice["action"] == "save":
            amount = Decimal(str(amounts[choice["amount_key"]]))
            save_to_goal(db, child, goal, amount)
        elif choice["action"] == "invest":
            amount = Decimal(str(amounts[choice["amount_key"]]))
            investment_result = invest(db, child, amount, "high")
    except HTTPException:
        db.rollback()
        raise

    # Goal state after the action (objects auto-reload after commit)
    goal_name = goal.name if goal else None
    goal_saved = goal.saved_amount if goal else None
    goal_target = goal.target_amount if goal else None
    goal_status = goal.status if goal else None
    pct_after = None
    if goal and goal_target:
        pct_after = int(goal.saved_amount / goal_target * 100)

    # Build the "yahan kya hua" lines
    kit = amounts.get("kit", 0)
    fmt = {
        "balance": _rs(balance_before),
        "goal": ctx["goal_name"],
        "remaining": _rs(remaining_before),
        "save": _rs(amounts.get("save", 0)),
        "kit": _rs(kit),
        "cost": _rs(amounts.get("cost", 0)),
        "need": _rs(amounts.get("need", 0)),
        "amount": _rs(amounts.get("amount", 0)),
        "pct_after": pct_after if pct_after is not None else 0,
    }
    if kit and kit >= remaining_before:
        fmt["kit_line"] = (
            f"Lekin Rs. {kit} se goal POORA ho sakta tha — "
            f"sirf Rs. {_rs(remaining_before)} chahiye the!"
        )
    elif kit:
        fmt["kit_line"] = (
            f"Lekin ye Rs. {_rs(kit)} goal ke {int(kit / remaining_before * 100)}% the."
        )
    else:
        fmt["kit_line"] = ""

    if choice["action"] == "invest":
        profit_loss = investment_result["profit_loss"]
        if profit_loss >= 0:
            fmt["profit"] = _rs(profit_loss)
            lines = [line.format_map(fmt) for line in choice["outcome_lines_profit"]]
            headline = "Luck saath tha — lekin..."
        else:
            fmt["loss"] = _rs(abs(profit_loss))
            lines = [line.format_map(fmt) for line in choice["outcome_lines_loss"]]
            headline = "Startup gir gaya!"
        details["headline"] = headline
        details["profit_loss"] = float(profit_loss)
        activity.details = json.dumps(details)
        db.commit()
    else:
        lines = [line.format_map(fmt) for line in choice["outcome_lines"]]
        headline = choice["headline"]

    reflection = {
        "question": quest["reflection"]["question"],
        "options": [
            {
                "id": opt["id"],
                "label": opt["label"],
                "bot_line": opt["bot_line"],
            }
            for opt in quest["reflection"]["options"]
        ],
    }

    return {
        "quest_id": quest_id,
        "choice_id": choice_id,
        "verdict": choice["verdict"],
        "headline": headline,
        "what_happened": lines,
        "wallet_balance": child.wallet.balance,
        "goal_name": goal_name,
        "goal_saved_amount": goal_saved,
        "goal_target_amount": goal_target,
        "goal_status": goal_status,
        "goal_pct": pct_after,
        "investment_profit_loss": (
            investment_result["profit_loss"] if investment_result else None
        ),
        "reflection": reflection,
    }


def submit_reflection(db: Session, child: Child, quest_id: str, answer_id: str) -> dict:
    """Store the child's reflection answer on a completed quest.

    The answer is appended to the quest activity's details JSON (future
    AI Mentor context) — it is never graded.
    """
    quest = _find_quest(quest_id)

    answer = next(
        (o for o in quest["reflection"]["options"] if o["id"] == answer_id), None
    )
    if not answer:
        raise HTTPException(status_code=400, detail="Invalid answer selected.")

    activities = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "QUEST")
        .order_by(GrowActivity.created_at.desc())
        .all()
    )
    target = None
    for act in activities:
        if act.details:
            d = json.loads(act.details)
            if d.get("quest_id") == quest_id:
                target = (act, d)
                break

    if not target:
        raise HTTPException(status_code=400, detail="Ye quest abhi complete nahi hui.")

    act, d = target
    d["reflection_answer"] = answer_id
    act.details = json.dumps(d)
    db.commit()

    return {
        "quest_id": quest_id,
        "answer_id": answer_id,
        "bot_line": answer["bot_line"],
    }
