from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import admin, chat
from app.services import feedback_store, vectorstore

app = FastAPI(
    title="Knowledge Assistant API",
    description="Ask questions grounded in an admin-managed knowledge base.",
    version="2.0.0",
)


@app.on_event("startup")
async def on_startup():
    feedback_store.init_db()
    vectorstore.ensure_collection()
    vectorstore.ensure_verified_collection()


@app.on_event("shutdown")
async def on_shutdown():
    # Closes the Postgres connection pool cleanly. Matters more than it
    # would for a local file: Supabase's free tier caps total connections,
    # and Render restarts this process often (redeploys, spin-down/wake).
    # Leaving connections open on every restart would eat into that cap.
    feedback_store.close_pool()

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
