"""Report card service — compute financial skill grades from real behavior.

Produces a Money Report Card with grades across 5 categories.
Optionally uses ONE Groq API call for a personalized commentary paragraph.
Template-based fallback ensures the demo works without any API credits.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Child, Transaction, GrowActivity, Goal


_GRADE_MAP = [
    (90, "A"), (75, "B"), (55, "C"), (35, "D"), (0, "F"),
]


def _to_grade(score: float) -> str:
    for threshold, grade in _GRADE_MAP:
        if score >= threshold:
            return grade
    return "F"


def _grade_point(grade: str) -> float:
    return {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}.get(grade, 0.0)


def compute_report_card(db: Session, child: Child) -> dict:
    """Compute a child's Money Report Card — grades + stats + optional AI commentary."""

    # ------------------------------------------------------------------
    # Fetch all transactions
    # ------------------------------------------------------------------
    transactions = (
        db.query(Transaction)
        .filter(Transaction.child_id == child.id)
        .all()
    )
    save_txns = [t for t in transactions if t.type == "SAVE"]
    spend_txns = [t for t in transactions if t.type == "SPEND"]
    give_txns = [t for t in transactions if t.type == "GIVE"]
    earn_txns = [t for t in transactions if t.type == "EARN"]

    total_saved = sum(float(t.amount) for t in save_txns)
    total_spent = sum(float(t.amount) for t in spend_txns)
    total_given = sum(float(t.amount) for t in give_txns)
    total_earned = sum(float(t.amount) for t in earn_txns)
    txn_count = len(transactions)

    # ------------------------------------------------------------------
    # Fetch GROW activity
    # ------------------------------------------------------------------
    businesses = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "BUSINESS")
        .all()
    )
    skills = (
        db.query(GrowActivity)
        .filter(GrowActivity.child_id == child.id, GrowActivity.type == "SKILL")
        .count()
    )

    business_ids = set()
    total_profit = 0.0
    wins = 0
    losses = 0
    for b in businesses:
        import json
        try:
            details = json.loads(b.details) if b.details else {}
            profit = float(details.get("actual_profit", 0))
            total_profit += profit
            business_ids.add(details.get("template_id", "unknown"))
            if profit >= 0:
                wins += 1
            else:
                losses += 1
        except (json.JSONDecodeError, ValueError):
            pass

    # ------------------------------------------------------------------
    # 1. SAVING SKILLS
    # ------------------------------------------------------------------
    if txn_count > 0:
        save_ratio = len(save_txns) / txn_count
        # Bonus: saved more than spent
        save_vs_spend_bonus = min(total_saved / max(total_spent, 1), 2.0) / 2.0  # 0-1
        saving_score = int(min(save_ratio * 60 + save_vs_spend_bonus * 40, 100))
    else:
        saving_score = 0

    # ------------------------------------------------------------------
    # 2. SPENDING WISDOM
    #    Reward: fewer total spends, lower avg spend amount
    # ------------------------------------------------------------------
    if spend_txns:
        avg_spend = total_spent / len(spend_txns)
        # Lower avg spend = wiser.  Max score if avg < 50, drops after 150
        spend_score = int(max(0, min(100, 100 - (avg_spend - 30) * 0.6)))
    else:
        spend_score = 50  # Neutral — no data yet

    # ------------------------------------------------------------------
    # 3. BUSINESS SENSE
    #    Reward: diversity + profit + risk-taking (even losses!)
    # ------------------------------------------------------------------
    diversity_bonus = min(len(business_ids) * 15, 30)  # Up to 30 for variety
    profit_score = min(int(max(total_profit, 0) / 5), 40)  # Up to 40 for profit
    experience_bonus = min(len(businesses) * 8, 20)  # Up to 20 for attempts
    risk_bonus = min(losses * 5, 10)  # Reward risk-taking
    business_score = min(diversity_bonus + profit_score + experience_bonus + risk_bonus, 100)

    # ------------------------------------------------------------------
    # 4. GIVING SPIRIT
    # ------------------------------------------------------------------
    if txn_count > 0 and total_given > 0:
        give_ratio = len(give_txns) / txn_count
        give_amount_bonus = min(total_given / 100, 1.0)  # Up to 1 for Rs.100+ given
        giving_score = int(min(give_ratio * 50 + give_amount_bonus * 50, 100))
    else:
        giving_score = 0

    # ------------------------------------------------------------------
    # 5. MONEY GROWTH
    #    Reward: earned money + skills learned + businesses tried
    # ------------------------------------------------------------------
    earn_score = min(int(total_earned / 5), 40)  # Up to 40
    skill_score = min(skills * 12, 30)  # Up to 30
    activity_score = min(len(businesses) * 10, 30)  # Up to 30
    growth_score = min(earn_score + skill_score + activity_score, 100)

    # ------------------------------------------------------------------
    # Build report card
    # ------------------------------------------------------------------
    categories = [
        {
            "id": "saving",
            "name": "Saving Skills",
            "icon": "🐷",
            "score": saving_score,
            "grade": _to_grade(saving_score),
            "detail": f"Rs. {int(total_saved)} saved across {len(save_txns)} saves",
        },
        {
            "id": "spending",
            "name": "Spending Wisdom",
            "icon": "🧠",
            "score": spend_score,
            "grade": _to_grade(spend_score),
            "detail": f"{len(spend_txns)} purchases, avg Rs. {int(total_spent / max(len(spend_txns), 1))}",
        },
        {
            "id": "business",
            "name": "Business Sense",
            "icon": "🚀",
            "score": business_score,
            "grade": _to_grade(business_score),
            "detail": f"{len(businesses)} businesses ({wins} wins, {losses} losses), Rs. {int(total_profit)} profit",
        },
        {
            "id": "giving",
            "name": "Giving Spirit",
            "icon": "💛",
            "score": giving_score,
            "grade": _to_grade(giving_score),
            "detail": f"Rs. {int(total_given)} donated across {len(give_txns)} gifts",
        },
        {
            "id": "growth",
            "name": "Money Growth",
            "icon": "📈",
            "score": growth_score,
            "grade": _to_grade(growth_score),
            "detail": f"Rs. {int(total_earned)} earned, {skills} skills learned",
        },
    ]

    gpa_values = [_grade_point(c["grade"]) for c in categories]
    overall_gpa = round(sum(gpa_values) / len(gpa_values), 1) if gpa_values else 0.0

    return {
        "categories": categories,
        "overall_gpa": overall_gpa,
        "stats": {
            "total_transactions": txn_count,
            "total_saved": total_saved,
            "total_spent": total_spent,
            "total_given": total_given,
            "total_earned": total_earned,
            "businesses_tried": len(businesses),
            "business_types": len(business_ids),
            "skills_learned": skills,
            "total_profit": total_profit,
            "wins": wins,
            "losses": losses,
        },
        "commentary": "",
        "ai_generated": False,
    }


