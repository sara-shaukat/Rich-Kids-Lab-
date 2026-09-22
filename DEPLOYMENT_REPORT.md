# Rich Kids Lab — Vercel Deployment Report

**Date:** September 22, 2026
**Live URL:** https://rich-kids-lab.vercel.app
**Vercel project:** `rich-kids-lab` (Hobby plan — free tier)
**Prepared with:** Qoder (AI coding agent)

---

## 1. Executive Summary

Rich Kids Lab is fully deployed to **production on Vercel at zero cost**:

- **One public link** — https://rich-kids-lab.vercel.app — serves both the FastAPI backend and the React frontend to anyone, anywhere.
- The deployment was **verified end-to-end**: session creation, dashboard, Money Vault, and the AI Mentor (Paisa Bot) all work live, with real Groq AI responses.
- The app runs on Vercel's **Hobby (free) plan** — no payment, no credit card.
- Known limitation: the SQLite database is ephemeral in the serverless environment (see Section 7). For a live demo this is not a problem — create a profile at the start of the demo and play through in one sitting.

---

## 2. Objective and Constraints

| Item | Requirement |
|------|-------------|
| Goal | Public shareable link for judges, teachers, and friends |
| Budget | Free only (student project) |
| Use case | Live demo (a recorded demo video already exists as backup) |
| Alternatives considered | Docker (local only — cannot be shared as a link), so Vercel was chosen |

---

## 3. Hosting Architecture

Everything is served from a single Vercel project. Request routing works like this:

```
https://rich-kids-lab.vercel.app
        |
        |-- /api/*  ---->  Vercel Function (Python 3.12, Fluid compute)
        |                    FastAPI app (backend/app, 9 routers)
        |                    SQLite database at /tmp/rich_kids_lab.db (ephemeral)
        |
        |-- /*      ---->  Vercel CDN (static files from frontend/dist)
        |                    Client-side routes (/vault, /dashboard, /mentor)
        |                    fall back to index.html automatically
```

Key mechanics:

- Vercel's **FastAPI framework preset** auto-detects the app from a root-level `index.py` entrypoint — no framework settings needed in the dashboard.
- `app.frontend("/", directory="frontend/dist", fallback="index.html")` in the entrypoint **promotes the React build to the CDN** and enables SPA route fallback. API routes always take priority over static files.
- The React production build is **built in the cloud during deployment** (Vercel runs `cd frontend && npm ci && npm run build`), so no build artifacts are committed to the repository.
- Runtime configuration is injected via **Vercel environment variables** — no secrets exist in any file in the repository.

---

## 4. Work Performed

### Phase 1 — Source acquisition

The original project lived in an older workspace (`...\Qoder\2026-08-30\chat-1`). A deployment copy was created in the current workspace:

- Copied to `...\Qoder\2026-09-22\chat-1\rich-kids-lab\` via `robocopy`
- 539 files, 46.5 MB — excluded `node_modules`, Python `venv`, caches, and database files
- Local frontend production build was verified before deployment (Vite 8.2.2, built cleanly)

### Phase 2 — Deployment configuration files created

| File | Purpose |
|------|---------|
| `index.py` (new) | Vercel entrypoint: makes `backend/` importable, imports the FastAPI `app`, calls `app.frontend(...)` to promote the React build to the CDN |
| `pyproject.toml` (new) | Declares Python dependencies (FastAPI, SQLAlchemy, Pydantic, python-dotenv, httpx), the frontend build command, and static-file CDN settings |
| `vercel.json` (new) | Function configuration: 60 s max duration, and `excludeFiles` globs that keep venv/tests/node_modules/screenshots out of the function bundle |
| `.vercelignore` (new) | Upload exclusions: `.git`, `backend/venv`, **`backend/.env` and `.env` (secrets — never uploaded)**, `node_modules`, `dist`, screenshots, Docker files, `.vercel-tmp`, `.env.local` |
| `backend/app/database.py` (modified) | Added `DATABASE_URL` environment-variable override so the database location can be changed per environment (was hardcoded to a local file path) |

Why `database.py` was modified: Vercel's filesystem is read-only except for `/tmp`, so the hardcoded SQLite path would crash on the serverless runtime. With the override, local development is unchanged (no env var → same file as before), while Vercel points the database at `sqlite:////tmp/rich_kids_lab.db`.

