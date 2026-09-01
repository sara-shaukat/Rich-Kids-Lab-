# Rich Kids Lab -- Vibe Makeover Plan (v2)

## Problem
The app works (5 stages, 67 tests passing) but feels like a banking app. No personality, no engagement, no fun. Kids won't share it.

## Solution Overview
4 pillars: **Roasting Mascot** + **Meme Badges** + **Assets/Liabilities** + **Track Record**

---

## 1. Backend: Expanded Dashboard API

**Files:** `backend/app/routes/dashboard.py`, `backend/app/schemas.py`

Expand `GET /api/dashboard/{anonymous_id}` with new fields:

- `net_worth` (Decimal) -- balance + saved_amount + total_grown_profit
- `assets` (list) -- profitable businesses + winning investments with amounts
- `liabilities` (list) -- losing investments + total spent
- `business_history` (list) -- every business tried with name, cost, profit/loss, date
- `investment_history` (list) -- every investment with risk, amount, return, profit/loss
- `badges` (list) -- earned badges with icon, name, meme_line, earned_at
- `level` (object) -- name, number, progress_to_next, total_actions
- `last_action_type` (str or null) -- most recent action type for mascot context

**Net Worth formula:**
`net_worth = wallet.balance + SUM(active_goals.saved_amount) + net_grow_profit`

**Assets** = each business with profit > 0, each investment with profit > 0
**Liabilities** = each investment with loss, total SPEND amount

---

## 2. Backend: Badge System (computed, no new table)

**File:** `backend/app/services/badge_service.py` (new)

7 badges, all computed from existing transactions + grow_activities.
NO piggy icons (Muslim audience). Culturally neutral icons only.

| Badge | Icon | Condition | Meme Line (toast when earned) |
|-------|------|-----------|------------------------------|
| First Save | 💰 | Any SAVE txn | "Sigma grindset activated! Paisay bachana seekh gaya!" |
| First Business | 🚀 | Any BUSINESS activity | "CEO ban gaya! Elon Musk ko call karo!" |
| First Give | 🤲 | Any GIVE txn | "Sadqa jariya! Allah bless kare bhai!" |
| Big Spender | 💸 | Total SPEND >= 200 | "Kharcha king! Lekin bhai budget bhi dekh!" |
| Profit Maker | 📈 | 3+ BUSINESS activities | "Serial entrepreneur! Paisa follow karta hai!" |
| Explorer | 🧭 | All 3 GROW types tried | "Jack of all trades! Teeno try kar liye!" |
| Money Master | 👑 | Net worth > starting balance | "Money Master! Paisa hi paisa hoga!" |

**Level system** (total actions = transactions + grow activities):
- L1 "Newbie" (0-2) -- "Chal seekhte hain!"
- L2 "Seekhne Wala" (3-5) -- "Hunnar aa raha hai!"
- L3 "Smart Saver" (6-10) -- "Ab tu expert ban raha hai!"
- L4 "Paisa Pro" (11+) -- "Bhai tu toh Warren Buffet nikla!"

---

## 3. Backend: Mascot Lines Data

**File:** `backend/app/services/mascot_lines.py` (new)

Two pools of lines -- motivational and roasts. Dashboard API returns the appropriate line based on user state + last action.

**Motivational lines** (60% chance):
- Default tips (rotate): "Paisa follows my brother, paisa follows!" / "Aaj kuch seekhte hain!" / "Paisay ki duniya mein aao!"
- After save: "Shabash! Warren Buffet bhi impressed hoga!"
- After give: "Sadqa jariya activated! Allah bless kare!"
- After business profit: "Munafa! Paisa follow karta hai bhai ko!"
- After investment profit: "Returns! Sigma grindset on top!"
- Level up: "Level up! Tu toh legend ban raha hai!"

**Roast lines** (40% chance, context-dependent):
- Balance < 50: "Bhai tera balance ro raha hai... thora bacha le!"
- After overspending: "Itne mein toh 2 biryani aur aa jati thin..."
- After bad investment: "Loss ho gaya bhai... Warren Buffet thori tha tu?"
- After wasting money: "Bro went full YOLO on snacks. Respect."
- No savings goal: "Goal kahan hai bhai? Bina target ke archer?"
- Balance = 0: "Zero hero! Chal koi baat nahi, seekh gaya na!"
- Multiple losses: "Tu toh financial disaster movie ka hero hai!"

