# Deploying a FastAPI + React App to Vercel — Step-by-Step Guide

This guide documents exactly how Rich Kids Lab (FastAPI backend + React/Vite frontend) was deployed to Vercel's **free Hobby plan** as a single public URL, with the frontend built in the cloud during deployment. Follow the steps in order for a fresh deployment or to reproduce this setup for a similar project.

**Result:** one URL (e.g. https://rich-kids-lab.vercel.app) serving:
- `/api/*` → FastAPI app running as a Vercel serverless function
- `/*` → React static build on Vercel's CDN, with SPA route fallback

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Node.js 20+ and npm | Needed for the Vercel CLI and the frontend build |
| A Vercel account | Free — sign up with GitHub, Google, or email at https://vercel.com |
| Project layout | FastAPI app in a `backend/` folder, React/Vite app in a `frontend/` folder |
| `frontend/package-lock.json` | Required — the cloud build uses `npm ci` |

Expected layout (Rich Kids Lab):

```
rich-kids-lab/
├── index.py               <- Vercel entrypoint (created in Step 3)
├── pyproject.toml         <- Python deps + build command (Step 4)
├── vercel.json            <- Function settings (Step 5)
├── .vercelignore          <- Upload exclusions (Step 6)
├── backend/
│   ├── app/
│   │   ├── main.py        <- FastAPI `app` instance
│   │   ├── database.py
│   │   └── routes/...
│   └── .env               <- local secrets (NEVER uploaded)
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js     <- dev proxy /api -> localhost:8000
    └── src/...
```

---

## Step 1 — Install the Vercel CLI

```bash
npm install -g vercel
vercel --version
```

**Windows notes:**
- If `vercel` is "not recognized", add the npm global bin folder to PATH for the session:
  ```powershell
  $env:Path = "C:\Program Files\nodejs;$env:APPDATA\npm;$env:Path"
  ```
- If you get `vercel.ps1 cannot be loaded because running scripts is disabled`, invoke the `.cmd` shim instead of the `.ps1`:
  ```powershell
  & "$env:APPDATA\npm\vercel.cmd" --version
  ```
  For a permanent fix, run PowerShell as your user and execute `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

---

## Step 2 — Log in

```bash
vercel login
```

The CLI switches to a **device-code flow**: it prints a URL like `https://vercel.com/oauth/device?user_code=XXXX-XXXX` and waits for you to authorize it in the browser.

**Important timing rule:** the code is short-lived and the CLI process stops polling after a while. Complete the browser authorization **within 1–2 minutes** of the URL appearing, or the login silently fails (you will see "Logged out" on the next command). If that happens, just rerun `vercel login` and use the fresh code — old codes cannot be reused.

Verify the login:

```bash
vercel whoami
```

It should print your account id/username.

---

## Step 3 — Create the Vercel entrypoint (`index.py`)

Vercel's FastAPI preset auto-detects a root-level `index.py`. This file wires the backend into the function and promotes the React build to the CDN:

```python
"""Vercel entrypoint — Rich Kids Lab.

Serves the FastAPI backend (backend/app) as a Vercel Function and promotes the
built React frontend (frontend/dist) to the CDN. API routes win over static
files; client-side routes fall back to index.html.
"""
import os
import sys

# Make the backend package importable (backend/app/...)
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, BACKEND_DIR)

from app.main import app  # noqa: E402

# Promote the production frontend build to the CDN and serve index.html for
# client-side navigation routes like /vault or /dashboard.
app.frontend("/", directory="frontend/dist", fallback="index.html")
```

Key points:
- `sys.path.insert(0, BACKEND_DIR)` is what allows `from app.main import app` — inside `backend/app/*.py` the imports are absolute (`from app.database import ...`), so the `backend/` folder itself must be on `sys.path`.
- `app.frontend(...)` makes Vercel serve `frontend/dist` from the CDN. API routes always win over static files. `fallback="index.html"` serves the SPA shell for client-side navigation routes (see Step 11 for a testing gotcha).

---

## Step 4 — Configure `pyproject.toml`

At the project root, declare Python dependencies, the frontend build command, and the static CDN settings:

```toml
[project]
name = "rich-kids-lab"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "python-dotenv",
    "httpx",
]

# Vercel build: install + build the React frontend before deployment
[tool.vercel.scripts]
build = "cd frontend && npm ci && npm run build"

# Serve the promoted frontend from the CDN (bypasses the function)
[tool.vercel.fastapi.static]
cdn = true
exclude = true
```

Why each piece matters:
- `[project] dependencies` — Vercel installs these during the cloud build. **Do not list `uvicorn`** — the serverless runtime provides its own ASGI server.
- `[tool.vercel.scripts] build` — becomes the Vercel "Build Command". Runs on every deployment, before the function is bundled, so `frontend/dist` exists when the static promotion happens.
- `[tool.vercel.fastapi.static] cdn = true` — **required when the FastAPI app has top-level middleware** (e.g. `CORSMiddleware`). Without it, Vercel keeps static files inside the function instead of the CDN. `exclude = true` removes the static folder from the function bundle to keep it small.

---

## Step 5 — Configure `vercel.json`

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "index.py": {
      "maxDuration": 60,
      "excludeFiles": "{backend/venv/**,backend/tests/**,backend/*.db,frontend/node_modules/**,frontend/src/**,frontend/public/**,screenshots/**,.vercel-tmp/**,**/__pycache__/**,**/*.md,docker-compose.yml}"
    }
  }
}
```

Notes:
- The `functions` key is keyed by the **resolved entrypoint** (`index.py`).
- `maxDuration: 60` — 60-second function timeout (Hobby plan allows up to 60 s). Useful for AI calls.
- `excludeFiles` keeps venv, tests, docs, and build tooling out of the deployed function bundle. It does not affect what is served from the CDN.

---

## Step 6 — Configure `.vercelignore`

Controls which files are uploaded to Vercel at all:

```
.git
backend/venv
backend/.venv
backend/.env
.env
backend/rich_kids_lab.db
backend/__pycache__
backend/.pytest_cache
frontend/node_modules
frontend/dist
screenshots
.vercel-tmp
docker-compose.yml
.env.local
```

**Critical:** exclude every `.env` file. Secrets must never be uploaded — they are provided by Vercel environment variables instead (Step 9). Note that `frontend/dist` is ignored because Vercel builds it in the cloud; `frontend/node_modules` is ignored because Vercel runs `npm ci` itself.

---

## Step 7 — Make the database path configurable

Serverless filesystems are **read-only except `/tmp`**. A hardcoded SQLite path (or any hardcoded file path) will crash in production. Add an environment-variable override:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database file lives next to the backend/ folder root.
# Override with the DATABASE_URL env var (e.g. Docker: sqlite:////data/rich_kids_lab.db)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'rich_kids_lab.db')}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific: allow multi-thread access
)
```

