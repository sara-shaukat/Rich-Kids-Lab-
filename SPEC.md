# Rich Kids Lab — V1 Product Specification

## 1. Product Overview

**Rich Kids Lab** is an AI-powered financial-literacy simulation for Pakistani children approximately 9–13 years old.

The core idea is:

> **Don't just teach children about money. Let them practice making money decisions.**

Children use virtual money to make choices, observe consequences, and receive personalized guidance from an AI Mentor.

### Core actions

**SAVE → SPEND → GROW → GIVE**

The primary conversational language is natural **Roman Urdu**, with familiar English financial/UI terms where useful.

---

## 2. Target User

A child approximately 9–13 years old who is learning basic financial decision-making.

The V1 prototype does not require account registration or real-world identity.

The system generates an anonymous Child ID so simulated data can be associated with the correct child/session.

---

## 3. Product Principles

1. Make financial learning interactive rather than purely theoretical.
2. Let children safely experiment using virtual money.
3. Show consequences of financial decisions.
4. Make guidance personalized.
5. Keep language natural and accessible to Pakistani children.
6. Keep the first prototype narrow enough to demonstrate clearly.
7. Avoid unnecessary collection of children's personal information.

---

## 4. V1 User Journey

1. Open Rich Kids Lab.
2. Receive an anonymous Child ID.
3. Enter starting virtual money.
4. Arrive at the Dashboard.
5. Choose SAVE, SPEND, GROW, or GIVE.
6. See the result/consequence of the decision.
7. Ask or receive guidance from the AI Mentor.
8. Return to the Dashboard and see the updated financial journey.

### Primary demo journey

Starting balance: **Rs. 500**

- Create a goal.
- Save some money.
- Make a spending decision.
- Observe the consequence.
- Explore a small-business idea.
- Try an investment simulation.
- Give a virtual amount.
- Ask the AI Mentor for guidance.
- Return to the dashboard and see the updated journey.

---

## 5. Language Requirements

### UI
Use simple Roman Urdu and familiar English financial terms.

Examples:
- "Aap ke paas kitne virtual paisay hain?"
- "Aap apne paisay ka kya karna chahte ho?"
- "Mera Goal"
- "Aaj kitna save karna hai?"

### AI Mentor
Default response language: natural, child-friendly Roman Urdu.

Example:

> "Aapne Rs. 200 save kiye hain. Ab aap apne goal ke aur qareeb ho! Agar aap isi tarah save karte rahe to aap apna goal complete kar sakte ho."

Avoid unnecessarily formal Urdu.

---

## 6. Initial Money

### User goal
The child enters the amount of virtual money they want to start with.

### Screen
**"Aap ke paas kitne virtual paisay hain?"**

Example: `Rs. 500`

### Requirements
- Accept valid numeric input.
- Amount must be greater than zero.
- Reject negative, empty, or invalid input.
- Store it as virtual money.

---

## 7. Anonymous Child ID

Generate an anonymous identifier automatically.

Example:

`RKL-7F29A`

The child does not need to provide identifying information.

Purpose:
- associate wallet data
- associate goals
- associate transactions
- provide relevant context to the AI Mentor

---

## 8. Dashboard

The Dashboard is the central screen.

Display:
- current virtual balance
- goal progress
- total saved
- total spent
- total grown
- total given
- SAVE action
- SPEND action
- GROW action
- GIVE action
- AI Mentor entry point

The dashboard should make the child's financial journey understandable at a glance.

---

# 9. SAVE

## Goals — Single Active Goal

V1 supports **one active goal at a time**. A child creates one goal and works toward it. Once a goal is completed (saved_amount reaches target_amount), the child may create a new goal. This keeps the experience focused and avoids overwhelming a child with multiple goals.

## Goal Creation

The child creates a financial goal.

Example:

**Goal:** Headphones
**Target:** Rs. 8,000

Required:
- goal name
- target amount

Optional:
- target date

## Goal Progress

Show:
- target amount
- amount saved
- amount remaining
- percentage progress

Example:

`Rs. 1,500 / Rs. 8,000`

## Saving

When the child saves virtual money:
1. Validate amount (positive, numeric).
2. Ensure available wallet balance is sufficient.
3. Deduct the saved amount from the wallet balance.
4. Increase the goal's `saved_amount` by the same amount.
5. Record a SAVE transaction.
6. Update dashboard.