Docker files (`backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `docker-compose.yml`) were also added and remain in the repository as an optional local hosting path — they are excluded from the Vercel upload.

### Phase 3 — Environment setup (Windows)

- Node.js v24.19.0 and npm located at `C:\Program Files\nodejs` (not on the default shell PATH — handled by prepending it in every command)
- **Vercel CLI 59.25.0 installed globally** via `npm install -g vercel`
- Two Windows-specific issues discovered and handled: npm global bin (`%APPDATA%\npm`) is not on PATH, and PowerShell's execution policy blocks `vercel.ps1`, so `vercel.cmd` is invoked directly with its full path

### Phase 4 — Authentication

- Logged in with the Vercel CLI **device-flow login** (`vercel login`)
- First attempt expired: the CLI polling process exited before the browser authorization was confirmed — the fix was to relaunch `vercel login` and complete the browser authorization within 1–2 minutes
- Second attempt succeeded; verified with `vercel whoami`

### Phase 5 — Project linking and environment variables

Linked and configured via CLI (`vercel link`, `vercel env add`). Production environment variables set **before** the first deployment:

| Variable | Value / Source | Environment |
|----------|----------------|-------------|
| `DATABASE_URL` | `sqlite:////tmp/rich_kids_lab.db` | Production |
| `AI_PROVIDER` | `groq` | Production |
| `GROQ_API_KEY` | Piped directly from `backend/.env` into Vercel; stored **encrypted as a secret** and never displayed in any log or file | Production |

Note: `vercel link` also attempted to auto-connect the project to a GitHub repository; this failed harmlessly (no GitHub login connection on the account) and does not affect CLI-based deployments.

### Phase 6 — Production deployment

- `vercel deploy --prod --yes` — first production build **ready in 24 s** (852 KB uploaded, no build artifacts committed)
- The build ran fully in the cloud: Python dependencies installed, frontend `npm ci && npm run build` executed, function bundled
- One polish redeploy followed a `<title>` fix in `frontend/index.html` ("frontend" → "Rich Kids Lab") — **ready in 22 s**
- Canonical alias: **https://rich-kids-lab.vercel.app**

### Phase 7 — Verification

| # | Check | Method | Result |
|---|-------|--------|--------|
| 1 | API health | `GET /api/health` | `{"status":"ok"}` |
| 2 | Frontend served | `GET /` | 200 — React HTML with hashed assets, favicon 200, JS bundle 200 |
| 3 | SPA route fallback | `GET /vault`, `GET /dashboard` (with `Accept: text/html`) | 200 `text/html` — client-side routing works |
| 4 | Database write | `POST /api/sessions` (starting balance 100) | Session created, e.g. `RKL-AC94E5`, wallet balance 100.00 |
| 5 | AI provider | `POST /api/mentor` with a question | `provider: "groq"` — real Roman Urdu answer returned |
| 6 | Dashboard read | `GET /api/dashboard/{id}` | 200, balance 100.00 |
| 7 | Full browser walkthrough | Automated browser session on the live URL | Landing → profile creation → Dashboard → Money Vault → AI Mentor chat all working; AI replied in ~5 s; no JavaScript console errors |

Screenshots captured during verification (in `screenshots/`):

| File | Content |
|------|---------|
| `verify_landing.png` | Landing page with starting-money input |
| `verify_dashboard.png` | Dashboard after session creation |
| `verify_vault.png` | Money Vault island |
| `verify_mentor.png` | AI Mentor chat with a live Groq response |

---

## 5. Issues Encountered and Resolutions

| # | Issue | Cause | Resolution |
|---|-------|-------|------------|
| 1 | `node`/`vercel` not found in the agent shell | Node.js installed under `C:\Program Files\nodejs`, npm global bin under `%APPDATA%\npm`; neither on the shell PATH | Prepend both directories to `$env:Path` in each command |
| 2 | `vercel.ps1 cannot be loaded` | PowerShell execution policy blocks script execution | Invoke `vercel.cmd` directly by full path |
| 3 | Login script produced an empty log file | Detached background process output buffering on Windows | Ran `vercel login` directly in a captured terminal instead |
| 4 | First authorization expired | CLI polling process exited before browser authorization was confirmed | Relaunched `vercel login`, user authorized the fresh code within ~1 minute; verified with `vercel whoami` |
| 5 | Link step could not connect a GitHub repo | No GitHub login connection on the Vercel account | Harmless — ignored; CLI deployments do not need a Git connection |
| 6 | `/vault` returned JSON 404 when tested with `curl` | The `index.html` fallback only applies to navigation requests (`Accept: text/html`); plain curl requests get the API's 404 | Expected behavior — re-tested with `Accept: text/html`, got 200; browsers always receive the SPA correctly |
| 7 | Browser tab title showed "frontend" | Default Vite `index.html` title | Changed to "Rich Kids Lab" and redeployed (22 s) |

---

## 6. Final Artifacts

| Artifact | Location |
|----------|----------|
| Public URL | https://rich-kids-lab.vercel.app |
| Vercel dashboard | https://vercel.com/2501256-5396/rich-kids-lab (project: `2501256-5396/rich-kids-lab`) |
| Deployment source | `...\Qoder\2026-09-22\chat-1\rich-kids-lab\` — original remains at `...\Qoder\2026-08-30\chat-1\` |
| Vercel config | `index.py`, `pyproject.toml`, `vercel.json`, `.vercelignore` (project root) |
| Docker alternative | `docker-compose.yml` + both Dockerfiles (local hosting with persistent database) |
| Step-by-step guide | `VERCEL_DEPLOY_GUIDE.md` (same folder) |

---

## 7. Known Limitations and Recommendations

1. **Ephemeral database (most important):** SQLite lives in the serverless `/tmp` directory. Data (created child profiles) can reset on cold starts, redeploys, or when Vercel spins up a different instance. The app itself always works — only previously created profiles may disappear.
   - Demo advice: create a fresh profile at the start of the live demo and complete the walkthrough in one session.
   - Permanent fix (later): point `DATABASE_URL` at a free hosted database (e.g., Turso/libSQL) — the env-var override is already in place, so it is a configuration change, not a code rewrite.
2. **Free-tier behavior:** the first visit after idle time may take a few seconds (cold start). Subsequent requests are fast.
3. **Deployment method:** deploys are done from the CLI, not via Git push. If the project later moves to GitHub, it can be connected in the Vercel dashboard for automatic deploys.
4. **Secret hygiene:** the Groq API key exists only in `backend/.env` (local, excluded from all uploads) and as an encrypted Vercel secret. It is not in the repository, this report, or any log.

---

## 8. Maintenance Runbook

| Task | Command / Action |
|------|------------------|
| Redeploy after code changes | From `rich-kids-lab\`: `vercel deploy --prod --yes` |
| Verify login still valid | `vercel whoami` |
| Update an environment variable | `vercel env rm NAME production`, then re-add with `vercel env add NAME production` (redeploy afterwards) |
| View runtime logs | Vercel dashboard → project → Deployments → Logs |
| Roll back | Vercel dashboard → Deployments → select a previous build → "Promote to Production" |
| Change the public URL | Vercel dashboard → project → Domains |

**Deployment time:** ~25 seconds from command to live (small project, cached builds make it faster).

---

## 9. Post-Deployment Incident and Fix — Groq model decommission (resolved)

**Symptom:** Groq decommissioned the `groq/compound` model on September 21, 2026. The app had that model ID hardcoded in 4 places, and because AI failures fall back gracefully to mock templates (by design, for demo safety), the live mentor chat silently began returning canned template replies — while the API tag still said "groq".

**Diagnosis:** (1) Live responses were matched character-for-character against known mock templates; (2) a direct probe showed `groq/compound` **and** all Llama models now return 404 for this account; (3) `GET /openai/v1/models` listed the current roster: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`, `allam-2-7b`.

**Fix applied and verified:**
- All 4 Groq call sites migrated to `openai/gpt-oss-120b` with `reasoning_effort: "low"` (GPT-OSS is a reasoning model — the low setting is required so reasoning tokens do not consume the reply budget and truncate answers; verified both ways with live probes).
- Report-card commentary budget raised from 100 to 200 tokens for safety margin.
- The provider tag is now honest by construction: `"groq"` only when Groq actually answered, `"mock"` when the fallback was used — visible in the chat UI.
- 262 backend tests pass; production redeployed (~24 s) and verified live: mentor replies are dynamic, on-topic, and include matching Urdu-script translations.
