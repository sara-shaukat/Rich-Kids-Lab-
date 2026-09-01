# Rich Kids Lab — Technical Architecture V1

## 1. Architecture Goal

Build a simple, maintainable, hackathon-ready application that can be completed in **3 days**.

Priorities:

1. Working product
2. Correct financial logic
3. Clear user experience
4. Contextual AI Mentor
5. Roman Urdu experience
6. Easy testing and iteration

Avoid unnecessary enterprise complexity.

---

# 2. High-Level Architecture

```text
                 CHILD
                   |
                   v
          +------------------+
          | React Frontend   |
          | (Vite)           |
          |                  |
          | Welcome          |
          | Dashboard        |
          | Save             |
          | Spend            |
          | Grow             |
          | Give             |
          | AI Mentor        |
          +--------+---------+
                   |
            Vite proxy /api
                   |
                   v
          +------------------+
          | FastAPI Backend  |
          |                  |
          | Session/Wallet   |
          | Goals            |
          | Transactions     |
          | Grow Logic       |
          | Give Logic       |
          | AI Mentor        |
          +--------+---------+
                   |
             +-----+-----+
             |           |
             v           v
       +-----------+  +-----------+
       | SQLite    |  | AI Layer  |
       | Database  |  | (Modular) |
       +-----------+  +-----------+
```

---

# 3. Technology Stack

### Frontend
**React + Vite**

Responsibilities:
- UI and user interaction
- Dashboard rendering
- API calls via a single service module
- localStorage for session resumption
- Vite dev proxy to eliminate CORS configuration

### Backend
**Python + FastAPI**

Responsibilities:
- All business logic and validation
- Wallet calculations (using Decimal)
- Transaction handling
- Goal handling
- Simulation logic (GROW)
- AI context preparation

### Database
**SQLite**

Rationale:
- Zero setup — no installation, no configuration, no credentials
- Single file (`rich_kids_lab.db`) — easy to backup, share, debug
- Fully sufficient for a single-user demo application
- SQLAlchemy abstracts the database layer — switching to PostgreSQL later requires only a connection string change

### AI
**Modular provider interface**

- Primary: free-tier API (Groq, Google Gemini, or hackathon-provided)
- Fallback: mock provider with hardcoded contextual response templates
- Provider selected via environment variable — no code change to switch
- Mock provider uses the child's actual balance, goal, and transaction data to fill template responses

### Money Representation
**Python `Decimal` type** throughout the application.

- All monetary values stored and calculated as `Decimal`.
- Database columns use `DECIMAL(10, 2)`.
- API schemas use `Decimal` fields.
- Frontend displays amounts as whole rupees (Rs.) — no paisa shown to the user.
- Never use `float` for money.

---

# 4. Data Model (5 Tables)

## 4.1 Children

```text
children
────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
anonymous_id    TEXT UNIQUE NOT NULL     -- e.g., "RKL-7F29A"
interests       TEXT                     -- JSON array, optional, e.g., '["drawing","coding"]'
created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

The `interests` column replaces the separate `profiles` table. It stores a JSON array of interest strings collected during GROW/Skill exploration. It is optional and starts as `NULL`.

No real identity is collected or stored.

---

## 4.2 Wallets

```text
wallets
───────
id              INTEGER PRIMARY KEY AUTOINCREMENT
child_id        INTEGER NOT NULL REFERENCES children(id)
balance         DECIMAL(10,2) NOT NULL DEFAULT 0
```

One wallet per child. Balance represents virtual money available for spending, saving, investing, or giving.

**Available balance** = `wallets.balance` (this is the amount shown on the dashboard as "current balance").

**Total virtual money** = `wallets.balance` + SUM of `goals.saved_amount` for all the child's goals.

---

## 4.3 Transactions

```text
transactions
────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
child_id        INTEGER NOT NULL REFERENCES children(id)
type            TEXT NOT NULL            -- SAVE | SPEND | GROW | GIVE
amount          DECIMAL(10,2) NOT NULL
description     TEXT
created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

Transaction types:
- `SAVE` — money moved from wallet into a goal
- `SPEND` — money spent on a predefined option
- `GROW` — money invested in a business or investment simulation
- `GIVE` — money given in a simulated donation

Amount is always positive. The type indicates the direction/purpose.

---

## 4.4 Goals

