"""Grow service — business, investment, and skill logic.

All GROW wallet mutations go through this module so that validation
and financial logic are enforced in exactly one place.
"""

import json
import random
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Child, Wallet, Transaction, GrowActivity
from app.services.wallet_service import validate_amount


# ---------------------------------------------------------------------------
# Predefined business templates (from SPEC.md §11.1)
# ---------------------------------------------------------------------------

BUSINESS_TEMPLATES = [
    {
        "id": "bookmarks",
        "name": "Handmade Bookmarks",
        "min_budget": 100,
        "cost": 80,
        "expected_profit_min": 80,
        "expected_profit_max": 160,
        "skills": ["creativity", "selling"],
        "description": "Aap handmade bookmarks bana kar bech sakte ho!",
    },
    {
        "id": "lemonade",
        "name": "Lemonade Stand",
        "min_budget": 150,
        "cost": 120,
        "expected_profit_min": 150,
        "expected_profit_max": 310,
        "skills": ["planning", "customer service"],
        "description": "Thanda lemonade bechna ek classic business hai!",
    },
    {
        "id": "homework",
        "name": "Homework Helper",
        "min_budget": 50,
        "cost": 30,
        "expected_profit_min": 80,
        "expected_profit_max": 160,
        "skills": ["teaching", "patience"],
        "description": "Doosron ko parhana bhi ek business hai!",
    },
    {
        "id": "art_cards",
        "name": "Art Cards",
        "min_budget": 200,
        "cost": 150,
        "expected_profit_min": 170,
        "expected_profit_max": 330,
        "skills": ["art", "marketing"],
        "description": "Apni art se greeting cards banao!",
    },
    {
        "id": "sticker_shop",
        "name": "Sticker Shop",
        "min_budget": 250,
        "cost": 200,
        "expected_profit_min": 200,
        "expected_profit_max": 400,
        "skills": ["design", "selling"],
        "description": "Cool stickers design karo aur becho!",
    },
]

# ---------------------------------------------------------------------------
# Predefined skill cards (from SPEC.md §11.3)
# ---------------------------------------------------------------------------

