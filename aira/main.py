"""AIRA module: main.py"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from agents.signal_hunter.scheduler import start_scheduler, stop_scheduler
from core.gemini_client import init_gemini_client
from core.supabase_client import init_supabase
from orchestrator.agent_registry import register_all_agents
from orchestrator.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("aira")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AIRA starting up...")
    init_supabase()
    init_gemini_client()

    orchestrator = Orchestrator()
    logger.info("Registering agents...")
    register_all_agents(orchestrator)
    logger.info("All agents registered")

    app.state.orchestrator = orchestrator
    start_scheduler(app)
    logger.info("AIRA ready")
    try:
        yield
    finally:
        stop_scheduler(app)


app = FastAPI(title="AIRA API", version=os.getenv("APP_VERSION", "1.0.0"), lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "AIRA backend is running",
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(api_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