```text
goals
─────
id              INTEGER PRIMARY KEY AUTOINCREMENT
child_id        INTEGER NOT NULL REFERENCES children(id)
name            TEXT NOT NULL
target_amount   DECIMAL(10,2) NOT NULL
saved_amount    DECIMAL(10,2) NOT NULL DEFAULT 0
target_date     DATE                     -- optional
status          TEXT NOT NULL DEFAULT 'active'   -- active | completed
created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

V1 supports **one active goal at a time**. A new goal can only be created when the current goal's status is `completed` or no active goal exists.

---

## 4.5 GROW Activities

```text
grow_activities
───────────────
id              INTEGER PRIMARY KEY AUTOINCREMENT
child_id        INTEGER NOT NULL REFERENCES children(id)
type            TEXT NOT NULL            -- BUSINESS | INVESTMENT | SKILL
details         TEXT                     -- JSON object (see below)
created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

The `details` column stores a JSON string whose structure depends on `type`:

**BUSINESS:**
```json
{
  "idea": "Handmade Bookmarks",
  "budget": 100,
  "cost": 80,
  "revenue": 200,
  "profit": 120,
  "skills": ["creativity", "selling"]
}
```

**INVESTMENT:**
```json
{
  "initial_amount": 100,
  "risk_level": "medium",
  "return_percentage": 8.5,
  "outcome_amount": 108.5,
  "profit_loss": 8.5
}
```

**SKILL:**
```json
{
  "name": "Drawing",
  "category": "art",
  "practice_answer": "50",
  "earning_potential": "Artists can earn from commissions and selling artwork"
}
```

---

# 5. Relationships

```text
Child (1)
 │
 ├── Wallet (1)
 │
 ├── Transactions (many)
 │
 ├── Goals (many, but only 1 active at a time)
 │
 └── GROW Activities (many)
```

No separate profiles table. No separate mentor_interactions table. No separate business_activities or investment_simulations tables.

---

# 6. Savings Model

**Savings are earmarked — money moves from the wallet into the goal.**

When a child saves Rs. X toward a goal:

1. Validate: X > 0, X is numeric, X <= wallet.balance
2. `wallet.balance -= X`
3. `goal.saved_amount += X`
4. Record a `SAVE` transaction with amount = X
5. If `goal.saved_amount >= goal.target_amount`, set `goal.status = 'completed'`
6. Return updated wallet, goal, and transaction data

**Consistency invariant:** At all times, the total virtual money in the system equals:

```
wallet.balance + SUM(goals.saved_amount for all child's goals)
```

This must be preserved after every operation. Tests must verify this invariant.

---

# 7. Core API Design

```text
POST   /api/sessions                    — Create child session (generates ID, initializes wallet)
GET    /api/sessions/{anonymous_id}     — Get child data + wallet + active goal

GET    /api/dashboard/{anonymous_id}    — Get dashboard summary (balance, totals, goal progress)

POST   /api/goals                       — Create a goal (only if no active goal exists)
GET    /api/goals/{anonymous_id}        — Get all goals for child
POST   /api/goals/{goal_id}/save        — Save money toward a goal

POST   /api/transactions/spend         — Record a spend (predefined option)
POST   /api/transactions/give          — Record a give
GET    /api/transactions/{anonymous_id} — Get transaction history

POST   /api/grow/business               — Start a business simulation
POST   /api/grow/invest                 — Run an investment simulation
POST   /api/grow/skill                  — Explore a skill
GET    /api/grow/templates               — Get business templates + skill cards

POST   /api/mentor                      — Send context to AI Mentor, receive response
```

All money-related endpoints validate on the backend:
- Amount must be positive and numeric
- Amount must not exceed available wallet balance
- Wallet balance is always read from the database — never trusted from the client

---

# 8. Financial Logic

## Starting balance

```
starting_balance > 0
```

## Saving

```
save_amount > 0
save_amount <= wallet.balance
wallet.balance -= save_amount
goal.saved_amount += save_amount
```

## Spending

```
spend_amount > 0
spend_amount <= wallet.balance
wallet.balance -= spend_amount
```

## Giving

```
give_amount > 0
give_amount <= wallet.balance
wallet.balance -= give_amount
```

## Business Simulation

```
budget = template.starting_budget
IF budget > wallet.balance: REJECT
wallet.balance -= budget
profit = template.simulated_revenue - template.cost
wallet.balance += template.simulated_revenue   # revenue comes in
# Net effect: wallet.balance changed by (revenue - budget)
# Record GROW transaction with amount = budget
```

Simplified: the child pays the `budget`, the business generates `revenue`. The net gain or loss is `revenue - budget`. In V1 all predefined templates are profitable (revenue > budget) to keep the experience positive and educational.