SKILL_CARDS = [
    {
        "id": "ai_prompting",
        "name": "AI Prompt Engineering",
        "icon": "\U0001f916",
        "why": "AI ko sahi sawal poochna ek skill hai — achay prompts likhna seekho!",
        "steps": "Simple sawalon se shuru karo -> Specific hona seekho -> Clear instructions do -> Context samjho",
        "practice_question": "Agar tum AI se koi sawal pooch sakte, to kya poochte?",
        "earning_potential": "AI tools use karna future mein valuable skill ho sakti hai — content creation, research, aur problem-solving mein.",
        "category": "tech",
        "discover": "AI ko sahi sawal poochna ek skill hai! Achay prompts likhna seekho to AI se bohat kuch kar sakte ho. Jitna specific tumhara sawal, utna useful jawab milega.",
        "challenge": {
            "question": "Tum AI se ek bachon ke liye educational story likhwana chahte ho jo Pakistan mein set ho. Kon sa prompt best result dega?",
            "options": [
                {"id": "a", "text": "Ek story likho Pakistan ke baare mein", "correct": False},
                {"id": "b", "text": "Ek 500-word adventure story likho jo Lahore mein set hai, main character ek 12 saal ka bacha hai jo purani haveli explore karta hai, simple Urdu-English mix mein", "correct": True},
                {"id": "c", "text": "Best Pakistani story ever likho for kids", "correct": False},
                {"id": "d", "text": "Story about Pakistan, kids, adventure, good story", "correct": False},
            ],
            "explanation_correct": "Sahi jawab! Specific prompt mein audience, setting, character, length aur style — sab kuch clear hai. AI ko jitni detail doge, utna acha result milega.",
            "explanation_wrong": "Hmm, ye prompt bohat vague hai. Specific details dena zaroori hai — jaise audience kaun hai, kitni lambi story chahiye, kahan set hai.",
        },
        "connect_text": "Future mein AI tools use karna ek valuable skill ho sakti hai. Jitna specific prompt, utna useful result. Ye skill content creation, research, aur problem-solving mein kaam aa sakti hai.",
        "linked_business_ids": ["homework"],
    },
    {
        "id": "coding",
        "name": "Coding",
        "icon": "\U0001f4bb",
        "why": "Coding seekho, apps banao, future ready ho!",
        "steps": "Scratch se shuru karo -> Python seekho -> Chhoti apps banao -> Logic building practice karo",
        "practice_question": "Agar aap ek app banao jo logon ki madad kare, to uska naam kya hoga?",
        "earning_potential": "Developers apps banate hain jo logon ki problems solve karti hain — coding logic aur problem-solving dono seekhata hai.",
        "category": "tech",
        "discover": "Coding seekho = apps banana seekho! Computer ko instructions dena ek superpower hai. Har app, website aur game ke peeche coding hoti hai.",
        "challenge": {
            "question": "Ek app banani hai jo user se naam aur age pooche, check kare age 13+ hai, aur personalized greeting show kare. Steps ka sahi order kya hai?",
            "options": [
                {"id": "a", "text": "Ask name -> Ask age -> Display greeting -> Check age", "correct": False},
                {"id": "b", "text": "Ask name -> Ask age -> If age >= 13 show greeting else show error", "correct": True},
                {"id": "c", "text": "Check age -> Ask name -> Ask age again -> Display greeting", "correct": False},
                {"id": "d", "text": "Display greeting -> Ask name -> Ask age -> Check age", "correct": False},
            ],
            "explanation_correct": "Bilkul sahi! Pehle input lo, phir validate karo, phir result dikhao. Ye pattern — Input, Process, Output — coding ki basic building block hai.",
            "explanation_wrong": "Socho: agar greeting validation se pehle dikha diya to kya hoga? Sahi order hai: pehle input lo, phir check karo, phir result dikhao.",
        },
        "connect_text": "Developers apps banate hain jo logon ki problems solve karti hain. Coding logic aur problem-solving dono seekhata hai — ye skills har field mein useful hain.",
        "linked_business_ids": ["sticker_shop"],
    },
    {
        "id": "writing",
        "name": "Writing",
        "icon": "\u270d\ufe0f",
        "why": "Acha likhna ek superpower hai!",
        "steps": "Roz ek paragraph likho -> Different styles try karo -> Feedback lo -> Improve karo",
        "practice_question": "Agar aap ek kahani likho, to kis baare mein likhoge?",
        "earning_potential": "Content writers, bloggers, aur storytellers apni writing skill se kaam karte hain. Achay words products ko bhi behtar banate hain.",
        "category": "creative",
        "discover": "Acha likhna ek superpower hai! Words se logon ko inspire, inform aur entertain kar sakte ho. Har product, website aur ad ke peeche acha likha hota hai.",
        "optional_practice": "Ek handmade bookmark ke liye 2-line description likho — apni creativity dikhao!",
        "challenge": {
            "question": "Ek customer tumhari handmade bookmark dekhta hai. Kon si tagline customer ko sab se zyada attract karegi?",
            "options": [
                {"id": "a", "text": "Ye bookmark hai. Khareed lo.", "correct": False},
                {"id": "b", "text": "Apni har kitaab ko ek kahani banayein — ye bookmark sirf page nahi, imagination hold karta hai.", "correct": True},
                {"id": "c", "text": "Bookmark sasta hai, le lo.", "correct": False},
                {"id": "d", "text": "Best bookmark in the world, number 1 bookmark.", "correct": False},
            ],
            "explanation_correct": "Zabardast! Achay words emotions jagate hain aur value dikhate hain. 'Imagination hold karta hai' — ye line customer ko sochnay par majboor karti hai.",
            "explanation_wrong": "Socho: customer kya chahta hai? Sirf 'sasta' ya 'best' bolna kafi nahi. Achay words product ki value batate hain aur emotions connect karte hain.",
        },
        "connect_text": "Content writers, bloggers, aur storytellers apni writing skill se kaam karte hain. Achay words products ko bhi behtar banate hain — ye skill marketing mein bhi useful hai.",
        "linked_business_ids": ["bookmarks"],
    },
    {
        "id": "photography",
        "name": "Photography",
        "icon": "\U0001f4f8",
        "why": "Photos se stories batao aur earn karo!",
        "steps": "Phone camera se practice karo -> Light samjho -> Angles try karo -> Composition seekho",
        "practice_question": "Agar aap photo lete ho, to kis cheez ki photo loge?",
        "earning_potential": "Photography skill events, products, aur social media ke liye useful ho sakti hai. Achi product photos selling mein farq karti hain.",
        "category": "art",
        "discover": "Photo lena sirf click karna nahi hai — light, angle, aur composition samajhna hai! Achi photo kisi bhi product ya moment ko special bana sakti hai.",
        "challenge": {
            "question": "Ek handmade bookmark ki product photo leni hai jo online sell karni hai. Tumhare paas ek phone camera, ek table, aur natural window light hai. Kon sa setup best result dega?",
            "options": [
                {"id": "a", "text": "Flash on karo, table pe seedha upar se photo lo, busy background rakho taake colorful lage", "correct": False},
                {"id": "b", "text": "Window ke paas table rakho, clean white cloth bichhao, bookmark ko center mein rakho, side angle se photo lo, natural light use karo", "correct": True},
                {"id": "c", "text": "Raat ko tube light ke neeche photo lo, haath mein phone pakro, close-up zoom use karo", "correct": False},
                {"id": "d", "text": "Multiple bookmarks scatter karo table pe, flash + filter lagao, dark room mein photo lo", "correct": False},
            ],
            "explanation_correct": "Perfect! Natural light + clean background + proper composition = professional product photo. Ye setup simple hai lekin result bohat acha deta hai.",
            "explanation_wrong": "Product photography mein teen cheezen important hain: clean background (taake product stand out kare), natural light (flash harsh hota hai), aur proper angle.",
        },
        "connect_text": "Photography skill events, products, aur social media ke liye useful ho sakti hai. Online selling mein achi product photos bohat farq karti hain.",
        "linked_business_ids": ["art_cards"],
    },
    {
        "id": "video_editing",
        "name": "Video Editing",
        "icon": "\U0001f3ac",
        "why": "Videos banana seekho — bohot demand hai!",
        "steps": "Free editing apps try karo -> Basic cuts seekho -> Transitions add karo -> Storytelling practice karo",
        "practice_question": "Agar aap ek video banao, to kis topic par banoge?",
        "earning_potential": "Video editors social media, events, aur content creation mein kaam karte hain. Planning aur storytelling dono video editing mein important hain.",
        "category": "tech",
        "discover": "Videos banana aur edit karna ek in-demand skill hai! Short videos ki demand bohat zyada hai — lekin achi video banane ke liye planning aur storytelling dono chahiye.",
        "challenge": {
            "question": "Ek 60-second tutorial video banani hai jo dikhaye ke handmade bookmark kaise banate hain. Pehle se last tak, production steps ka sahi order kya hai?",
            "options": [
                {"id": "a", "text": "Edit clips -> Record footage -> Plan shots -> Upload", "correct": False},
                {"id": "b", "text": "Plan shots + script -> Record footage step by step -> Select best clips -> Edit + add text + add music -> Export", "correct": True},
                {"id": "c", "text": "Upload to social media -> Record while uploading -> Edit later", "correct": False},
                {"id": "d", "text": "Record everything randomly -> Pick one clip -> Upload without editing", "correct": False},
            ],
            "explanation_correct": "Sahi! Pehle plan karo, phir record karo, phir edit karo. Ye 'Pre-production -> Production -> Post-production' workflow hai — har professional video isi process se guzarti hai.",
            "explanation_wrong": "Video production ka order hai: pehle plan karo (script + shots), phir record karo, phir best clips select karo, phir edit karo. Bina planning ke recording karna time waste hai.",
        },
        "connect_text": "Video editors social media, events, aur content creation mein kaam karte hain. Planning aur storytelling dono video editing mein important hain — ye skills har creative field mein kaam aati hain.",
        "linked_business_ids": ["sticker_shop"],
    },
    {
        "id": "crafts",
        "name": "Crafts",
        "icon": "\u2702\ufe0f",
        "why": "Haath se banana ek valuable skill hai!",
        "steps": "Simple projects se shuru karo -> Har hafte kuch naya banao -> Materials samjho -> Selling ki practice karo",
        "practice_question": "Aap kya craft banana chahte ho?",
        "earning_potential": "Crafters handmade items sell karte hain — online aur markets mein. Pricing samajhna bhi ek important skill hai.",
        "category": "creative",
        "discover": "Haath se banana ek valuable skill hai! Handmade products ki bohat demand hai — lekin sirf banana kafi nahi, pricing aur selling bhi seekhna zaroori hai.",
        "challenge": {
            "question": "Tum 10 handmade bookmarks bana kar school mein sell karna chahte ho. Har bookmark ki material cost Rs. 5 hai. Tum chahte ho ke profit bhi ho aur price bhi reasonable rahe. Kon sa plan best hai?",
            "options": [
                {"id": "a", "text": "Rs. 5 mein becho — cost recovery ho jayegi, profit zero", "correct": False},
                {"id": "b", "text": "Rs. 25 mein becho — materials Rs. 50 total, revenue Rs. 250, profit Rs. 200, ek sign board bhi banao jo designs dikhaye", "correct": True},
                {"id": "c", "text": "Rs. 100 mein becho — maximum profit!", "correct": False},
                {"id": "d", "text": "Free mein baant do — log khush honge", "correct": False},
            ],
            "explanation_correct": "Smart thinking! Rs. 25 reasonable price hai school kids ke liye, profit bhi hai, aur sign board se marketing bhi ho rahi hai. Business mein pricing aur presentation dono important hain.",
            "explanation_wrong": "Business mein sirf banana kafi nahi — sahi price rakhna bhi zaroori hai. Bohat sasta = no profit. Bohat mehenga = no customers. Reasonable price + marketing = smart business.",
        },
        "connect_text": "Crafters handmade items sell karte hain — online aur markets mein. Pricing samajhna bhi ek important skill hai — cost, profit, aur customer budget teeno ko balance karna seekho.",
        "linked_business_ids": ["bookmarks", "art_cards"],
    },
]

