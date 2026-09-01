"""AI Provider — mock implementation for hackathon.

Generates personalized business recommendations based on a child's interests.
Can be replaced with a real AI provider (Groq, etc.) later.

The mock provider uses template-based Roman Urdu pitches that combine the
child's interests with the business template's skill tags.
"""

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
    "tech": ["sticker_shop"],
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


def rank_templates(child_interests: list[str], templates: list[dict]) -> list[dict]:
    """Rank business templates by interest match and add personalized pitches.

    Returns the same templates with added 'pitch' and 'match_score' fields,
    sorted by match score (best matches first).
    """
    scored = []
    for t in templates:
        score = score_template(child_interests, t["id"])
        pitch = generate_pitch(child_interests, t["id"], t["name"])
        scored.append({
            **t,
            "match_score": score,
            "pitch": pitch,
        })

    # Sort by match_score descending, then by name for stability
    scored.sort(key=lambda x: (-x["match_score"], x["name"]))
    return scored
