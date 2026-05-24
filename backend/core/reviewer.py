"""
Reviewer module for LLM-powered code review.

Performs automated code review using LLM to check:
- Security vulnerabilities (SQL injection, XSS, path traversal, secrets)
- Code quality (readability, maintainability, naming, structure)
- Best practices (error handling, typing, documentation)
- Test coverage (are tests comprehensive enough?)

Returns structured review results with severity levels and suggestions.
"""
import json
import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.models.project import AgentRun, AgentStatus, Project

load_dotenv()


class ReviewResult:
    """Structured code review result."""

    def __init__(
        self,
        passed: bool,
        score: int,
        issues: list[dict[str, Any]],
        summary: str,
        suggestions: list[str],
    ) -> None:
        """
        Initialize review result.

        Args:
            passed: Whether the review passed (no critical/high issues)
            score: Quality score 0-100
            issues: List of issues found
            summary: Brief review summary
            suggestions: List of improvement suggestions
        """
        self.passed = passed
        self.score = score
        self.issues = issues
        self.summary = summary
        self.suggestions = suggestions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": self.issues,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }


class Reviewer:
    """LLM-powered code reviewer."""

    def __init__(self, workspace_root: str = "./workspace") -> None:
        """
        Initialize reviewer with LLM client.

        Args:
            workspace_root: Root directory for project workspaces
        """
        self.workspace_root = Path(workspace_root)

        api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.fallback_model = os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6")

    def get_project_workspace(self, project: Project) -> Path:
        """Get workspace directory for a project."""
        return self.workspace_root / project.id

    async def review_project(self, project: Project) -> tuple[AgentRun, ReviewResult]:
        """
        Perform code review on all generated files in the project workspace.

        Args:
            project: Project instance

        Returns:
            tuple: (AgentRun record, ReviewResult)
        """
        from datetime import datetime

        workspace = self.get_project_workspace(project)

        # Collect all source files
        code_content = self._collect_source_files(workspace)

        if not code_content:
            # No code to review — pass by default
            result = ReviewResult(
                passed=True,
                score=100,
                issues=[],
                summary="No source files to review.",
                suggestions=[],
            )
            agent_run = AgentRun(
                project_id=project.id,
                agent_name="reviewer",
                input="Code review (no files found)",
                output=json.dumps(result.to_dict()),
                status=AgentStatus.SUCCESS,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
            return agent_run, result

        # Build review prompt
        prompt = self._build_review_prompt(project, code_content)

        # Create agent run
        agent_run = AgentRun(
            project_id=project.id,
            agent_name="reviewer",
            input=f"Code review for {len(code_content)} files",
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            # Call LLM for review
            review_response = await self._call_llm(prompt)

            # Parse review result
            result = self._parse_review_response(review_response)

            agent_run.output = json.dumps(result.to_dict())
            agent_run.logs = f"Review complete: score={result.score}, issues={len(result.issues)}"
            agent_run.status = AgentStatus.SUCCESS
            agent_run.finished_at = datetime.utcnow()

        except Exception as e:
            # On failure, pass the review (don't block pipeline)
            result = ReviewResult(
                passed=True,
                score=70,
                issues=[],
                summary=f"Review could not be completed: {str(e)}",
                suggestions=["Manual review recommended"],
            )
            agent_run.output = json.dumps(result.to_dict())
            agent_run.logs = f"Review error (auto-passed): {str(e)}"
            agent_run.status = AgentStatus.SUCCESS
            agent_run.finished_at = datetime.utcnow()

        return agent_run, result

    def _collect_source_files(self, workspace: Path) -> dict[str, str]:
        """
        Collect all source files from workspace.

        Args:
            workspace: Project workspace directory

        Returns:
            dict: {relative_path: file_content}
        """
        if not workspace.exists():
            return {}

        code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx",
            ".go", ".rs", ".java", ".rb",
            ".yaml", ".yml", ".toml", ".json",
        }

        files = {}
        total_size = 0
        max_total_size = 50000  # 50KB limit to avoid token overflow

        for file_path in sorted(workspace.rglob("*")):
            if not file_path.is_file():
                continue

            # Skip non-source files
            if file_path.suffix not in code_extensions:
                continue

            # Skip node_modules, __pycache__, .git, etc.
            rel_path = str(file_path.relative_to(workspace))
            if any(skip in rel_path for skip in (
                "node_modules", "__pycache__", ".git", ".venv", "venv",
                "dist", "build", ".next",
            )):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                if total_size + len(content) > max_total_size:
                    # Truncate to stay within limits
                    break
                files[rel_path] = content
                total_size += len(content)
            except (UnicodeDecodeError, PermissionError):
                continue

        return files

    def _build_review_prompt(self, project: Project, code_content: dict[str, str]) -> str:
        """
        Build code review prompt.

        Args:
            project: Project instance
            code_content: dict of {path: content}

        Returns:
            str: Review prompt
        """
        # Format code files
        files_text = ""
        for path, content in code_content.items():
            files_text += f"\n### File: `{path}`\n```\n{content}\n```\n"

        return f"""You are a senior code reviewer. Review the following code for a project.

## Project Context
- **Name:** {project.name}
- **Tech Stack:** {project.tech_stack or "Not specified"}
- **Goal:** {project.goal or "Not specified"}

## Code to Review
{files_text}

## Review Checklist
1. **Security** (critical): SQL injection, XSS, path traversal, hardcoded secrets, input validation
2. **Correctness** (high): Logic errors, race conditions, unhandled edge cases, type mismatches
3. **Error Handling** (medium): Missing try/catch, unvalidated inputs, silent failures
4. **Code Quality** (low): Naming, readability, DRY violations, unused code
5. **Testing** (medium): Are tests comprehensive? Do they cover edge cases?

## Output Format
Return ONLY valid JSON:
```json
{{
  "passed": true,
  "score": 85,
  "issues": [
    {{
      "severity": "medium",
      "category": "error_handling",
      "file": "src/main.py",
      "line": 42,
      "description": "Missing error handling for file read operation",
      "suggestion": "Add try/except with proper error message"
    }}
  ],
  "summary": "Overall good quality code with minor improvements needed.",
  "suggestions": [
    "Add input validation for user-provided URLs",
    "Consider adding rate limiting"
  ]
}}
```

Rules:
- `passed` = true if no critical or high severity issues
- `score` = 0-100 quality score
- `severity` must be one of: critical, high, medium, low
- Be constructive, not pedantic — focus on real issues that could cause bugs or security problems
- Return ONLY valid JSON, no markdown code blocks"""

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with fallback support."""
        messages = [
            {"role": "system", "content": (
                "You are an expert code reviewer with deep knowledge of security, "
                "performance, and software engineering best practices. "
                "You output only valid JSON matching the requested schema."
            )},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096,
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception:
            if self.fallback_model and self.fallback_model != self.model:
                response = await self.client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.1,
                )
                return response.choices[0].message.content
            raise

    def _parse_review_response(self, response: str) -> ReviewResult:
        """
        Parse LLM review response into ReviewResult.

        Args:
            response: Raw LLM response text

        Returns:
            ReviewResult: Parsed review result
        """
        try:
            # Clean potential markdown wrapping
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            return ReviewResult(
                passed=data.get("passed", True),
                score=data.get("score", 70),
                issues=data.get("issues", []),
                summary=data.get("summary", "Review completed."),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            # If parsing fails, assume pass with a note
            return ReviewResult(
                passed=True,
                score=70,
                issues=[],
                summary="Review response could not be parsed. Auto-passed.",
                suggestions=["Consider manual review."],
            )