Local development is unchanged when the env var is unset. In production, `DATABASE_URL` points at `/tmp` (see Step 9).

---

## Step 8 — Link the project

From the project root:

```bash
vercel link --yes
```

What happens:
- Creates a Vercel project (named after the folder) and writes `.vercel/project.json`.
- Auto-detects the framework: you should see `Detected FastAPI (Output Directory: N/A)`.
- It may try to auto-connect a matching GitHub repository. If the account has no GitHub connection, this prints an error — **it is harmless**, CLI deployments do not need it.
- It creates a `.env.local` file containing a short-lived `VERCEL_OIDC_TOKEN` — make sure `.env.local` is in your `.vercelignore`.

---

## Step 9 — Add production environment variables

Run these **before the first deployment** (environment changes take effect on the next build/run):

```bash
"sqlite:////tmp/rich_kids_lab.db" | vercel env add DATABASE_URL production
"groq" | vercel env add AI_PROVIDER production
```

Example — pipe a secret from a local env file without ever displaying it (works in PowerShell and bash):

```bash
key=$(grep '^GROQ_API_KEY=' backend/.env | cut -d= -f2) && echo "$key" | vercel env add GROQ_API_KEY production
```

PowerShell version:

```powershell
$k = (Select-String -Path "backend\.env" -Pattern '^GROQ_API_KEY=(.+)$').Matches[0].Groups[1].Value.Trim()
$k | & "$env:APPDATA\npm\vercel.cmd" env add GROQ_API_KEY production
```

Notes:
- `vercel env add NAME production` reads the value from **stdin** and automatically strips the trailing newline. The value is never echoed if you pipe it from a file.
- Values are stored as **Secret** type by default — hidden in the dashboard and unavailable to `vercel env pull` (use `--type config` for non-sensitive values you want readable later).
- Verify names (not values) with `vercel env ls production`.

---

## Step 10 — Deploy to production

```bash
vercel deploy --prod --yes
```

Expected flow (first deployment of this project took ~24 s total):
1. Upload of the source (852 KB for this project — small because `.vercelignore` excluded node_modules/venv/dist).
2. Cloud build: Python dependencies installed, then the custom build command `cd frontend && npm ci && npm run build` runs, then the function is bundled.
3. Output ends with:
   ```
   Inspect         https://vercel.com/<account>/<project>/<deployment>
   Production      https://<project>-<hash>-<account>.vercel.app
   Aliased         https://<project>.vercel.app
   ✓ Ready in 24s
   ```

