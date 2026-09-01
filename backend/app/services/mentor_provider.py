"""Mentor providers — Mock (default, offline) and Groq (free tier).

Every response is produced in TWO scripts:
  - text     : Roman Urdu (displayed in the chat bubble)
  - text_ur  : Urdu script (fed to speechSynthesis for correct pronunciation)

The Mock provider is fully offline and free — it guarantees the demo
works with no internet. The Groq provider is free-tier Llama 3.3 and
gracefully falls back to Mock on ANY failure (missing key, timeout,
HTTP error, missing httpx package).
"""

import json
import os

from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class MentorProvider:
    def get_response(self, context: dict, message: str, history: list[dict]) -> dict:
        """Return {"response": str, "response_urdu": str}."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Mock provider — 12 context-driven templates in both scripts
# ---------------------------------------------------------------------------

# Topic keywords: Roman + Urdu script (voice input arrives in Urdu script)
_TOPIC_KEYWORDS = {
    "save": ["save", "bacha", "bachat", "بچا", "بچت"],
    "spend": ["spend", "kharch", "خرچ"],
    "invest": ["invest", "انویسٹ", "سرمایہ"],
    "business": ["business", "karobar", "کاروبار", "بزنس"],
    "skill": ["skill", "seekh", "سکل", "سیکھ"],
    "give": ["give", "donate", "sadqa", "عطیہ", "دین"],
}

_DONT_KNOW = ["nahi pata", "pata nahi", "kya karon", "نہیں پتا", "پتا نہیں", "کیا کروں", "کیا کریں"]


class MockProvider(MentorProvider):
    """Deterministic, offline, context-driven Roman + Urdu script replies."""

    def get_response(self, context: dict, message: str, history: list[dict]) -> dict:
        msg = (message or "").lower()
        fmt = self._format_map(context)
        was_fresh = context.get("total_actions", 0) == 0

        # 1. "I don't know" path (SPEC §14) — guided questions
        if any(k in msg for k in _DONT_KNOW):
            return self._fill(_T_DONT_KNOW, fmt)

        # 2. Topic keywords (Roman or Urdu script)
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(k in msg for k in keywords):
                return self._fill(_T_TOPICS[topic], fmt)

        # 3. Goal mention
        if "goal" in msg or "گول" in msg or "ہدف" in msg:
            if context["goal"]:
                return self._fill(_T_GOAL_PROGRESS, fmt)
            return self._fill(_T_NO_GOAL, fmt)

        # 4. State context — fresh child greeting
        if was_fresh:
            return self._fill(_T_FRESH, fmt)

        # 5. State context — no goal yet (suggest creating one)
        if not context["goal"]:
            return self._fill(_T_NO_GOAL, fmt)

        # 6. State context — low balance
        if context.get("balance", 0) < 50:
            return self._fill(_T_LOW_BALANCE, fmt)

        # 7. Default fallback
        return self._fill(_T_DEFAULT, fmt)

    def _format_map(self, context: dict) -> dict:
        goal = context.get("goal") or {}
        balance = context.get("balance", 0)
        fmt = {
            "balance": f"{balance:g}",
            "goal_name": goal.get("name", ""),
            "saved": f"{goal.get('saved', 0):g}",
            "target": f"{goal.get('target', 0):g}",
            "remaining": f"{goal.get('remaining', 0):g}",
            "progress_pct": str(goal.get("progress_pct", 0)),
            "level_name": context.get("level_name", "Newbie"),
        }
        if goal:
            fmt["goal_line"] = (
                f"Goal '{goal['name']}' ke liye {fmt['saved']} / {fmt['target']} "
                f"save ho chuke hain — sirf {fmt['remaining']} aur chahiye!"
            )
            fmt["goal_line_ur"] = (
                f"گول {goal['name']} کے لیے {fmt['saved']} / {fmt['target']} "
                f"بچ چکے ہیں — صرف {fmt['remaining']} باقی!"
            )
        else:
            fmt["goal_line"] = ""
            fmt["goal_line_ur"] = ""
        return fmt

    def _fill(self, template: dict, fmt: dict) -> dict:
        return {
            "response": template["text"].format_map(fmt),
            "response_urdu": template["text_ur"].format_map(fmt),
        }


# --- Templates: text (Roman Urdu) + text_ur (Urdu script) ---

_T_DONT_KNOW = {
    "text": (
        "Koi baat nahi, ghabrao mat! Chalo saath sochte hain. "
        "Pehle yeh batao — tumhe kya zyada pasand hai: paisay bachana, kharch karna, "
        "ya paisay banana? Abhi tumhare paas Rs. {balance} hain. "
        "Shuru ka sawal: kya tumhara koi goal hai?"
    ),
    "text_ur": (
        "کوئی بات نہیں، گھبراؤ نہیں! چلو مل کر سوچتے ہیں۔ "
        "پہلے یہ بتاؤ — تمہیں کیا زیادہ پسند ہے: پیسے بچانا، خرچ کرنا، "
        "یا پیسے کمانا؟ ابھی تمہارے پاس {balance} روپے ہیں۔ "
        "شروع کا سوال: کیا تمہارا کوئی گول ہے؟"
    ),
}

_T_TOPICS = {
    "save": {
        "text": (
            "Bachat ka sawal! Tumhare paas Rs. {balance} hain. "
            "Agar har hafte thora sa bhi bacha lo — jaise Rs. 50 — "
            "to dheere dheere bara fund ban jata hai. {goal_line} "
            "Chota qadam, bara farq!"
        ),
        "text_ur": (
            "بچت کا سوال! تمہارے پاس {balance} روپے ہیں۔ "
            "اگر ہر ہفتے تھوڑا سا بھی بچا لو — جیسے ۵۰ روپے — "
            "تو دھیرے دھیرے بڑا فنڈ بن جاتا ہے۔ {goal_line_ur} "
            "چھوٹا قدم، بڑا فرق!"
        ),
    },
    "spend": {
        "text": (
            "Kharche se pehle ek sawal poocho: kya ye cheez zaroori hai "
            "ya sirf dil chahta hai? Zaroori cheez pehle — wish baad mein. "
            "Isi ko smart spending kehte hain!"
        ),
        "text_ur": (
            "خرچ سے پہلے ایک سوال پوچھو: کیا یہ چیز ضروری ہے "
            "یا صرف دل چاہتا ہے؟ ضروری چیز پہلے — خواہش بعد میں۔ "
            "اسی کو اسمارٹ اسپینڈنگ کہتے ہیں!"
        ),
    },
    "invest": {
        "text": (
            "Investment ka matlab: paisay ko kaam par lagana taake barh jaye. "
            "Lekin yaad rakho — jitna bara risk, utna bara chance. "
            "GROW mein teen options hain — low risk se shuru karna behtar hai!"
        ),
        "text_ur": (
            "انویسٹمنٹ کا مطلب: پیسے کو کام پر لگانا تاکہ بڑھ جائے۔ "
            "لیکن یاد رکھو — جتنا بڑا رِسک، اتنا بڑا چانس۔ "
            "گرو میں تین آپشنز ہیں — لو رِسک سے شروع کرنا بہتر ہے!"
        ),
    },
    "business": {
        "text": (
            "Business matlab apna kaam khud shuru karna! "
            "GROW mein 5 business ideas hain — bookmarks se sticker shop tak. "
            "Pehla business sirf Rs. 30 se shuru ho sakta hai. "
            "Kaun sa try karna chahoge?"
        ),
        "text_ur": (
            "بزنس مطلب اپنا کام خود شروع کرنا! "
            "گرو میں ۵ بزنس آئڈیاز ہیں — بک مارکس سے اسٹیکر شاپ تک۔ "
            "پہلا بزنس صرف ۳۰ روپے سے شروع ہو سکتا ہے۔ "
            "کون سا آزماتے ہو؟"
        ),
    },
    "skill": {
        "text": (
            "Skill seekhna bhi paisay kamane ki tayari hai! "
            "SKILL LAB mein 6 skills hain — AI prompting, coding, writing, "
            "photography, video editing aur crafts. Tumhara favourite kaun sa hai?"
        ),
        "text_ur": (
            "سکل سیکھنا بھی پیسے کمانے کی تیاری ہے! "
            "سکل لیب میں ۶ سکلز ہیں — اے آئی پرامپٹنگ، کوڈنگ، رائٹنگ، "
            "فوٹوگرافی، ویڈیو ایڈیٹنگ اور کرافٹس۔ تمہارا پسندیدہ کون سا ہے؟"
        ),
    },
    "give": {
        "text": (
            "Denay wala hamesha aage hota hai! GIVE mein tum apne virtual "
            "paisay kisi achi wajah ke liye de sakte ho. Dil bara karo — "
            "sharing bhi ek money habit hai."
        ),
        "text_ur": (
            "دینے والا ہمیشہ آگے ہوتا ہے! گِو میں تم اپنے ورچوئل "
            "پیسے کسی اچھی وجہ کے لیے دے سکتے ہو۔ دل بڑا کرو — "
            "شیئرنگ بھی ایک منی ہیبٹ ہے۔"
        ),
    },
}

_T_GOAL_PROGRESS = {
    "text": (
        "Goal '{goal_name}' ke liye {saved} / {target} save ho chuke hain — "
        "sirf {remaining} aur chahiye! Tum {progress_pct}% par ho. "
        "Har save goal ko qareeb le jata hai. Bas thora aur!"
    ),
    "text_ur": (
        "گول {goal_name} کے لیے {saved} / {target} بچ چکے ہیں — "
        "صرف {remaining} باقی! تم {progress_pct} فیصد پر ہو۔ "
        "ہر بچت گول کو قریب لے جاتی ہے۔ بس تھوڑا اور!"
    ),
}

_T_NO_GOAL = {
    "text": (
        "Abhi koi goal nahi hai — aur yehi sab se pehla kaam hai! "
        "Jaise archer ko target chahiye, waise paison ko goal chahiye. "
        "SAVE page par jao aur pehla goal banao. Main madad ke liye yahin hoon!"
    ),
    "text_ur": (
        "ابھی کوئی گول نہیں ہے — اور یہی سب سے پہلا کام ہے! "
        "جیسے تیر انداز کو ٹارگٹ چاہیے، ویسے پیسوں کو گول چاہیے۔ "
        "سیو صفحے پر جاؤ اور پہلا گول بناؤ۔ میں مدد کے لیے یہیں ہوں!"
    ),
}

_T_FRESH = {
    "text": (
        "Assalamu Alaikum! Main Paisa Bot hoon — tumhara paisay ka dost. "
        "Tum abhi {level_name} level par ho aur Rs. {balance} tumhare paas hain. "
        "Main bachat, kharch, investment, business aur skill — sab mein madad kar sakta hoon. "
        "Kahan se shuru karein?"
    ),
    "text_ur": (
        "السلام علیکم! میں پیسہ بوٹ ہوں — تمہارے پیسے کا دوست۔ "
        "تم ابھی {level_name} لیول پر ہو اور {balance} روپے تمہارے پاس ہیں۔ "
        "میں بچت، خرچ، انویسٹمنٹ، بزنس اور سکل — سب میں مدد کر سکتا ہوں۔ "
        "کہاں سے شروع کریں؟"
    ),
}

_T_LOW_BALANCE = {
    "text": (
        "Balance Rs. {balance} hai — thora kam, lekin koi masla nahi! "
        "GROW mein business ya investment se paisay barha sakte ho. "
        "Chota business sirf Rs. 30 se shuru hota hai!"
    ),
    "text_ur": (
        "بیلنس {balance} روپے ہے — تھوڑا کم، لیکن کوئی مسئلہ نہیں! "
        "گرو میں بزنس یا انویسٹمنٹ سے پیسے بڑھا سکتے ہو۔ "
        "چھوٹا بزنس صرف ۳۰ روپے سے شروع ہوتا ہے!"
    ),
}

_T_DEFAULT = {
    "text": (
        "Achaa sawal! Chalo sochte hain. Tumhare paas abhi Rs. {balance} hain. "
        "Kya tum save karna chahte ho, kuch kharch karna hai, "
        "ya paisay barhana hai? Main teeno mein madad kar sakta hoon!"
    ),
    "text_ur": (
        "اچھا سوال! چلو سوچتے ہیں۔ تمہارے پاس ابھی {balance} روپے ہیں۔ "
        "کیا تم بچانا چاہتے ہو، کچھ خرچ کرنا ہے، "
        "یا پیسے بڑھانا ہے؟ میں تینوں میں مدد کر سکتا ہوں!"
    ),
}


# ---------------------------------------------------------------------------
# Groq provider — free tier (Llama 3.3 70B), falls back to Mock on ANY error
# ---------------------------------------------------------------------------

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "groq/compound"

SYSTEM_PROMPT = """You are Paisa Bot, a friendly financial mentor for Pakistani children aged 9-13.
Respond in natural, simple Roman Urdu with familiar English financial terms (save, spend, invest, profit, loss, assets, liabilities) where natural.
Be encouraging, educational, and age-appropriate.
Use the child's context data to give personalized guidance.
Keep responses short (2-4 sentences) and conversational.
Ask a follow-up question when it helps the child decide.
Never guarantee investment returns or income.
Never give real-world financial advice — this is a virtual money simulation.
If asked something off-topic, gently bring the conversation back to money choices.
Reply in EXACTLY this format (the child speaks Urdu, so both lines are needed):
<Roman Urdu reply>
###
<Urdu script version of the same reply>"""


class GroqProvider(MentorProvider):
    """Groq free-tier model. Any failure -> MockProvider."""

    def __init__(self):
        self._fallback = MockProvider()

    def get_response(self, context: dict, message: str, history: list[dict]) -> dict:
        try:
            content = self._call_api(context, message, history)
            response, response_urdu = self._parse(content)
            return {"response": response, "response_urdu": response_urdu}
        except Exception:
            return self._fallback.get_response(context, message, history)

    def _call_api(self, context: dict, message: str, history: list[dict]) -> str:
        # httpx is imported lazily so the app runs fine without it installed
        import httpx

        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nChild context: " + json.dumps(context)},
        ]
        for item in history[-6:]:
            role = "user" if item.get("role") == "child" else "assistant"
            messages.append({"role": role, "content": str(item.get("text", ""))[:500]})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 350,
            "temperature": 0.7,
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        with httpx.Client(timeout=15) as client:
            resp = client.post(GROQ_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    def _parse(self, content: str) -> tuple[str, str]:
        parts = content.split("###")
        response = parts[0].strip()
        response_urdu = parts[1].strip() if len(parts) > 1 else response
        if not response:
            response = response_urdu
        if not response:
            raise RuntimeError("Empty Groq response")
        return response, response_urdu


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_mentor_provider() -> MentorProvider:
    """Select the provider from the AI_PROVIDER env var (default: mock)."""
    provider = os.environ.get("AI_PROVIDER", "mock").strip().lower()
    if provider == "groq" and os.environ.get("GROQ_API_KEY"):
        return GroqProvider()
    return MockProvider()
