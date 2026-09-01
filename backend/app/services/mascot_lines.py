"""Mascot lines — motivational (hype) and roasting (roast) line pools.

The mascot "Paisa Bot" alternates between hype mode (60%) and roast mode (40%).
Lines are context-dependent based on the child's financial state and last action.
"""

import random


# ---------------------------------------------------------------------------
# Motivational (Hype) Lines — 60% chance
# ---------------------------------------------------------------------------

HYPE_DEFAULT_TIPS = [
    "Paisa follows my brother, paisa follows!",
    "Aaj kuch seekhte hain! 💪",
    "Paisay ki duniya mein aao!",
    "Har rupaya ek kahani kehta hai!",
    "Champion log soch ke kharch karte hain!",
    "Seekhna kabhi band mat karo!",
]

HYPE_AFTER_SAVE = [
    "Shabash! Warren Buffet bhi impressed hoga!",
    "Paisa bachaya = Paisa kamaya! 💰",
    "Smart move! Future mein thank you bolna apne aap ko!",
    "Bachana seekh gaya! Ab bara aadmi banega!",
]

HYPE_AFTER_GIVE = [
    "Sadqa jariya activated! Allah bless kare!",
    "Aap ne aaj kisi ki duniya badli! 🤲",
    "Dene wala hamesha zyada ameer hota hai!",
    "Charity champion! Dil bara hai tera!",
]

HYPE_AFTER_BUSINESS_PROFIT = [
    "Munafa! Paisa follow karta hai bhai ko! 📈",
    "CEO vibes! Business ne paisa diya!",
    "Entrepreneur energy! Aise hi chalte raho!",
    "Business king! Warren Buffet 2.0!",
]

HYPE_AFTER_INVESTMENT_PROFIT = [
    "Returns! Sigma grindset on top! 💪",
    "Investment ne kaam kiya! Smart investor!",
    "Paisay se paisa banana — ab aadat daalo!",
]

HYPE_LEVEL_UP = [
    "Level up! Tu toh legend ban raha hai!",
    "Upgrade! Next level pe chal!",
]


# ---------------------------------------------------------------------------
# Roast Lines — 40% chance (context-dependent)
# ---------------------------------------------------------------------------

ROAST_BALANCE_LOW = [
    "Bhai tera balance ro raha hai... thora bacha le! 😭",
    "Itna kam paisa? Bhai tu kya hawa kha ke jeeta hai?",
    "Balance dekh ke dar lag raha hai... save karna seekh!",
]

ROAST_BALANCE_ZERO = [
    "Zero hero! Chal koi baat nahi, seekh gaya na! 😅",
    "Bhai ka balance: zero. Lekin experience: infinite!",
    "Khali jeb, bhara dimaag! Ab seekh gaya na?",
]

ROAST_AFTER_SPEND = [
    "Itne mein toh 2 biryani aur aa jati thin... 🍛",
    "Bro went full YOLO on snacks. Respect. 💀",
    "Kharcha karna aasan hai, bachana mushkil. Life lessons!",
    "Paisa ud gaya... koi baat nahi, agli baar sochna!",
]

ROAST_AFTER_BAD_INVESTMENT = [
    "Loss ho gaya bhai... Warren Buffet thori tha tu? 😂",
    "Investment mein loss! Lekin loss se seekhte hain!",
    "Bhai ne paisa daala aur paisa bhaag gaya! 💨",
    "Risk liya, loss hua. Next time zyada sochna!",
]

ROAST_NO_GOAL = [
    "Goal kahan hai bhai? Bina target ke archer? 🎯",
    "Bina goal ke bhaag raha hai... GPS laga le!",
    "Savings goal set kar! Warna paisay kahan jaenge pata nahi!",
]

ROAST_MULTIPLE_LOSSES = [
    "Tu toh financial disaster movie ka hero hai! 🎬",
    "Lagataar loss! Bhai tu investor hai ya gambler? 😂",
    "Har baar naya loss! Consistency toh hai tujh mein!",
]

ROAST_BIG_SPENDER = [
    "Kharcha machine! Paisay tere dost nahi hain bhai 💸",
    "Itna kharcha? Bhai Ambani ka beta hai kya?",
]


# ---------------------------------------------------------------------------
# Welcome / Greeting Lines
# ---------------------------------------------------------------------------

WELCOME_LINES = [
    "Paisa Bot aapka swagat karta hai! 🤖💰",
    "Assalamu Alaikum! Paiso ki duniya mein aao!",
    "Aaj kya seekhte hain? Paisa? Business? Investment?",
    "Tayyar ho? Apni paiso ki kahani shuru karo!",
]


# ---------------------------------------------------------------------------
# Line Selection Logic
# ---------------------------------------------------------------------------

def get_mascot_line(
    last_action_type: str | None,
    balance: float,
    has_active_goal: bool,
    has_investment_losses: bool,
    total_spent: float,
) -> dict:
    """Select an appropriate mascot line based on context.
    
    Returns: {"line": "...", "mode": "hype" | "roast"}
    """
    # Decide mode: 60% hype, 40% roast
    # But force roast if certain conditions are met
    force_roast = False

    if balance <= 0:
        # Always roast at zero
        return {"line": random.choice(ROAST_BALANCE_ZERO), "mode": "roast"}

    if balance < 50:
        # Likely roast
        if random.random() < 0.7:
            return {"line": random.choice(ROAST_BALANCE_LOW), "mode": "roast"}

    if not has_active_goal and random.random() < 0.3:
        return {"line": random.choice(ROAST_NO_GOAL), "mode": "roast"}

    # Context-dependent
    if last_action_type == "SPEND":
        if random.random() < 0.5 and total_spent >= 200:
            return {"line": random.choice(ROAST_BIG_SPENDER), "mode": "roast"}
        if random.random() < 0.4:
            return {"line": random.choice(ROAST_AFTER_SPEND), "mode": "roast"}

    if last_action_type == "GROW_INVESTMENT":
        if has_investment_losses and random.random() < 0.5:
            return {"line": random.choice(ROAST_AFTER_BAD_INVESTMENT), "mode": "roast"}

    # Random roast chance (40%)
    if random.random() < 0.4:
        # Pick a context-appropriate roast
        roast_pool = ROAST_AFTER_SPEND if last_action_type == "SPEND" else ROAST_BALANCE_LOW
        return {"line": random.choice(roast_pool), "mode": "roast"}

    # Default: hype mode
    if last_action_type == "SAVE":
        return {"line": random.choice(HYPE_AFTER_SAVE), "mode": "hype"}
    elif last_action_type == "GIVE":
        return {"line": random.choice(HYPE_AFTER_GIVE), "mode": "hype"}
    elif last_action_type == "GROW_BUSINESS":
        return {"line": random.choice(HYPE_AFTER_BUSINESS_PROFIT), "mode": "hype"}
    elif last_action_type == "GROW_INVESTMENT":
        if not has_investment_losses:
            return {"line": random.choice(HYPE_AFTER_INVESTMENT_PROFIT), "mode": "hype"}

    # Default hype tip
    return {"line": random.choice(HYPE_DEFAULT_TIPS), "mode": "hype"}


def get_welcome_line() -> dict:
    """Return a welcome/greeting mascot line."""
    return {"line": random.choice(WELCOME_LINES), "mode": "hype"}