# ---------------------------------------------------------------------------
# Investment scenarios (from SPEC.md §11.2)
# ---------------------------------------------------------------------------

INVESTMENT_SCENARIOS = {
    "low": {
        "name": "Savings Fund",
        "icon": "🌱",
        "description": "Safe-ish option. Chhota gain ya chhota loss ho sakta hai.",
        "min_return": -3,
        "max_return": 8,
        "message": "Kam risk, kam reward. Ye safe choice hai.",
    },
    "medium": {
        "name": "Growing Company",
        "icon": "🚀",
        "description": "Medium risk. Moderate gain ya moderate loss ho sakta hai.",
        "min_return": -15,
        "max_return": 25,
        "message": "Medium risk — kabhi profit, kabhi thora loss.",
    },
    "high": {
        "name": "New Startup",
        "icon": "⚡",
        "description": "High risk! Bara gain ya bara loss — kuch bhi ho sakta hai!",
        "min_return": -50,
        "max_return": 60,
        "message": "High risk — bada profit ho sakta hai, lekin loss bhi ho sakta hai!",
    },
}


def get_templates_for_budget(balance: Decimal) -> list[dict]:
    """Return business templates where min_budget <= balance."""
    return [t for t in BUSINESS_TEMPLATES if Decimal(str(t["min_budget"])) <= balance]


