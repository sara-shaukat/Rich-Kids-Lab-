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
