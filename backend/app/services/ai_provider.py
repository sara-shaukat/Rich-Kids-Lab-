"""AI Provider — business recommendations with Groq integration.

Generates personalized business recommendations based on a child's interests.
Uses Groq API when available, falls back to mock templates.
"""

import json
import os
import random

# Interest options the child can pick from (child-friendly categories)
INTEREST_OPTIONS = [
    {"id": "art", "label": "Art & Drawing", "icon": "🎨"},
    {"id": "food", "label": "Food & Cooking", "icon": "🍕"},
    {"id": "tech", "label": "Technology", "icon": "💻"},
    {"id": "teaching", "label": "Teaching Others", "icon": "📚"},
    {"id": "design", "label": "Design & Crafts", "icon": "✂️"},
    {"id": "helping", "label": "Helping People", "icon": "🤝"},
]

# Maps child interest → business template ids (for ranking)
INTEREST_BUSINESS_MAP = {
    "art": ["bookmarks", "art_cards", "sticker_shop"],
    "food": ["lemonade"],
    "tech": ["sticker_shop", "phone_accessories"],
    "teaching": ["homework"],
    "design": ["bookmarks", "art_cards", "sticker_shop"],
    "helping": ["homework", "lemonade"],
}

# Personalized pitch templates (Roman Urdu)
# {interest} and {business_name} are filled in dynamically.
PITCH_TEMPLATES = {
    "art": [
        "Aapko art pasand hai! {business_name} try karein — aap apni creativity se paisay kama sakte ho!",
        "Drawing aapka passion hai? {business_name} aapke liye perfect business hai!",
    ],
    "food": [
        "Khana banana pasand hai? {business_name} mein aap mazay ke saath paisay bhi kamao!",
        "Food lover ho? {business_name} try karein — tasty business hai!",
    ],
    "tech": [
        "Technology pasand hai? {business_name} mein aap apni skills use kar sakte ho!",
        "Tech-savvy bachay ke liye {business_name} ek acha start hai!",
    ],
    "teaching": [
        "Doosron ko parhana pasand hai? {business_name} se aap paisay bhi kamao aur seekhao bhi!",
        "Teaching ek noble kaam hai — {business_name} try karein!",
    ],
    "design": [
        "Design karna pasand hai? {business_name} mein aap apni creativity dikha sakte ho!",
        "Creative mind ke liye {business_name} perfect hai!",
    ],
    "helping": [
        "Madad karna pasand hai? {business_name} se aap doosron ki madad bhi karo aur paisay bhi kamao!",
        "Helping others is the best business — {business_name} try karein!",
    ],
}

# Default pitch when no interests match
DEFAULT_PITCHES = [
    "{business_name} ek acha business hai — shuru karein aur dekhein kya hota hai!",
    "{business_name} mein kam invest mein zyada munafa ho sakta hai!",
    "Naye business owner banein — {business_name} try karein!",
]


def get_matching_interests(child_interests: list[str], template_skills: list[str]) -> list[str]:
    """Find which child interests match a business template's skills."""
    matches = []
    for interest in child_interests:
        mapped_businesses = INTEREST_BUSINESS_MAP.get(interest, [])
        # This is checked at a higher level; here we just return the interest
        if interest in child_interests:
            matches.append(interest)
    return matches


def generate_pitch(child_interests: list[str], template_id: str, template_name: str) -> str:
    """Generate a personalized pitch for a business template.

    Tries to match child interests with the template.
    Falls back to a generic pitch if no match.
    """
    # Find which interests map to this template
    matching_interests = []
    for interest in child_interests:
        mapped_ids = INTEREST_BUSINESS_MAP.get(interest, [])
        if template_id in mapped_ids:
            matching_interests.append(interest)

    if matching_interests:
        # Use a pitch from the best matching interest
        interest = random.choice(matching_interests)
        pitch_templates = PITCH_TEMPLATES.get(interest, DEFAULT_PITCHES)
    else:
        pitch_templates = DEFAULT_PITCHES

    pitch = random.choice(pitch_templates)
    return pitch.format(business_name=template_name)


def score_template(child_interests: list[str], template_id: str) -> int:
    """Score a template based on how well it matches the child's interests.

    Higher score = better match. Returns 0 if no match.
    """
    score = 0
    for interest in child_interests:
        mapped_ids = INTEREST_BUSINESS_MAP.get(interest, [])
        if template_id in mapped_ids:
            score += 1
    return score