def start_business(db: Session, child: Child, template_id: str) -> dict:
    """Start a business simulation with randomized profit.

    1. Validate template exists and child can afford it
    2. Randomize actual profit within expected_profit_min..expected_profit_max
    3. Deduct cost from wallet, add (cost + actual_profit) as revenue
    4. Record GROW activity and GROW transaction
    """
    template = None
    for t in BUSINESS_TEMPLATES:
        if t["id"] == template_id:
            template = t
            break

    if not template:
        raise HTTPException(status_code=400, detail="Invalid business idea selected.")

    cost = Decimal(str(template["cost"]))
    p_min = Decimal(str(template["expected_profit_min"]))
    p_max = Decimal(str(template["expected_profit_max"]))

    wallet: Wallet = child.wallet
    if cost > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Aapke paas sirf Rs. {wallet.balance} hain. Rs. {cost} chahiye is business ke liye.",
        )

    # Randomize actual profit within the expected range
    actual_profit = Decimal(str(random.randint(int(p_min), int(p_max))))
    actual_revenue = cost + actual_profit

    # Deduct cost, add revenue
    wallet.balance -= cost
    wallet.balance += actual_revenue

    # Record GROW transaction (amount = actual profit)
    txn = Transaction(
        child_id=child.id,
        type="GROW",
        amount=actual_profit,
        description=f"Business: {template['name']}",
    )
    db.add(txn)

    # Record GROW activity
    details = {
        "idea": template["name"],
        "budget": template["min_budget"],
        "cost": template["cost"],
        "expected_profit_min": template["expected_profit_min"],
        "expected_profit_max": template["expected_profit_max"],
        "actual_revenue": int(actual_revenue),
        "actual_profit": int(actual_profit),
        "skills": template["skills"],
    }
    activity = GrowActivity(
        child_id=child.id,
        type="BUSINESS",
        details=json.dumps(details),
    )
    db.add(activity)

    db.commit()
    db.refresh(wallet)

    return {
        "wallet_balance": wallet.balance,
        "idea": template["name"],
        "cost": cost,
        "actual_revenue": actual_revenue,
        "actual_profit": actual_profit,
        "expected_profit_min": p_min,
        "expected_profit_max": p_max,
        "skills": template["skills"],
        "description": template["description"],
    }