The child's **total virtual money** = wallet balance + sum of saved_amount across all goals. Saving does not destroy money — it moves it from the available wallet into the goal.

Educational message example:

> "Thora thora save karne se aap apne bade goals ko achieve kar sakte ho."

---

# 10. SPEND

SPEND should be a decision-making experience rather than only a transaction form.

Example:

> "Aapke paas Rs. 500 hain. Aap kya choose karoge?"

### V1 Spend Options (Predefined)

For V1, spend options are **predefined scenarios** — not a free-form input. The system presents 3–4 choices per round. Each choice has a name, cost, and a consequence message.

**Scenario Set 1 — Everyday Choices:**
| Option | Cost | Consequence Message |
|---|---|---|
| Pizza | Rs. 300 | "Mazedaar pizza! Lekin ab aapke paas kam paisay hain." |
| Book | Rs. 200 | "Kitab parhna ek achi aadat hai! Aapne seekhne mein invest kiya." |
| Game | Rs. 250 | "Game khelna mazedaar hai! Lekin yaad rakho, entertainment bhi budget mein hona chahiye." |
| Save Instead | Rs. 0 | "Bohot acha faisla! Kabhi kabhi na khareedna bhi ek smart choice hai." |

**Scenario Set 2 — Weekend Choices:**
| Option | Cost | Consequence Message |
|---|---|---|
| Cinema | Rs. 400 | "Cinema ka maza! Lekin ye ek luxury hai — zaroorat nahi." |
| Snack | Rs. 100 | "Chota snack, chota kharcha. Smart choice!" |
| Toy | Rs. 350 | "Khilona khareedna acha hai, lekin kya ye zaroori tha?" |
| Save Instead | Rs. 0 | "Aapne paise bachaye. Ye discipline hai!" |

The system selects a scenario set (randomly or sequentially). Only options the child can afford are shown as selectable. The "Save Instead" option is always available and costs nothing.

When a choice is made:
1. Validate the amount.
2. Update virtual balance.
3. Record the SPEND transaction where applicable.
4. Show the consequence.
5. Reflect the updated state on the dashboard.

Educational objective:

> **Financial choices have consequences.**

---

# 11. GROW

GROW is a major V1 feature.

It contains:

1. Start a Small Business
2. Investment Simulation
3. Learn a Skill

---

## 11.1 Start a Small Business

The child selects:

> "Main chota sa business start karna chahta/chahti hoon."

### Business Simulation Lifecycle

1. The system presents a list of **predefined business templates** filtered by the child's available budget.
2. The child selects a business idea.
3. The system shows a simulation card with educational data.
4. The child "starts" the business — the starting budget is deducted from their wallet.
5. The simulated revenue/profit is calculated and displayed.
6. The simulated profit (revenue minus cost) is added back to the wallet.
7. A GROW transaction is recorded.

**Key rule:** The child only sees the simulation results after "starting" the business. The simulation is clearly labeled as educational and simulated.

### Predefined Business Templates (V1)

| Business Idea | Min Budget | Cost | Revenue | Profit | Skills |
|---|---|---|---|---|---|
| Handmade Bookmarks | Rs. 100 | Rs. 80 | Rs. 200 | Rs. 120 | creativity, selling |
| Lemonade Stand | Rs. 150 | Rs. 120 | Rs. 350 | Rs. 230 | planning, customer service |
| Homework Helper | Rs. 50 | Rs. 30 | Rs. 150 | Rs. 120 | teaching, patience |
| Art Cards | Rs. 200 | Rs. 150 | Rs. 400 | Rs. 250 | art, marketing |
| Sticker Shop | Rs. 250 | Rs. 200 | Rs. 500 | Rs. 300 | design, selling |

The system filters templates to only show those where `Min Budget <= child's current wallet balance`.

Example simulation card:

> "Aapko drawing pasand hai aur aapke paas Rs. 300 hain. Aap handmade bookmarks ka business simulation try kar sakte ho."
>
> **Budget:** Rs. 100 | **Cost:** Rs. 80 | **Revenue:** Rs. 200 | **Profit:** Rs. 120
>
> ⚠️ "Ye ek simulation hai. Real business mein results alag ho sakte hain."

---

## 11.2 Investment Simulation

Use virtual money only.

Teach:
- profit
- loss
- risk
- uncertainty

### V1 Investment Scenarios (Deterministic with Mild Randomization)

