# Rich Kids Lab — Development Rules

## 1. Product
- Product name: **Rich Kids Lab**.
- Rich Kids Lab is an educational financial-literacy simulation for Pakistani children approximately 9–13 years old.
- The child uses **virtual money only**.
- The core actions are **SAVE, SPEND, GROW, GIVE**.
- The product must remain focused enough to explain the first prototype in about one minute.

## 2. Privacy & Child Safety
- Generate an anonymous Child ID for associating simulated data.
- Do not require a real name, email, phone number, address, bank account, or other unnecessary personal information.
- Never implement real-money transactions in V1.
- Never request unnecessary personal information from the child.
- Keep business and investment experiences educational/simulated.
- Never guarantee investment returns or business income.
- Keep AI responses age-appropriate.

## 3. Language
- Primary conversational/UI language: natural **Roman Urdu**.
- Familiar English financial/UI terms may remain in English: SAVE, SPEND, GROW, GIVE, Goal, Investment, Profit, Loss, etc.
- Avoid unnecessarily formal Urdu.
- AI Mentor should respond in simple, friendly Roman Urdu by default.
- Do not force every technical/financial term into Urdu if a familiar English term is clearer.

## 4. Financial Logic
- Validate all money inputs.
- Reject negative or invalid amounts.
- Do not allow spending/saving/giving more virtual money than is available.
- Use **integer paisa** (1 rupee = 100 paisa) or **Python `Decimal`** for all money representation. Never use floating-point arithmetic for financial calculations.
- All amounts displayed to the user as whole rupees (Rs.). Internally, use the chosen representation consistently.
- Important financial logic must have tests.

## 5. AI
- AI Mentor must be contextual, not merely a generic chatbot.
- Give the AI only the relevant simulation context needed for the task.
- AI provider is **TBD** until the available hackathon resources are verified.
- Do not assume an Alibaba Cloud AI API is available.
- Do not add a paid AI service.
- Use only free-tier or hackathon-provided AI services (e.g., Groq free tier, Google Gemini free tier, or local Ollama).
- Keep the AI integration modular so the provider can be changed without rewriting the application.
- Implement a **mock/fallback AI provider** with hardcoded contextual responses so the demo never breaks if the AI service is unavailable or rate-limited.

## 6. Development
- This is a **3-day hackathon MVP**.
- Prefer simple, maintainable solutions over enterprise-level complexity.
- Do not over-engineer.
- Do not introduce unnecessary microservices, infrastructure, or dependencies.
- Do not add a new library/service without a clear reason.
- Implement one well-defined stage at a time.
- Do not modify unrelated features while implementing a scoped task.
- Preserve working functionality after every change.
- Run relevant tests/build checks after significant changes.

## 7. Qoder Workflow
- Read `RULES.md`, `SPEC.md`, and `ARCHITECTURE.md` before major implementation work.
- For large changes, plan first and implement in small, reviewable stages.
- Do not invent product requirements that are not in `SPEC.md`.
- If a requirement is ambiguous, flag it instead of silently making a major product decision.
- Keep the application runnable at every stage.

## 8. Session Resumption
- Store the anonymous Child ID in the browser's **localStorage** after session creation.
- On app load, check localStorage for an existing Child ID.
- If found, resume the session by fetching the child's data from the backend.
- If not found, show the Welcome/onboarding screen.
- This allows a child to close and reopen the browser without losing progress.

## 9. Scope
V1 includes:
- anonymous Child ID (with localStorage resumption)
- starting virtual money
- dashboard
- SAVE (with goal creation)
- SPEND (with predefined decision scenarios)
- GROW
  - Small Business simulation
  - Investment simulation
  - Learn a Skill
- GIVE simulation (with simulated impact experience)
- AI Mentor (modular provider with mock fallback)
- Roman Urdu experience

V1 supports **one active goal at a time** to keep the experience simple and focused.

Do not add unrelated features unless explicitly approved.