def invest(db: Session, child: Child, invest_amount, risk_level: str) -> dict:
    """Run an investment simulation.

    1. Validate amount and risk level
    2. Deduct investment from wallet
    3. Calculate random return within risk range
    4. Calculate outcome and add to wallet (cap loss so balance >= 0)
    5. Record GROW activity and GROW transaction
    """
    amount = validate_amount(invest_amount)

    if risk_level not in INVESTMENT_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail="Invalid risk level. Choose: low, medium, or high.",
        )

    scenario = INVESTMENT_SCENARIOS[risk_level]
    wallet: Wallet = child.wallet

    if amount > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Aapke paas sirf Rs. {wallet.balance} hain. Rs. {amount} invest nahi ho sakte.",
        )

    # Deduct investment
    wallet.balance -= amount

    # Calculate random return
    return_pct = random.uniform(scenario["min_return"], scenario["max_return"])
    return_pct = round(return_pct, 2)

    # Calculate outcome
    outcome_amount = amount * (1 + Decimal(str(return_pct)) / Decimal("100"))
    outcome_amount = outcome_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    profit_loss = outcome_amount - amount

    # Add outcome to wallet, cap loss so balance never goes below 0
    add_amount = outcome_amount
    if wallet.balance + add_amount < Decimal("0"):
        add_amount = -wallet.balance
        profit_loss = add_amount - amount

    wallet.balance += add_amount

    # Record transaction
    if profit_loss >= 0:
        desc = f"Investment ({scenario['name']}): +{profit_loss} profit"
    else:
        desc = f"Investment ({scenario['name']}): {profit_loss} loss"

    txn = Transaction(
        child_id=child.id,
        type="GROW",
        amount=abs(profit_loss),
        description=desc,
    )
    db.add(txn)

    # Record activity
    details = {
        "initial_amount": float(amount),
        "risk_level": risk_level,
        "return_percentage": return_pct,
        "outcome_amount": float(outcome_amount),
        "profit_loss": float(profit_loss),
    }
    activity = GrowActivity(
        child_id=child.id,
        type="INVESTMENT",
        details=json.dumps(details),
    )
    db.add(activity)

    db.commit()
    db.refresh(wallet)

    is_profit = profit_loss >= Decimal("0")

    return {
        "wallet_balance": wallet.balance,
        "invested_amount": amount,
        "risk_level": risk_level,
        "risk_name": scenario["name"],
        "return_percentage": return_pct,
        "outcome_amount": outcome_amount,
        "profit_loss": profit_loss,
        "is_profit": is_profit,
        "risk_message": scenario["message"],
        "disclaimer": "Ye ek simulation hai. Real investment mein results hamesha alag hote hain.",
    }


def explore_skill(
    db: Session,
    child: Child,
    skill_id: str,
    practice_answer: str | None = None,
    challenge_answer: str | None = None,
    practice_text: str | None = None,
) -> dict:
    """Explore a skill card and optionally complete a challenge.

    No wallet changes — purely educational.
    Records challenge answer, correctness, and optional practice text
    in GrowActivity details for future AI Mentor context.
    """
    skill = None
    for s in SKILL_CARDS:
        if s["id"] == skill_id:
            skill = s
            break

    if not skill:
        raise HTTPException(status_code=400, detail="Invalid skill selected.")

    # Determine challenge correctness
    is_correct = None
    explanation = ""
    if challenge_answer and "challenge" in skill:
        challenge = skill["challenge"]
        for opt in challenge["options"]:
            if opt["id"] == challenge_answer:
                is_correct = opt["correct"]
                break
        if is_correct is None:
            # Invalid option ID — treat as wrong
            is_correct = False
        explanation = (
            challenge["explanation_correct"] if is_correct
            else challenge["explanation_wrong"]
        )

    # Record activity
    details = {
        "name": skill["name"],
        "category": skill["category"],
        "practice_answer": practice_answer or "",
        "earning_potential": skill["earning_potential"],
        "challenge_answer": challenge_answer or "",
        "was_correct": is_correct,
        "practice_text": practice_text or "",
    }
    activity = GrowActivity(
        child_id=child.id,
        type="SKILL",
        details=json.dumps(details),
    )
    db.add(activity)
    db.commit()

    # Update child interests if not already set
    existing_interests = json.loads(child.interests) if child.interests else []
    if skill["category"] not in existing_interests:
        existing_interests.append(skill["category"])
        child.interests = json.dumps(existing_interests)
        db.commit()

    return {
        "skill_name": skill["name"],
        "icon": skill["icon"],
        "why": skill["why"],
        "steps": skill["steps"],
        "practice_question": skill["practice_question"],
        "earning_potential": skill["earning_potential"],
        "category": skill["category"],
        "message": f"Great choice! {skill['name']} seekhna aapke future ke liye bohot acha hai!",
        "is_correct": is_correct,
        "explanation": explanation,
        "connect_text": skill.get("connect_text", ""),
        "linked_business_ids": skill.get("linked_business_ids", []),
    }
