"""
Project template system for the AI Factory.

Provides pre-configured project templates that enhance the planner's output
by injecting known-good boilerplate, dependencies, and architecture patterns.

Templates are applied during the planning stage to give the LLM executor
better context about desired project structure.
"""
from typing import Optional


# ─── Template Definitions ───────────────────────────────────────────────────

TEMPLATES: dict[str, dict] = {
    "python-cli": {
        "name": "Python CLI Tool",
        "description": "Command-line tool with Click/argparse, tests, and packaging",
        "tech_stack": "Python, Click, pytest",
        "suggested_structure": [
            "src/__init__.py",
            "src/main.py",
            "src/cli.py",
            "tests/__init__.py",
            "tests/test_main.py",
            "tests/conftest.py",
            "pyproject.toml",
            "requirements.txt",
            "README.md",
        ],
        "boilerplate_prompt": (
            "Create a well-structured Python CLI tool using Click for argument parsing. "
            "Include proper entry point in pyproject.toml, comprehensive pytest tests, "
            "and a helpful --help output. Use type hints throughout. "
            "Follow src layout (src/ package with __init__.py)."
        ),
    },
    "python-api": {
        "name": "Python REST API",
        "description": "FastAPI REST API with SQLAlchemy, Pydantic schemas, and tests",
        "tech_stack": "Python, FastAPI, SQLAlchemy, Pydantic, pytest",
        "suggested_structure": [
            "app/__init__.py",
            "app/main.py",
            "app/models.py",
            "app/schemas.py",
            "app/routes.py",
            "app/database.py",
            "tests/__init__.py",
            "tests/test_routes.py",
            "tests/conftest.py",
            "requirements.txt",
            "README.md",
        ],
        "boilerplate_prompt": (
            "Create a FastAPI REST API with SQLAlchemy ORM models, Pydantic schemas, "
            "proper CRUD routes, error handling, and async database operations. "
            "Include comprehensive pytest tests with httpx AsyncClient. "
            "Use SQLite for simplicity (easy to swap to PostgreSQL)."
        ),
    },
    "node-api": {
        "name": "Node.js Express API",
        "description": "Express.js REST API with TypeScript and Jest tests",
        "tech_stack": "Node.js, Express, TypeScript, Jest",
        "suggested_structure": [
            "src/index.ts",
            "src/routes/index.ts",
            "src/middleware/errorHandler.ts",
            "src/types/index.ts",
            "tests/routes.test.ts",
            "package.json",
            "tsconfig.json",
            "README.md",
        ],
        "boilerplate_prompt": (
            "Create an Express.js REST API in TypeScript with proper middleware, "
            "error handling, route separation, and Jest tests. "
            "Include tsconfig.json with strict mode, scripts for dev/build/test. "
            "Use zod for input validation."
        ),
    },
    "react-app": {
        "name": "React Web Application",
        "description": "React SPA with TypeScript, Vite, and component tests",
        "tech_stack": "React, TypeScript, Vite, Tailwind CSS",
        "suggested_structure": [
            "src/main.tsx",
            "src/App.tsx",
            "src/components/Layout.tsx",
            "src/pages/Home.tsx",
            "src/hooks/useApi.ts",
            "src/types/index.ts",
            "tests/App.test.tsx",
            "index.html",
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "tailwind.config.ts",
            "README.md",
        ],
        "boilerplate_prompt": (
            "Create a React SPA with Vite, TypeScript strict mode, Tailwind CSS, "
            "React Router for navigation, and component-based architecture. "
            "Include Vitest for testing and a clean project structure."
        ),
    },
    "go-api": {
        "name": "Go REST API",
        "description": "Go HTTP API with chi router and standard library",
        "tech_stack": "Go, chi, standard library",
        "suggested_structure": [
            "main.go",
            "handlers/handlers.go",
            "models/models.go",
            "middleware/middleware.go",
            "handlers/handlers_test.go",
            "go.mod",
            "README.md",
        ],
        "boilerplate_prompt": (
            "Create a Go REST API using chi router with proper handler separation, "
            "middleware (logging, CORS), structured JSON responses, and table-driven tests. "
            "Use Go modules. Keep it idiomatic Go — no unnecessary abstractions."
        ),
    },
    "fullstack": {
        "name": "Fullstack Web App",
        "description": "Next.js frontend + FastAPI backend with shared types",
        "tech_stack": "Next.js, TypeScript, FastAPI, Python, Tailwind CSS",
        "suggested_structure": [
            "frontend/src/app/page.tsx",
            "frontend/src/app/layout.tsx",
            "frontend/src/lib/api.ts",
            "frontend/package.json",
            "frontend/tsconfig.json",
            "backend/app/main.py",
            "backend/app/routes.py",
            "backend/app/models.py",
            "backend/requirements.txt",
            "backend/tests/test_routes.py",
            "README.md",
            "docker-compose.yml",
        ],
        "boilerplate_prompt": (
            "Create a fullstack application with Next.js (App Router) frontend "
            "and FastAPI backend. Frontend uses Tailwind CSS and fetches from the API. "
            "Backend provides RESTful endpoints with proper CORS. "
            "Include docker-compose.yml for easy deployment."
        ),
    },
}


def get_template(template_key: str) -> Optional[dict]:
    """
    Get a template by key.
    
    Args:
        template_key: Template identifier (e.g., "python-cli", "react-app")
        
    Returns:
        dict: Template data, or None if not found
    """
    return TEMPLATES.get(template_key)


def list_templates() -> list[dict]:
    """
    List all available templates with their metadata.
    
    Returns:
        list: List of template summaries
    """
    return [
        {
            "key": key,
            "name": t["name"],
            "description": t["description"],
            "tech_stack": t["tech_stack"],
        }
        for key, t in TEMPLATES.items()
    ]


def get_template_prompt(template_key: str) -> str:
    """
    Get the boilerplate prompt for a template.
    
    This is injected into the executor's LLM prompt to guide code generation.
    
    Args:
        template_key: Template identifier
        
    Returns:
        str: Template-specific prompt text, or empty string if template not found
    """
    template = TEMPLATES.get(template_key)
    if not template:
        return ""

    structure = "\n".join(f"  - {f}" for f in template["suggested_structure"])
    return (
        f"\n## Project Template: {template['name']}\n"
        f"Tech stack: {template['tech_stack']}\n\n"
        f"{template['boilerplate_prompt']}\n\n"
        f"Suggested file structure:\n{structure}\n"
    )
