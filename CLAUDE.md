# Autonomous AI Software Factory — CLAUDE.md

## Project Overview
This is an AI-powered software factory platform. Users input requirements, the system autonomously generates PRD, architecture, code, tests, and deploys.

## Stack
- Frontend: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- Backend: FastAPI (Python 3.11), PostgreSQL, Redis, ARQ task queue
- Orchestration: Custom Python orchestrator calling Claude Code via subprocess
- Testing: pytest, vitest, playwright

## Directory Structure
```
autonomous-ai-factory/
├── frontend/          # Next.js app
├── backend/           # FastAPI app
│   ├── api/           # Route handlers
│   ├── core/          # Orchestrator, planner, executor, tester, gatekeeper
│   ├── models/        # SQLAlchemy ORM models
│   ├── workers/       # ARQ async workers
│   ├── db/            # Alembic migrations
│   └── main.py
├── workspace/         # Generated project workspaces
├── docker-compose.yml
└── .env.example
```

## Key Commands
- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Tests: `cd backend && pytest` | `cd frontend && npm test`
- Lint: `cd backend && ruff check .` | `cd frontend && npm run lint`
- Docker: `docker compose up -d`

## Code Standards
- Python: type hints on all functions, ruff formatting
- TypeScript: strict mode, no any, functional components only
- API routes: prefix /api/v1/
- All DB operations through ORM
- Every Agent action MUST log to agent_runs table

## Critical Rules
1. Never hardcode secrets - use env vars only
2. All dangerous ops go through gatekeeper.py
3. All agent actions must be logged
4. Retry: max_retries from project config, default 3
5. WebSocket events use typed schemas
