from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import analysis, benchmarks, health, queries, recommendations
from scripts.init_db import init_both

logger = logging.getLogger("optimizer")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        stats = init_both()
        logger.info("Database ready: %s", stats)
    except Exception as exc:
        logger.warning("Database init skipped/failed: %s", exc)
    yield


app = FastAPI(
    title="AI-Powered PostgreSQL Performance Optimizer",
    description="Privacy-preserving query optimization with sandbox validation.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(queries.router)
app.include_router(analysis.router)
app.include_router(recommendations.router)
app.include_router(benchmarks.router)