def rank_templates(child_interests: list[str], templates: list[dict], child_context: dict = None) -> list[dict]:
    """Rank business templates by interest match and add personalized pitches.

    Uses Groq AI when available, falls back to mock templates.

    Args:
        child_interests: List of interest IDs the child selected
        templates: List of business template dicts
        child_context: Optional dict with child's balance, previous businesses, etc.

    Returns the same templates with added 'pitch' and 'match_score' fields,
    sorted by match score (best matches first).
    """
    # Try Groq AI first
    ai_pitches = None
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key and child_context:
        ai_pitches = _generate_ai_pitches(child_interests, templates, child_context, groq_key)

    scored = []
    for t in templates:
        score = score_template(child_interests, t["id"])
        # Use AI pitch if available, otherwise fall back to mock
        if ai_pitches and t["id"] in ai_pitches:
            pitch = ai_pitches[t["id"]]
        else:
            pitch = generate_pitch(child_interests, t["id"], t["name"])
        scored.append({
            **t,
            "match_score": score,
            "pitch": pitch,
        })

    # Sort by match_score descending, then by name for stability
    scored.sort(key=lambda x: (-x["match_score"], x["name"]))
    return scored


def generate_ai_business_ideas(
    child_interests: list[str],
    balance: float,
    groq_key: str,
) -> list[dict]:
    """Generate completely new AI-powered business ideas.

    Args:
        child_interests: List of interest IDs the child selected
        balance: Child's current wallet balance
        groq_key: Groq API key

    Returns list of business idea dicts, or empty list on failure.
    """
    try:
        import httpx

        # Build interest labels
        interest_labels = []
        for interest_id in child_interests:
            for opt in INTEREST_OPTIONS:
                if opt["id"] == interest_id:
                    interest_labels.append(opt["label"])
                    break

        prompt = f"""You are Paisa Bot, a creative business idea generator for Pakistani children aged 9-13.
The child is interested in: {', '.join(interest_labels) if interest_labels else 'general entrepreneurship'}.
Their current budget is Rs. {balance}.

Generate 4 UNIQUE, CREATIVE micro-business ideas that:
1. Are age-appropriate and safe for children
2. Can be started with Rs. 50 to Rs. {min(int(balance * 0.6), 500)} budget
3. Relate to the child's interests when possible
4. Teach real financial concepts (cost, revenue, profit, LOSS, skills)
5. Are NOT the standard lemonade stand or bookmarks (be creative!)

IMPORTANT — RISK EDUCATION:
- At least 1 (ideally 2) of the 4 businesses MUST have a NEGATIVE expected_profit_min (e.g., -60 or -100).
  This teaches children that businesses can LOSE money, which is a critical real-world lesson.
- Risky businesses should have a higher expected_profit_max to compensate (risk vs reward).
- Describe risky businesses honestly in the pitch: mention they are risky but potentially rewarding.

For each business idea, provide:
- id: unique snake_case identifier (e.g., "custom_sticker_pack")
- name: catchy, kid-friendly name in English or Roman Urdu (2-4 words)
- description: 1-2 sentence description in Roman Urdu explaining what the business does
- cost: startup cost in Rs. (integer, within budget)
- expected_profit_min: minimum expected profit in Rs. (NEGATIVE integer for risky businesses)
- expected_profit_max: maximum expected profit in Rs. (integer, about 2-3x the absolute value of min for risky ones)
- skills: list of 2-3 skills the child will learn (e.g., ["creativity", "marketing", "planning"])
- pitch: 1 sentence personalized pitch in Roman Urdu mentioning the child's interests

Respond in EXACTLY this JSON format (no markdown, no code blocks):
[
  {{
    "id": "business_id_1",
    "name": "Business Name",
    "description": "Description in Roman Urdu",
    "cost": 150,
    "expected_profit_min": -60,
    "expected_profit_max": 300,
    "skills": ["skill1", "skill2"],
    "pitch": "Personalized pitch text"
  }}
]
"""

        with httpx.Client(timeout=15) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "groq/compound",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.9,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

        # Parse JSON response
        ideas = json.loads(content)
        if not isinstance(ideas, list):
            return []

        # Validate and filter
        valid_ideas = []
        for idea in ideas:
            if not isinstance(idea, dict):
                continue
            required = {"id", "name", "description", "cost", "expected_profit_min", "expected_profit_max", "skills", "pitch"}
            if not required.issubset(idea.keys()):
                continue
            # Validate types
            if not isinstance(idea["id"], str) or not isinstance(idea["name"], str):
                continue
            if not isinstance(idea["cost"], (int, float)) or idea["cost"] <= 0:
                continue
            if not isinstance(idea["expected_profit_min"], (int, float)):
                continue
            if not isinstance(idea["expected_profit_max"], (int, float)):
                continue
            if not isinstance(idea["skills"], list) or len(idea["skills"]) == 0:
                continue
            # Ensure cost is within budget
            if idea["cost"] > balance:
                continue
            valid_ideas.append({
                "id": idea["id"],
                "name": idea["name"],
                "description": idea["description"],
                "cost": int(idea["cost"]),
                "expected_profit_min": int(idea["expected_profit_min"]),
                "expected_profit_max": int(idea["expected_profit_max"]),
                "skills": idea["skills"],
                "pitch": idea["pitch"],
                "min_budget": int(idea["cost"]),
            })

        # --- SERVER-SIDE RISK INJECTION ---
        # If Groq gave us all-positive businesses, force risk on 1-2 of them.
        # This ensures the child ALWAYS sees at least one risky option.
        has_risky = any(i["expected_profit_min"] < 0 for i in valid_ideas)
        if not has_risky and len(valid_ideas) >= 2:
            import random
            # Pick 1-2 random businesses to make risky
            risky_count = min(2, len(valid_ideas))
            risky_indices = random.sample(range(len(valid_ideas)), risky_count)
            for idx in risky_indices:
                cost = valid_ideas[idx]["cost"]
                # Set loss range proportional to cost (20-60% of cost as max loss)
                loss_amount = int(cost * random.uniform(0.2, 0.6))
                valid_ideas[idx]["expected_profit_min"] = -loss_amount
                # Ensure max is at least 2x the loss to make it interesting
                valid_ideas[idx]["expected_profit_max"] = max(
                    valid_ideas[idx]["expected_profit_max"],
                    loss_amount * 3
                )

        return valid_ideas

    except Exception:
        # Any failure → return empty list
        return []