Investment scenarios are **predetermined educational scenarios** — not real market simulations. Each scenario has a fixed educational narrative and a randomized outcome within a defined range.

The child:
1. Chooses how much to invest (from their wallet).
2. Selects a risk level (Low / Medium / High).
3. Sees the outcome after a simulated "time period."

**Scenario Definitions:**

| Risk Level | Outcome Range | Educational Message |
|---|---|---|
| Low (Savings Account) | +2% to +5% return | "Kam risk, kam reward. Ye safe choice hai." |
| Medium (Small Fund) | -5% to +12% return | "Medium risk — kabhi profit, kabhi thora loss." |
| High (Startup Idea) | -15% to +25% return | "High risk — bada profit ho sakta hai, lekin loss bhi ho sakta hai!" |

**Outcome calculation:**
- `return_percentage` = random value within the risk level's range
- `outcome_amount` = invested_amount × (1 + return_percentage / 100)
- `profit_loss` = outcome_amount - invested_amount
- If profit_loss is positive, the profit is added to the wallet.
- If profit_loss is negative, the loss is deducted from the wallet (but wallet balance must not go below zero — cap the loss).

**Safety rules:**
- The invested amount is deducted from the wallet at the start.
- The outcome amount is added to the wallet at the end.
- Loss is capped so wallet balance never goes below zero.
- Every outcome displays a clear disclaimer: "Ye ek simulation hai. Real investment mein results hamesha alag hote hain."
- The system must NOT guarantee profit.

Example educational message:

> "Is simulation mein investment ki value barh gayi, lekin real life mein investment ka result hamesha same nahi hota."

---

## 11.3 Learn a Skill

The system suggests skills based on the child's selected interests (if any) or presents a general skill exploration screen.

### V1 Skill Experience

The Learn a Skill experience is a **guided interactive card flow** — not a complex system:

1. The child sees a grid of **skill cards** with icons and short descriptions.
2. The child taps a skill card that interests them.
3. The system shows a **skill detail card** with:
   - Skill name
   - Why it matters (earning potential connection)
   - Simple steps to start learning
   - An encouraging message
4. The child can "practice" the skill by answering a simple fun question related to the skill (e.g., for drawing: "Agar aap ek bookmark design karte ho, to aap kitne mein bechte? Rs. ___").
5. The system shows a result message connecting skill → earning potential.

### V1 Skill Cards (Predefined)

| Skill | Icon | Why It Matters | Starter Steps |
|---|---|---|---|
| Drawing | 🎨 | "Artists apni creativity se paisay kama sakte hain!" | Practice 10 min daily, try selling art |
| Coding | 💻 | "Coding seekho, apps banao, future ready ho!" | Start with Scratch, then Python |
| Writing | ✍️ | "Acha likhna ek superpower hai!" | Write a short story daily |
| Photography | 📸 | "Photos se stories batao aur earn karo!" | Practice with phone camera |
| Video Editing | 🎬 | "Videos banana seekho — bohot demand hai!" | Try free editing apps |
| Crafts | ✂️ | "Haath se banana ek valuable skill hai!" | Make something new weekly |

Educational connection:

**Interest → Skill → Practice → Potential future earning**

Do not present earnings as guaranteed. The "practice" question is purely educational and does not involve real wallet transactions.

---

# 12. GIVE

GIVE teaches that money can also create positive social impact.

Flow:

`GIVE → choose virtual amount → confirm → simulated impact experience`

### V1 Give Impact Experience

When a child gives virtual money:

1. The child enters or selects an amount to give.
2. The system shows a confirmation: "Kya aap Rs. ___ dena chahte ho?"
3. On confirm, the amount is deducted from the wallet.
4. A GIVE transaction is recorded.
5. The system shows an **impact card** based on the amount given:

| Amount Range | Impact Message |
|---|---|
| Rs. 10–50 | "Rs. {amount} se ek bachay ke liye ek notebook khareedi ja sakti hai! 📓" |
| Rs. 51–100 | "Rs. {amount} se ek family ko ek din ka ration mil sakta hai! 🍞" |
| Rs. 101–200 | "Rs. {amount} se ek bachay ka school bag khareeda ja sakta hai! 🎒" |
| Rs. 201–500 | "Rs. {amount} se ek chhoti si medical help ho sakti hai! 💊" |
| Rs. 500+ | "Rs. {amount} — bohot bara contribution! Aap ne dikhaya ke paisay sirf kharch karne ke liye nahi, madad ke liye bhi hain! 🌟" |

