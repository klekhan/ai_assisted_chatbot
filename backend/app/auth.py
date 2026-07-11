"""
Two separate shared-secret gates:

- require_api_key: used by the public /chat endpoint. This key is baked
  into the public frontend's build, so it is NOT a real secret — it only
  stops casual bots/scrapers from hammering your Groq/Qdrant free-tier quota.

- require_admin_key: used by every /admin/* endpoint (upload, delete,
  debug retrieval). This key is NEVER included in the frontend build — the
  admin types it in at the /admin login screen each session, so it never
  ships inside public JavaScript.

For real multi-user auth later, swap these for JWT / OAuth without
touching the RAG logic itself.
"""
from fastapi import Header, HTTPException, status
from app.config import settings


def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != settings.admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")
