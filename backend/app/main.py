"""Rich Kids Lab — FastAPI application entry point."""

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.models import Child, Wallet, Transaction, Goal, GrowActivity, VaultProgress  # noqa: ensure models are registered
from app.routes import session, dashboard, goals, spend, grow, give, quests, mentor, vault

# Load .env (AI_PROVIDER / GROQ_API_KEY) if present
load_dotenv()

# Create all tables on startup (no migrations needed for hackathon)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rich Kids Lab API", version="0.1.0")

# CORS — allow Vite dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(session.router)
app.include_router(dashboard.router)
app.include_router(goals.router)
app.include_router(spend.router)
app.include_router(grow.router)
app.include_router(give.router)
app.include_router(quests.router)
app.include_router(mentor.router)
app.include_router(vault.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