The **alias URL** (`https://<project>.vercel.app`) is the stable public link — it keeps pointing at the latest production deployment, so it never changes when you redeploy.

---

## Step 11 — Verify the deployment

**1. API health:**

```bash
curl https://<project>.vercel.app/api/health
# {"status":"ok"}
```

**2. Frontend HTML and assets:**

```bash
curl https://<project>.vercel.app/
# 200 — HTML with hashed asset links; check the JS/CSS files return 200 too
```

**3. SPA route fallback (testing gotcha):** client-side routes such as `/vault` only fall back to `index.html` for **navigation requests** — requests that send `Accept: text/html`. Plain `curl` does not, and would show the API's JSON `404`, which is *expected*, not a bug:

```bash
curl -H "Accept: text/html" https://<project>.vercel.app/vault
# HTTP/1.1 200 OK, Content-Type: text/html
```

**4. End-to-end API check (database + AI):** create a session, then ask the mentor:

```bash
curl -X POST https://<project>.vercel.app/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"starting_balance":100}'
# {"anonymous_id":"RKL-XXXXXX","wallet":{"balance":"100.00"},"active_goal":null}

curl -X POST https://<project>.vercel.app/api/mentor \
  -H "Content-Type: application/json" \
  -d '{"anonymous_id":"RKL-XXXXXX","message":"Mera pehla din hai, kya karun?"}'
# {"response":"...","response_urdu":"...","provider":"groq"}
```

If `provider` is `"groq"` (not `"mock"`), the AI API key reached production correctly.

**5. Browser walkthrough:** open the alias URL and click through the app (landing → profile creation → dashboard → sections → AI chat), checking the browser console for errors.

---

## Updating a live deployment

| Task | Command |
|------|---------|
| Redeploy current code | `vercel deploy --prod --yes` (from the project root) |
| Preview a change without touching production | `vercel deploy` (creates a preview URL) |
| Change an env var | `vercel env rm NAME production` then re-add, then redeploy |
| Roll back | Vercel dashboard → Deployments → previous build → "Promote to Production" |

The public alias URL never changes on redeploy.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `vercel` not recognized | npm global bin not on PATH | Prepend `%APPDATA%\npm` (Windows) or `~/.npm-global/bin` to PATH |
| `vercel.ps1 cannot be loaded` (Windows) | PowerShell execution policy | Use `vercel.cmd` directly, or `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `whoami` says "Logged out" right after authorizing | Device code expired before authorization (CLI stopped polling) | Rerun `vercel login`, authorize the fresh code within 1–2 minutes |
| Build fails: `npm ci can only install with an existing package-lock.json` | Lockfile missing | Run `npm install` once in `frontend/` and commit the generated `package-lock.json` |
| Static files not on the CDN (`x-vercel-cache: MISS` persistently) | App has top-level middleware (e.g. CORS) | Set `cdn = true` under `[tool.vercel.fastapi.static]` |
| Client route works in browser but 404s in curl | Fallback applies to navigation requests only | Test with `-H "Accept: text/html"` — browser behavior is correct |
| `ModuleNotFoundError: No module named 'app'` in the function | `backend/` not on `sys.path` | Keep the `sys.path.insert(0, BACKEND_DIR)` line in `index.py` |
| App crashes on startup: read-only file system | Hardcoded file/database path | Use a `DATABASE_URL`-style env override pointing at `/tmp` |
| Secrets accidentally uploaded | `.env` not in `.vercelignore` | Add it, rotate the key, redeploy |

---

## Serverless database reality check

SQLite works on Vercel but lives in `/tmp`, which is **per-instance and ephemeral**: data can reset on cold starts, redeploys, or when traffic is routed to a different instance. This is acceptable for demos and prototypes. For durable storage, keep the same code and point `DATABASE_URL` at a free hosted database (e.g. Turso/libSQL) — the override pattern in Step 7 means it is a configuration change, not a rewrite.

---

## Command quick reference

```bash
npm install -g vercel                 # install CLI
vercel login                          # device-flow login (authorize within 1-2 min)
vercel whoami                         # verify login
vercel link --yes                     # create + link the project
echo "value" | vercel env add NAME production   # add env var (before deploying)
vercel env ls production              # list env var names
vercel deploy --prod --yes            # production deployment
vercel deploy                         # preview deployment
vercel logs <deployment-url>          # runtime logs
```