## Investment Simulation

```
invest_amount > 0
invest_amount <= wallet.balance
wallet.balance -= invest_amount

# Determine return based on risk level:
Low risk:    return_pct = random(2, 5)
Medium risk: return_pct = random(-5, 12)
High risk:   return_pct = random(-15, 25)

outcome = invest_amount * (1 + return_pct / 100)
# Cap: outcome >= 0 (wallet balance never goes negative)
wallet.balance += outcome
profit_loss = outcome - invest_amount
# Record GROW transaction with amount = invest_amount
```

---

# 9. AI Architecture

## Context Builder

Before calling the AI provider, the backend builds a structured context object:

```json
{
  "child_id": "RKL-7F29A",
  "balance": 500,
  "goal": {
    "name": "Headphones",
    "target": 8000,
    "saved": 1500,
    "progress_pct": 18.75
  },
  "total_saved": 1500,
  "total_spent": 300,
  "total_grown": 120,
  "total_given": 50,
  "recent_transactions": [
    {"type": "SPEND", "amount": 300, "description": "Pizza", "time": "2 hours ago"},
    {"type": "SAVE", "amount": 200, "description": "Saved toward Headphones", "time": "3 hours ago"}
  ],
  "interests": ["drawing"],
  "recent_grow": {"type": "BUSINESS", "idea": "Handmade Bookmarks", "profit": 120}
}
```

## System Prompt

```
You are a friendly financial mentor for Pakistani children aged 9-13.
Respond in natural, simple Roman Urdu.
Use familiar English financial terms (save, spend, invest, profit, loss) where natural.
Be encouraging, educational, and age-appropriate.
Never guarantee investment returns.
Never suggest real financial decisions.
Keep responses short (2-4 sentences) and conversational.
Use the child's actual data to give personalized guidance.
```

## Provider Interface

```python
class AIMentorProvider:
    async def get_response(self, context: dict, child_message: str) -> str:
        raise NotImplementedError

class GroqProvider(AIMentorProvider):
    # Uses Groq free-tier API with Llama 3.3 or Mixtral

class MockProvider(AIMentorProvider):
    # Returns templated responses using context data
    # 8-10 response templates covering different scenarios
```

Provider selection via `AI_PROVIDER` environment variable: `groq`, `gemini`, or `mock`. Defaults to `mock`.

---

# 10. Session Resumption

### Flow

1. **Session creation:** Frontend calls `POST /api/sessions` → receives `anonymous_id` → stores it in `localStorage.setItem('rkl_child_id', anonymous_id)`.
2. **App load:** Frontend checks `localStorage.getItem('rkl_child_id')`.
   - If found: calls `GET /api/sessions/{anonymous_id}`. If 200, navigate to Dashboard. If 404, clear localStorage and show Welcome.
   - If not found: show Welcome screen.
3. **Session invalidation:** If the backend database is reset, old IDs return 404. Frontend clears localStorage and starts fresh.

---

# 11. Security & Privacy

- No real financial transactions.
- No unnecessary personal information collected.
- Anonymous Child ID only.
- Validate all client input on the backend.
- Never trust client-side balance calculations.
- Do not expose secret API keys in frontend code.
- Store secrets in environment variables (`.env` file, never committed).
- Do not send unnecessary child data to the AI provider.
- AI provider receives only the structured context object — no raw database rows.

---

# 12. Project Structure

```text
rich-kids-lab/
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Welcome.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Save.jsx
│   │   │   ├── Spend.jsx
│   │   │   ├── Grow.jsx
│   │   │   ├── Give.jsx
│   │   │   └── Mentor.jsx
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── BalanceCard.jsx
│   │   │   └── ActionButton.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── routes/
│   │   │   ├── session.py
│   │   │   ├── dashboard.py
│   │   │   ├── goals.py
│   │   │   ├── transactions.py
│   │   │   ├── grow.py
│   │   │   └── mentor.py
│   │   ├── services/
│   │   │   ├── wallet_service.py
│   │   │   └── grow_service.py
│   │   └── ai/
│   │       ├── mentor.py
│   │       ├── provider.py
│   │       ├── groq_provider.py
│   │       └── mock_provider.py
│   ├── tests/
│   │   └── test_wallet.py
│   ├── requirements.txt
│   ├── .env
│   └── rich_kids_lab.db          -- created on first run
│
├── RULES.md
├── SPEC.md
├── ARCHITECTURE.md
└── README.md
```

---

# 13. Implementation Stages (3-Day Plan)