# ---------------------------------------------------------------------------
# AI Commentary — ONE Groq call, falls back to template
# ---------------------------------------------------------------------------

_FALLBACK_COMMENTARY = (
    "Bahut acha kaam! Aapne apni money journey mein bahut kuch seekha. "
    "Saving aur business dono mein try kiya — ye smart approach hai. "
    "Aage bhi seekhte raho aur smart decisions lete raho!"
)

_REPORT_CARD_SYSTEM = (
    "You are Paisa Bot writing a brief comment on a child's financial report card. "
    "Write EXACTLY 2-3 short sentences in simple Roman Urdu. "
    "Be specific about the child's strongest and weakest area. "
    "Be warm, encouraging, and age-appropriate (child is 9-13 years old). "
    "Do NOT use markdown, bullet points, or line breaks. "
    "Do NOT add Urdu script or any separator. "
    "Just one plain paragraph."
)


def generate_commentary(report_data: dict) -> str:
    """Generate ONE short AI commentary paragraph. Falls back to template on any error."""
    import os
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return _FALLBACK_COMMENTARY

    try:
        import httpx

        categories_summary = ", ".join(
            f"{c['name']}:{c['grade']}" for c in report_data["categories"]
        )
        user_msg = (
            f"Child report: {categories_summary}. "
            f"GPA: {report_data['overall_gpa']}. "
            f"Stats: {report_data['stats']['businesses_tried']} businesses, "
            f"Rs.{int(report_data['stats']['total_saved'])} saved, "
            f"Rs.{int(report_data['stats']['total_profit'])} business profit."
        )

        payload = {
            "model": "groq/compound",
            "messages": [
                {"role": "system", "content": _REPORT_CARD_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 100,
            "temperature": 0.7,
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        commentary = data["choices"][0]["message"]["content"].strip()
        # Strip any accidental markdown or separators
        commentary = commentary.replace("###", "").replace("**", "").strip()
        return commentary if commentary else _FALLBACK_COMMENTARY

    except Exception:
        return _FALLBACK_COMMENTARY
