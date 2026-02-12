from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

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
