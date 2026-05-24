"""
Health check API for monitoring system status.

Checks connectivity to:
- PostgreSQL (database)
- Redis (task queue)
- LLM API (model endpoint)
"""
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from backend.db.session import AsyncSessionLocal

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    System health check endpoint.

    Returns status of all external dependencies:
    - database: PostgreSQL connection
    - redis: Redis connection
    - llm: LLM API reachability

    Returns:
        dict: Health status with component details
    """
    checks = {}
    overall_healthy = True

    # 1. Database check
    try:
        start = time.time()
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)[:200]}
        overall_healthy = False

    # 2. Redis check
    try:
        import redis.asyncio as aioredis

        start = time.time()
        r = aioredis.from_url(
            f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}",
            decode_responses=True,
        )
        await r.ping()
        await r.aclose()
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)[:200]}
        overall_healthy = False

    # 3. LLM API check
    try:
        base_url = os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1")
        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/models")
            model_count = 0
            if resp.status_code == 200:
                data = resp.json()
                model_count = len(data.get("data", []))

        checks["llm"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 1),
            "base_url": base_url,
            "models_available": model_count,
        }
    except Exception as e:
        checks["llm"] = {
            "status": "degraded",
            "error": str(e)[:200],
            "base_url": os.getenv("OPENAI_BASE_URL", ""),
        }
        # LLM being down is degraded, not fatal
        # overall_healthy still True — pipeline can queue but not execute

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "version": "1.0.0",
        "checks": checks,
    }