API returns: `{ mascot_line: "...", mascot_mode: "hype" | "roast" }`

---

## 4. Backend Tests

**File:** `backend/tests/test_dashboard_v2.py` (new)

- Net worth calculation with and without businesses/investments
- Assets and liabilities lists populated correctly
- Each badge earned/not-earned condition
- Level progression
- Business/investment history completeness
- Mascot line selection logic

---

## 5. Frontend: CSS Mascot -- "Paisa Bot" with Roasting

**File:** `frontend/src/components/Mascot.jsx` (new) + CSS

CSS-only animated character:
- Round face, dot eyes, money-bag hat (built with divs/borders)
- Idle bounce animation
- Speech bubble with typewriter text reveal
- Two visual modes: green glow (hype) / red tinge (roast)
- Click to cycle through random tips/roasts
- Props: `mode` ("hype"|"roast"), `line` (text), `lastAction` (type)

Placed on:
- Dashboard (persistent, top) -- reads mascot_line from dashboard API
- Welcome page (greeting mode, always hype)
- Result screens in Save/Spend/Grow/Give (contextual reaction)

---

## 6. Frontend: Dashboard Makeover

**File:** `frontend/src/pages/Dashboard.jsx`, `frontend/src/index.css`

New layout (top to bottom):
```
[Mascot + speech bubble with tip/roast]
[Balance Card -- big, pulsing coin animation]
[Level Bar -- "Level 2: Seekhne Wala" with progress fill]
[Badges Row -- earned = lit + icon, unearned = locked gray]
[My Money Empire -- Assets (green col) vs Liabilities (red col)]
[Business Track Record -- expandable list, color-coded profit/loss]
[Goal Progress -- unchanged but styled]
[4 Action Buttons -- bigger with hover scale animation]
[AI Mentor button]
```

**Badge display:** Earned badges glow with icon + name + meme line on hover/tap. Unearned show as grayed lock with condition text.

**Business Track Record:** Each row = business name, cost, profit/loss (green/red), emoji verdict. "Ye business ne kaam kiya!" / "Ye business ne kaam nahi kiya"

---

## 7. Frontend: Welcome Page Refresh

**File:** `frontend/src/pages/Welcome.jsx`

- Add mascot greeting at top ("Paisa Bot aapka swagat karta hai!")
- More colorful animated background
- Fun tagline: "Apni paiso ki duniya banao!"
- Keep functionality identical (amount input + start button)

---

## 8. Frontend: API Update

**File:** `frontend/src/services/api.js`

- `getDashboard()` parses new fields (net_worth, assets, liabilities, badges, level, history, mascot_line, mascot_mode)
- No new endpoints -- everything from expanded dashboard response

---

## Implementation Order

1. `backend/app/services/badge_service.py` -- 7 badge checkers + level calculator
2. `backend/app/services/mascot_lines.py` -- motivational + roast line pools
3. `backend/app/routes/dashboard.py` + `backend/app/schemas.py` -- expanded response
4. `backend/tests/test_dashboard_v2.py` -- tests for all new fields
5. `frontend/src/components/Mascot.jsx` -- CSS mascot + speech bubble
6. `frontend/src/pages/Dashboard.jsx` -- full makeover
7. `frontend/src/pages/Welcome.jsx` -- refresh with mascot
8. `frontend/src/index.css` -- all new styles
9. Run all tests, browser verify end-to-end

---

## What Stays Unchanged
- All Stage 1-5 backend logic and tests (67 tests must keep passing)
- All existing routes, models, services
- SAVE, SPEND, GROW, GIVE page core functionality
- Database schema (no new tables -- all computed from existing data)
- Stage 6 (AI Mentor) is NOT touched

---

## Exit Criterion
- Dashboard shows mascot with speech bubble (tips + roasts), badges, level, assets vs liabilities, business track record
- Welcome page has mascot greeting
- At least 3 badges earnable by performing actions
- Mascot roasts when balance is low or decisions are bad
- All 67+ existing tests still pass + new dashboard v2 tests