6. Follow-up educational message:

> "Money sirf cheezen khareedne ke liye nahi, doosron ki madad ke liye bhi use ho sakta hai. Aap ne aaj ek acha kaam kiya!"

### Alkhidmat context

The feature may be visually/aligned with the hackathon's social-impact context.

However, V1 must NOT claim an official Alkhidmat donation or API integration unless such integration is explicitly provided/approved by the organizers.

V1 uses a simulated giving experience only.

---

# 13. AI MENTOR

The AI Mentor is a contextual educational assistant.

It can use relevant current simulation context:
- anonymous Child ID when necessary for lookup
- virtual balance
- goals
- recent transactions
- saving/spending behavior
- interests
- GROW activities

It should produce:
- personalized feedback
- explanations
- encouragement
- next-step suggestions
- simple financial education

Default language: natural Roman Urdu.

### Example

Context:
- Balance: Rs. 500
- Goal: Headphones — Rs. 8,000
- Recent spend: Rs. 250
- Recent save: Rs. 100

Possible response:

> "Aap apne headphones goal ke liye progress kar rahe ho! Aapne Rs. 100 save kiye, lekin Rs. 250 spend bhi kiye. Agar aap next time thora kam spend karo aur Rs. 150 save karo to aap goal ke aur qareeb ja sakte ho."

The AI should not behave as a generic unrestricted chatbot.

### AI Provider Strategy

- Primary: Free-tier API (Groq, Google Gemini, or hackathon-provided).
- Fallback: Mock provider with 8–10 hardcoded contextual response templates that use the child's actual balance, goal, and recent transaction data.
- The mock provider ensures the demo works even if the AI service is unavailable.
- Provider is selected via environment variable. No code change required to switch.

---

# 14. "I DON'T KNOW YET"

Provide a path for a child who does not know what to do.

Example:

> "Mujhe nahi pata."

The AI can ask simple questions about:
- interests
- skills
- goals
- available virtual money

Then guide the child toward SAVE, SPEND, GROW, or GIVE.

---

# 15. Session Resumption

- When a session is created, the anonymous Child ID is stored in the browser's **localStorage**.
- On app load, the frontend checks localStorage for an existing Child ID.
- If found: the app fetches the child's data (wallet, goals, transactions) and navigates directly to the Dashboard.
- If not found: the app shows the Welcome/onboarding screen.
- This allows a child to close the browser and resume later without losing progress.
- If the backend cannot find the stored Child ID (e.g., server was reset), the app clears localStorage and shows the Welcome screen.

---

# 16. Data Requirements

V1 needs to associate:

### Child/session
- anonymous ID
- optional interests (collected during GROW/Skill exploration)

### Wallet
- current virtual balance

### Transactions
- type (SAVE, SPEND, GROW, GIVE)
- amount
- description
- timestamp

### Goals
- name
- target amount
- saved amount
- optional target date
- status (active, completed)

### GROW activities
- type (BUSINESS, INVESTMENT, SKILL)
- details (idea/budget/cost/revenue/profit for business; amount/risk/outcome for investment; skill name/category for skill)

### AI
No persistent conversation storage in V1. Context is built per-request from the child's current data.

---

# 17. Acceptance Criteria

V1 is considered functionally complete when a tester can:

1. Start the application.
2. Receive an anonymous Child ID.
3. Enter Rs. 500 virtual money.
4. See the balance on the dashboard.
5. Create a goal.
6. Save money toward the goal.
7. Spend virtual money and see the consequence.
8. Open GROW.
9. Generate/explore an age-appropriate business idea.
10. Run an investment simulation.
11. Explore a skill.
12. Give a virtual amount and see an impact message.
13. Open the AI Mentor.
14. Receive contextual guidance in natural Roman Urdu.
15. Return to the dashboard and see the financial journey reflected correctly.
16. Close the browser, reopen, and resume the session from where they left off.

---

# 18. Out of Scope for V1

- Real payments
- Real donations
- Real investment
- Bank integration
- Parent accounts
- Teacher dashboards
- Social networking
- Complex gamification systems
- Unnecessary authentication
- Paid third-party services
- Unverified Alibaba Cloud service assumptions
- Multiple concurrent goals
- Free-form spend (V1 uses predefined scenarios)
- Real-time market data for investments
