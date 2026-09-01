# Skill Lab Makeover

## Inspection Summary

**Current state:** 3-step flat flow (grid -> explore text -> result text). No challenges, no progression, no business connection. 6 skill cards with free-text practice only.

**What is reused (no new tables):**
- `GrowActivity` (type="SKILL") — records challenge completion + details in JSON
- `explore_skill()` in `grow_service.py` — extended to handle challenge data
- Explorer badge, level system — already count SKILL activities
- `startBusiness` — existing business simulation linked from skill results

---

## 1. Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/grow_service.py` | Expand `SKILL_CARDS` with mini-challenges, discover/grow/connect content; replace Drawing with AI Prompt Engineering; extend `explore_skill()` to record challenge answers |
| `backend/app/routes/grow.py` | Expand `SkillCardResponse` + `SkillResultResponse` with new fields (challenge options, discover text, connect text, business suggestion) |
| `backend/tests/test_grow.py` | Update existing skill tests for new fields; add challenge completion tests |
| `frontend/src/pages/Grow.jsx` | Rewrite Skill tab with 4-step lab flow (pick -> discover -> challenge -> connect) |
| `frontend/src/index.css` | Add Skill Lab CSS styles |

## 2. No New Files Created

All changes fit within existing files. No new backend services or frontend components needed — the Skill Lab is entirely within the Grow.jsx Skill tab.

## 3. Proposed Skill Lab Flow (4 Steps)

```
Step 1: PICK        "Kon si cheez tumhein pasand hai?"
                    6 skill cards in a grid
                         |
Step 2: DISCOVER    "{skill} LAB — Let's experiment!"
                    What is this skill? (2-3 lines)
                    How to start? (bullet steps)
                    [START CHALLENGE] button
                         |
Step 3: CHALLENGE   Mini challenge with multiple-choice or structured input
                    Submit -> records activity
                         |
Step 4: CONNECT     "Challenge Complete!"
                    Financial literacy connection:
                    INTEREST -> SKILL -> PRACTICE -> POTENTIAL FUTURE VALUE
                    Disclaimer: "Income guaranteed nahi hoti..."
                    [TRY A BUSINESS] button (links to existing Business tab)
                    [TRY ANOTHER SKILL] [BACK TO GROW] [DASHBOARD]
                    Placeholder: "[LEARN MORE]" (disabled, for future resources)
```

## 4. Skill Cards (6 Skills — Drawing replaced with AI Prompt Engineering)

### Skill 1: AI Prompt Engineering (replaces Drawing)
- **Icon:** 🤖
- **Category:** tech
- **Discover:** "AI ko sahi sawal poochna ek skill hai! Achay prompts likhna seekho to AI se bohat kuch kar sakte ho."
- **Steps:** "Start with simple questions -> Learn to be specific -> Practice giving clear instructions"
- **Challenge (multiple choice):** "Tum AI se ek story likhwana chahte ho. Kon sa prompt best hai?"
  - A) "Story likho" (too vague)
  - B) "Ek 10-saal ke bachay ke liye adventure story likho jo space mein hoti hai, 3 paragraphs mein" (specific + clear)
  - C) "Best story ever" (too vague)
- **Connect:** "Future mein AI tools use karna ek valuable skill ho sakti hai. Achay prompts likhne se AI zyada useful hota hai."
- **Business link:** Suggests trying "Homework Helper" (uses teaching/planning skills)

### Skill 2: Coding
- **Icon:** 💻
- **Category:** tech
- **Discover:** "Coding seekho = apps banana seekho! Computer ko instructions dena ek superpower hai."
- **Challenge (ordering):** "Ek app banani hai jo user ka naam pooche aur greeting show kare. Steps ka sahi order kya hai?"
  - A) Display greeting -> Ask name -> Store name (wrong)
  - B) Ask name -> Store name -> Display greeting (correct)
  - C) Store name -> Display greeting -> Ask name (wrong)
- **Connect:** "Developers apps banate hain jo logon ki problems solve karti hain."
- **Business link:** Suggests trying "Sticker Shop" (design + tech skills)

### Skill 3: Writing
- **Icon:** ✍️
- **Category:** creative
- **Discover:** "Acha likhna ek superpower hai! Words se logon ko inspire, inform aur entertain kar sakte ho."
- **Challenge (text input + choice):** "Ek handmade bookmark ke liye 2-line description likho. Phir choose karo: kon si line customer ko attract karegi?"
  - A) "Ye bookmark hai." (boring)
  - B) "Apni kitaab ko ek special touch do — handmade bookmark jo har page ko memorable banaye!" (engaging)
- **Connect:** "Content writers, bloggers, aur storytellers apni writing skill se kaam karte hain."
- **Business link:** Suggests trying "Handmade Bookmarks"

### Skill 4: Photography
- **Icon:** 📸
- **Category:** art
- **Discover:** "Photo lena sirf click karna nahi hai — light, angle, aur composition samajhna hai!"
- **Challenge (multiple choice):** "Ek product ki photo leni hai. Kon si 3 cheezen sab se important hain?"
  - A) Good lighting + clean background + right angle (correct)
  - B) Expensive camera + filters + lots of photos (wrong)
  - C) Flash on + zoom in + close eyes (wrong)
- **Connect:** "Photography skill events, products, aur social media ke liye useful ho sakti hai."
- **Business link:** Suggests trying "Art Cards" (visual creativity)

### Skill 5: Video Editing
- **Icon:** 🎬
- **Category:** tech
- **Discover:** "Videos banana aur edit karna ek in-demand skill hai! Short videos ki demand bohat zyada hai."
- **Challenge (ordering):** "Ek 30-second short video banani hai. Editing ka sahi order kya hai?"
  - A) Add music -> Cut clips -> Record footage (wrong)
  - B) Record footage -> Cut best clips -> Add music + text (correct)
  - C) Upload -> Record -> Edit (wrong)
- **Connect:** "Video editors social media, events, aur content creation mein kaam karte hain."
- **Business link:** Suggests trying "Sticker Shop" (design skills transfer)

### Skill 6: Crafts
- **Icon:** ✂️
- **Category:** creative
- **Discover:** "Haath se banana ek valuable skill hai! Handmade products ki bohat demand hai."
- **Challenge (multiple choice):** "Ek handmade gift box banana hai. Pehle kya karna chahiye?"
  - A) Start gluing randomly (wrong)
  - B) Plan the design + gather materials + measure + then build (correct)
  - C) Buy the most expensive materials (wrong)
- **Connect:** "Crafters handmade items sell karte hain — online aur markets mein."
- **Business link:** Suggests trying "Handmade Bookmarks" or "Art Cards"

## 5. Skill -> Business Connection

After challenge completion, show a small card:
```
"Skill Lab ke baad ek experiment karna hai?"
[TRY A BUSINESS ->]
```
Clicking this switches to `activeTab='business'` and optionally pre-filters to a matching business. This reuses the existing Business Simulation entirely — no duplication.

The mapping is stored in each skill card as `linked_business_ids` (list of template IDs).

## 6. AI Mentor Integration

The AI Mentor is NOT yet implemented (Stage 6). The Skill Lab will be designed so that when the Mentor is built, it can:
- Read the child's completed skills from `GrowActivity` (type="SKILL")
- Know which challenges were completed and what answers were given
- Reference the skill in conversation

No Mentor code will be written now. The data architecture already supports this since GrowActivity records everything.

## 7. XP/Badge Integration

**Existing reuse:**
- Completing a skill challenge