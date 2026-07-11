from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, chat

app = FastAPI(
    title="Knowledge Assistant API",
    description="Ask questions grounded in an admin-managed knowledge base.",
    version="2.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/topics")
async def topics():
    """Public, unauthenticated — just the suggested-topics list shown on
    the empty-state chat screen. No knowledge base content, no auth needed."""
    return {"topics": [t.strip() for t in settings.kb_topics.split(",") if t.strip()]}
