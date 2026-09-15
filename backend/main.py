import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import admin, auth, classes, ingest, chat, materias
from services.auth_service import ensure_admins_approved
from services.db import init_db

logging.basicConfig(level=logging.INFO)

# Ensure API keys are available as environment variables for libraries that read them directly
os.environ["OPENAI_API_KEY"] = settings.openai_api_key
os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    ensure_admins_approved()
    if not settings.admin_emails:
        logging.warning("ADMIN_EMAILS is empty: nobody can approve access requests.")
    yield


app = FastAPI(title="Knowly API", lifespan=lifespan)

# Auth uses Bearer tokens (not cookies), so credentials are not needed for CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(materias.router, prefix="/materias", tags=["materias"])
app.include_router(classes.router, prefix="/classes", tags=["classes"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