def _generate_ai_pitches(
    child_interests: list[str],
    templates: list[dict],
    child_context: dict,
    groq_key: str,
) -> dict[str, str]:
    """Generate personalized pitches using Groq AI.

    Returns a dict mapping template_id → pitch text.
    Falls back to empty dict on any failure.
    """
    try:
        import httpx

        # Build interest labels
        interest_labels = []
        for interest_id in child_interests:
            for opt in INTEREST_OPTIONS:
                if opt["id"] == interest_id:
                    interest_labels.append(opt["label"])
                    break

        # Build business summaries
        business_summaries = []
        for t in templates:
            business_summaries.append({
                "id": t["id"],
                "name": t["name"],
                "cost": t["cost"],
                "expected_profit_min": t["expected_profit_min"],
                "expected_profit_max": t["expected_profit_max"],
                "skills": t["skills"],
            })

        prompt = f"""You are Paisa Bot, a friendly financial mentor for Pakistani children aged 9-13.
The child is interested in: {', '.join(interest_labels) if interest_labels else 'general business ideas'}.
Their current balance is Rs. {child_context.get('balance', 0)}.

Generate a SHORT, encouraging pitch (1-2 sentences max) in Roman Urdu for each business below.
Make each pitch personalized to the child's interests and budget.
Use simple language and familiar English terms (profit, investment, skills) where natural.

Businesses:
{json.dumps(business_summaries, indent=2)}

Respond in EXACTLY this JSON format (no markdown, no code blocks):
{{
  "business_id_1": "Pitch text here",
  "business_id_2": "Pitch text here"
}}
"""

        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}"},
                json={
                    "model": "groq/compound",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.8,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

        # Parse JSON response
        pitches = json.loads(content)
        if not isinstance(pitches, dict):
            return {}

        # Validate and filter
        valid_pitches = {}
        for template in templates:
            if template["id"] in pitches and isinstance(pitches[template["id"]], str):
                valid_pitches[template["id"]] = pitches[template["id"]]

        return valid_pitches

    except Exception:
        # Any failure (network, parsing, API error) → fall back to mock
        return {}
