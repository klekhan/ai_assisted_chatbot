"""
Minimal shared-secret auth. The frontend sends the key in the
'X-API-Key' header. This is enough to keep your free-tier deployment from
being spammed by strangers — for real multi-user auth later, swap this
for JWT / OAuth without touching the RAG logic.
"""
from fastapi import Header, HTTPException, status
from app.config import settings


def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
