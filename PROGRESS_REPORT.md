# Rich Kids Lab — Progress Report

## Project Overview
**AI-powered financial literacy simulation for Pakistani children (ages 9–13)**
- 3-day hackathon project
- Roman Urdu primary language (accessible to masses)
- Virtual money simulation — no real money involved
- 4 core actions: SAVE, SPEND, GROW, GIVE

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14 + FastAPI + SQLite + SQLAlchemy |
| Frontend | React + Vite + react-router-dom |
| Database | 5 tables (children, wallets, transactions, goals, grow_activities) |
| API | RESTful JSON endpoints |

---

## Completed Stages

### ✅ Stage 1 — Foundation (Complete)
- Welcome screen with starting money input
- Anonymous child creation (format: RKL-XXXXXX)
- Session persistence via localStorage
- Dashboard with balance display and 4 action buttons
- SQLite database with all 5 tables
- **17 tests passing**

### ✅ Stage 2 — SAVE (Complete)
- Goal creation with name + target amount
- Single active goal constraint
- Partial and full saving with progress tracking
- Consistency invariant: wallet.balance + SUM(goal.saved_amount) = total virtual money
- Goal completion tracking
- **Exit criterion met:** Create goal, save partial amount, see progress update

### ✅ Stage 3 — SPEND (Complete)
- 2 predefined scenario sets: Everyday + Weekend (randomly selected)
- 4 options per scenario with affordability flags
- "Save Instead" option always available
- Consequence messages in Roman Urdu
- Educational nudge if active goal exists
- **10 tests passing | Exit criterion met**

### ✅ Stage 4 — GROW (Complete)
**3 Sub-Features:**
- **Business:** Hybrid AI recommendations — interest picker → ranked templates with Roman Urdu pitches → simulated business with randomized profit within expected ranges
- **Investment:** 3 risk levels (low/medium/high) with random returns
- **Skill:** 6 skill cards with practice questions and earning potential info

**Hybrid AI System:**
- Mock AI provider with interest-to-business mapping
- Template-based Roman Urdu pitches (ready for Groq API swap in Stage 6)
- Interest scoring and ranking algorithm
- Expected profit ranges (not exact values) — teaches uncertainty

**26 tests passing | Exit criterion met**

### ✅ Stage 5 — GIVE (Complete)
- 5 Alkhidmat-aligned cause categories (Education, Food, Health, Shelter, Water)
- Impact messages by amount range (notebook, ration, school bag, medical, major contribution)
- Animated impact celebration with particles
- Cumulative giving tracker (total donated, times given)
- Alkhidmat Foundation inspiration noted (no official claim)
- Ready for future real Alkhidmat API integration

**14 tests passing | Exit criterion met**

---

## Test Summary
| Category | Tests |
|----------|-------|
| Wallet & Goals | 17 |
| Spend | 10 |
| Grow (incl. AI) | 26 |
| Give | 14 |
| **Total** | **67 passing** |

---

## Pending Stages

### ⏳ Stage 6 — AI Mentor
- Mock provider (8-10 contextual Roman Urdu response templates)
- Groq API integration (free tier)
- POST /api/mentor endpoint with context from all 4 actions
- Chat-like UI with input box + response display
- **Exit criterion:** Ask mentor for advice, get contextual Roman Urdu response

---

## Known Issues & Future Improvements

### Engagement & Vibe (V1)
- [ ] Add mascot/character for personality
- [ ] Add animations and transitions between pages
- [ ] Gamification: badges, streaks, level-up system
- [ ] Sound effects for celebrations and actions
- [ ] More colorful, child-friendly UI
- [ ] Story/narrative thread connecting all actions

### Financial Concepts (V1)
- [ ] Assets vs Liabilities tracker on dashboard
- [ ] Net worth visualization
- [ ] Business "track record" — see which businesses worked/failed

### AI Enhancement (Stage 6+)
- [ ] Swap mock AI provider with Groq API
- [ ] Dynamic personalized business pitches
- [ ] Contextual mentor conversations

### Accessibility
- [ ] Roman Urdu is already accessible to Pakistani masses
- [ ] Future: Audio narration for non-readers
- [ ] Future: Pure Urdu script option

### Integration
- [ ] Real Alkhidmat Foundation donation API (post-V1)

---

## Files Created/Modified

### Backend
| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app + router registration |
| `backend/app/database.py` | SQLAlchemy engine + session |
| `backend/app/models.py` | 5 database models |
| `backend/app/services/wallet_service.py` | Core wallet operations |
| `backend/app/services/grow_service.py` | Business, investment, skill logic |
| `backend/app/services/ai_provider.py` | Mock AI for business recommendations |
| `backend/app/routes/session.py` | Child creation + session |
| `backend/app/routes/dashboard.py` | Dashboard data |
| `backend/app/routes/goals.py` | Goal CRUD + saving |
| `backend/app/routes/spend.py` | Spend scenarios + transactions |
| `backend/app/routes/grow.py` | Business, investment, skill endpoints |
| `backend/app/routes/give.py` | Give causes + donation |
| `backend/tests/test_wallet.py` | 17 wallet tests |
| `backend/tests/test_spend.py` | 10 spend tests |
| `backend/tests/test_grow.py` | 26 grow + AI tests |
| `backend/tests/test_give.py` | 14 give tests |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/App.jsx` | Routing (6 routes) |
| `frontend/src/services/api.js` | All API calls |
| `frontend/src/pages/Welcome.jsx` | Starting money + name |
| `frontend/src/pages/Dashboard.jsx` | Balance + 4 action buttons |
| `frontend/src/pages/Save.jsx` | Goal creation + saving |
| `frontend/src/pages/Spend.jsx` | Scenario cards + consequences |
| `frontend/src/pages/Grow.jsx` | Business + Investment + Skill tabs |
| `frontend/src/pages/Give.jsx` | Cause picker + impact celebration |
| `frontend/src/index.css` | All styles (~1300 lines) |

---

*Report generated August 31, 2026*
**Update (Sep 4):** Stage 6 (AI Mentor) complete. Added dashboard v2 (badges, mascot, net worth), Report Card + Certificate pages.
