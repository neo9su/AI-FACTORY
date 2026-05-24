"""
Workspace file API — browse and preview generated code files.
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

WORKSPACE_ROOT = Path("./workspace")


@router.get("/projects/{project_id}/files")
async def list_project_files(project_id: str) -> list[dict[str, Any]]:
    """
    List all files in the project workspace.

    Returns a tree of files with metadata (size, path).
    """
    workspace = WORKSPACE_ROOT / project_id

    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Project workspace not found")

    # Skip hidden/cache dirs
    skip_dirs = {
        "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
        "node_modules", ".next", "dist", "build", ".git", "venv", ".venv",
    }

    files = []
    for file_path in sorted(workspace.rglob("*")):
        if not file_path.is_file():
            continue

        # Skip files in hidden/cache directories
        rel_path = file_path.relative_to(workspace)
        parts = rel_path.parts
        if any(part in skip_dirs for part in parts):
            continue

        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0

        files.append({
            "path": str(rel_path),
            "size": size,
            "extension": file_path.suffix,
        })

    return files


@router.get("/projects/{project_id}/files/{file_path:path}")
async def get_project_file(project_id: str, file_path: str) -> dict[str, Any]:
    """
    Get content of a specific file in the project workspace.

    Returns file content with metadata.
    """
    workspace = WORKSPACE_ROOT / project_id
    full_path = workspace / file_path

    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Project workspace not found")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    # Security: ensure path is within workspace (prevent path traversal)
    try:
        full_path.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

    # Check file size (don't serve files > 1MB)
    size = full_path.stat().st_size
    if size > 1_000_000:
        raise HTTPException(status_code=413, detail="File too large to preview (>1MB)")

    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Binary file cannot be previewed")

    return {
        "path": file_path,
        "content": content,
        "size": size,
        "extension": full_path.suffix,
        "lines": content.count("\n") + 1,
    }