## Day 1 — Foundation + SAVE + SPEND

### Stage 1: Foundation (morning, 3-4 hours)
- Initialize FastAPI project with SQLite + SQLAlchemy
- Create all 5 database models in `models.py`
- Implement `POST /api/sessions` (generate anonymous ID, create wallet)
- Implement `GET /api/sessions/{anonymous_id}` (return child + wallet)
- Implement `GET /api/dashboard/{anonymous_id}` (return balance + totals)
- Initialize React + Vite project with routing
- Build Welcome page (enter starting money → creates session)
- Build basic Dashboard page (shows balance, 4 action buttons)
- Configure Vite proxy (`/api` → `localhost:8000`)
- **Exit criterion:** Enter Rs. 500, see it on dashboard with anonymous ID

### Stage 2: SAVE (afternoon, 3-4 hours)
- Implement `POST /api/goals` (create goal — validate no active goal exists)
- Implement `POST /api/goals/{goal_id}/save` (save money with full validation)
- Implement `GET /api/goals/{anonymous_id}`
- Build Save page (create goal + save money form + progress display)
- Update Dashboard to show goal progress
- Write tests: save validation, insufficient balance, negative amount, goal completion
- **Exit criterion:** Create "Headphones Rs. 8000" goal, save Rs. 200, see progress

### Stage 3: SPEND (evening, 2-3 hours)
- Implement `POST /api/transactions/spend` (validate, deduct, record)
- Build Spend page (show predefined option cards, handle selection, show consequence)
- Update Dashboard with total spent
- Write tests: spend validation, insufficient balance
- **Exit criterion:** Spend Rs. 300 on Pizza, see balance drop, see consequence message

## Day 2 — GROW + GIVE + AI

### Stage 4: GROW (morning + early afternoon, 4-5 hours)
- Implement `GET /api/grow/templates` (return business templates + skill cards)
- Implement `POST /api/grow/business` (select template, deduct budget, add revenue, record)
- Implement `POST /api/grow/invest` (select risk level, calculate outcome, record)
- Implement `POST /api/grow/skill` (explore skill, optionally record interest)
- Build Grow page with three tabs: Business, Investment, Skill
- Business: show filtered template cards → simulation result card
- Investment: choose amount + risk level → animated outcome → disclaimer
- Skill: skill card grid → detail card → fun practice question
- Write tests: business budget check, investment loss cap
- **Exit criterion:** Try all three GROW sub-features, see results, wallet updates correctly

### Stage 5: GIVE (afternoon, 2 hours)
- Implement `POST /api/transactions/give` (validate, deduct, record)
- Build Give page (enter/select amount → confirm → impact card)
- Update Dashboard with total given
- **Exit criterion:** Give Rs. 50, see impact message, balance updates

### Stage 6: AI Mentor (evening, 2-3 hours)
- Implement mock provider (8-10 contextual response templates)
- Implement Groq provider (or other free-tier API)
- Implement `POST /api/mentor` (build context, call provider, return response)
- Build Mentor page (chat-like UI with input box + response display)
- System prompt for Roman Urdu, child-friendly, contextual responses
- Test with mock provider first, then test with live API
- **Exit criterion:** Ask mentor for advice, get contextual Roman Urdu response

## Day 3 — Integration + Polish + Demo Prep

### Stage 7: Integration & Bug Fixes (morning, 3-4 hours)
- Walk through the complete demo journey end-to-end (all 17 acceptance criteria)
- Fix all bugs found
- Implement session resumption (localStorage check on app load)
- Implement "I don't know yet" path (button on dashboard → opens Mentor with context)
- Add error handling for edge cases (invalid input, zero balance, API failures)
- Verify financial math consistency invariant

### Stage 8: Polish & Demo (afternoon + evening, 4-5 hours)
- Roman Urdu text review across all screens
- Visual consistency (colors, fonts, spacing — child-friendly, clean)
- Loading states and error messages in Roman Urdu
- Basic mobile-responsive layout
- Dry run of full demo journey (Rs. 500 starting balance)
- Prepare 1-minute explanation script
- Final bug fixes

---

# 14. Architecture Principles

1. Build the smallest useful version first.
2. Keep the application runnable after every stage.
3. Prefer simple architecture.
4. Separate financial/business logic from UI.
5. Keep AI provider replaceable.
6. Validate financial operations on the backend.
7. Keep child data minimal.
8. Do not add services just because they are available.
9. Do not introduce paid dependencies.
10. Optimize for a strong hackathon demonstration, not enterprise scale.
