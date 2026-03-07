from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import auth, exams, tests, questions, analytics, blueprints, pyq_papers
from app.core.config import settings
from app.core.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB connection
    await init_db()
    yield
    # Shutdown: Close MongoDB connection
    await close_db()


app = FastAPI(
    title="MockMitra API",
    description="AI-powered CBT Mock Test Generator for Indian Competitive Exams",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.CORS_ALLOW_ALL else settings.BACKEND_CORS_ORIGINS,
    allow_credentials=not settings.CORS_ALLOW_ALL,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Mount static files for images/diagrams
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(exams.router, prefix="/api/exams", tags=["Exams"])
app.include_router(tests.router, prefix="/api/tests", tags=["Tests"])
app.include_router(questions.router, prefix="/api/questions", tags=["Questions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(blueprints.router, prefix="/api/blueprints", tags=["Blueprints"])
app.include_router(pyq_papers.router, prefix="/api/pyq", tags=["PYQ Papers"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to MockMitra API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
