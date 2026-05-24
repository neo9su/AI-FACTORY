"""
Executor module for code generation using LLM API (OpenAI-compatible).

Uses the configured LLM endpoint to generate code for tasks.
Supports fallback model if primary fails.
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.models.project import AgentRun, AgentStatus, Project, Task

load_dotenv()


class Executor:
    """Code generation executor using LLM API."""

    def __init__(self, workspace_root: str = "./workspace") -> None:
        """
        Initialize executor with workspace root directory.

        Args:
            workspace_root: Root directory for project workspaces
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        
        # Initialize LLM client
        api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "http://10.190.0.214:8080/v1")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.fallback_model = os.getenv("LLM_FALLBACK_MODEL", "us.anthropic.claude-opus-4-6")
        
        # Token usage tracking for the last LLM call
        self._last_usage: dict = {}

    def get_project_workspace(self, project: Project) -> Path:
        """
        Get workspace directory for a project.

        Args:
            project: Project instance

        Returns:
            Path: Project workspace directory
        """
        workspace = self.workspace_root / project.id
        workspace.mkdir(exist_ok=True)
        return workspace

    async def execute_task(
        self,
        project: Project,
        task: Task,
        max_turns: int = 20,
        error_context: Optional[str] = None,
    ) -> AgentRun:
        """
        Execute a task using LLM API to generate code.

        Args:
            project: Project instance
            task: Task instance
            max_turns: Maximum iterations (unused in API mode, kept for interface compat)
            error_context: Previous error log from failed tests — helps LLM fix precisely

        Returns:
            AgentRun: Agent run record with execution results
        """
        workspace = self.get_project_workspace(project)

        # Build task prompt (with error context if retrying)
        prompt = self._build_task_prompt(task, project, error_context=error_context)

        # Create agent run record
        agent_run = AgentRun(
            project_id=project.id,
            task_id=task.id,
            agent_name="llm_code_executor",
            input=prompt,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            # Execute LLM code generation
            result = await self._call_llm(prompt, workspace)

            # Write generated code to workspace
            await self._write_generated_files(workspace, result)

            # Build usage summary
            usage_info = ""
            if self._last_usage:
                usage_info = (
                    f" | model={self._last_usage.get('model_used', 'unknown')}"
                    f" tokens={self._last_usage.get('total_tokens', 0)}"
                    f" (prompt={self._last_usage.get('prompt_tokens', 0)}"
                    f" completion={self._last_usage.get('completion_tokens', 0)})"
                    f" latency={self._last_usage.get('latency_ms', 0)}ms"
                )
                if self._last_usage.get("retried"):
                    usage_info += " [retried]"

            # Update agent run with results
            agent_run.output = result
            agent_run.logs = f"Generated code written to {workspace}{usage_info}"
            agent_run.status = AgentStatus.SUCCESS
            agent_run.finished_at = datetime.utcnow()

        except asyncio.TimeoutError:
            agent_run.status = AgentStatus.TIMEOUT
            agent_run.logs = "Execution timed out"
            agent_run.finished_at = datetime.utcnow()
        except Exception as e:
            agent_run.status = AgentStatus.FAILED
            agent_run.logs = f"Execution error: {str(e)}"
            agent_run.finished_at = datetime.utcnow()

        return agent_run

    def _build_task_prompt(self, task: Task, project: Project, error_context: Optional[str] = None) -> str:
        """
        Build optimized LLM prompt from task details.

        Args:
            task: Task instance
            project: Project instance
            error_context: Previous error log from failed tests (for retry)

        Returns:
            str: Formatted prompt for high-quality code generation
        """
        tech_stack = project.tech_stack or "Python"
        
        # Detect language-specific guidelines
        stack_lower = tech_stack.lower()
        if "python" in stack_lower:
            lang_guidelines = """
Language-specific guidelines:
- Use Python 3.11+ features (type hints, dataclasses, pathlib)
- Follow PEP 8 and use f-strings
- Include __init__.py for packages
- Use pytest for tests (conftest.py + test_*.py)
- Add requirements.txt or pyproject.toml with dependencies
- Use logging module (not print) for output
- Include if __name__ == '__main__': guard for CLI tools
"""
        elif any(kw in stack_lower for kw in ("node", "next", "react", "typescript")):
            lang_guidelines = """
Language-specific guidelines:
- Use TypeScript with strict mode
- Functional components with hooks (React)
- Include package.json with scripts (dev, build, test, lint)
- Use ESLint + Prettier config
- Use proper module imports (ES6)
- Add tsconfig.json for TypeScript projects
"""
        elif "go" in stack_lower:
            lang_guidelines = """
Language-specific guidelines:
- Follow Go conventions (exported names, error handling)
- Include go.mod
- Use standard library where possible
- Table-driven tests
"""
        else:
            lang_guidelines = f"""
Language-specific guidelines:
- Follow best practices for {tech_stack}
- Include proper project structure
"""

        prompt = f"""You are an expert software engineer. Generate production-quality code for this task.

## Project Context
- **Project:** {project.name}
- **Goal:** {project.goal or "Not specified"}
- **Tech Stack:** {tech_stack}
- **User Requirement:** {project.user_requirement[:500] if project.user_requirement else "See task description"}

## Current Task
- **Title:** {task.title}
- **Role:** {task.role}
- **Description:** {task.description}

## Code Quality Requirements
1. Production-ready: proper error handling, input validation, edge cases
2. Well-structured: clear separation of concerns, single responsibility
3. Fully typed: all function parameters and return types annotated
4. Documented: docstrings for public functions, inline comments for complex logic
5. Testable: include unit tests that cover key functionality
6. Complete: all files needed to run the code (configs, dependencies, etc.)
{lang_guidelines}
## Output Format
Return a JSON object with ALL files needed:
```json
{{
  "files": [
    {{"path": "src/main.py", "content": "...full file content..."}},
    {{"path": "tests/test_main.py", "content": "...full test content..."}},
    {{"path": "requirements.txt", "content": "...dependencies..."}}
  ],
  "summary": "Brief description of implementation approach"
}}
```

IMPORTANT:
- File paths must be relative (no leading /)
- Include ALL necessary files (don't assume any exist)
- Tests must actually test the implementation
- Code must be immediately runnable
- Return ONLY valid JSON, no markdown code blocks
"""
        # Add error context for retry attempts
        if error_context:
            prompt += f"""
## ⚠️ PREVIOUS ATTEMPT FAILED — FIX THESE ERRORS

The previous code generation failed tests. Here is the error output:
```
{error_context[:2000]}
```

IMPORTANT: Analyze the errors above and fix ALL issues in your new output.
Do NOT repeat the same mistakes. Focus on:
1. The specific error messages and stack traces
2. Missing imports or dependencies
3. Incorrect function signatures or return types
4. Logic errors identified by tests
"""
        return prompt

    async def _call_llm(self, prompt: str, workspace: Path) -> str:
        """
        Call LLM API with fallback support, JSON validation retry, and token tracking.
        
        If the LLM response is not valid JSON, retries once with a fix-up prompt.
        Tracks token usage (prompt + completion) and latency in self._last_usage.
        
        Args:
            prompt: Task prompt
            workspace: Working directory context
            
        Returns:
            str: LLM response content (validated as parseable JSON)
        """
        import time

        # Include workspace context if files exist
        context = ""
        existing_files = list(workspace.rglob("*"))
        if existing_files:
            file_list = [str(f.relative_to(workspace)) for f in existing_files if f.is_file()]
            if file_list:
                context = f"\n\nExisting files in workspace:\n" + "\n".join(f"- {f}" for f in file_list[:20])

        messages = [
            {"role": "system", "content": (
                "You are a senior full-stack software engineer with 15+ years experience. "
                "You write production-quality code that is clean, well-tested, and immediately runnable. "
                "You always output valid JSON exactly matching the requested structure. "
                "Never wrap output in markdown code blocks. Never add commentary outside the JSON."
            )},
            {"role": "user", "content": prompt + context},
        ]

        # Reset usage tracking for this call
        self._last_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model_used": self.model,
            "latency_ms": 0,
            "retried": False,
        }

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=8192,
                temperature=0.1,
            )
            result = response.choices[0].message.content
            # Track usage
            if response.usage:
                self._last_usage["prompt_tokens"] += response.usage.prompt_tokens or 0
                self._last_usage["completion_tokens"] += response.usage.completion_tokens or 0
                self._last_usage["total_tokens"] += response.usage.total_tokens or 0
        except Exception as e:
            # Fallback to backup model
            if self.fallback_model and self.fallback_model != self.model:
                self._last_usage["model_used"] = self.fallback_model
                response = await self.client.chat.completions.create(
                    model=self.fallback_model,
                    messages=messages,
                    max_tokens=8192,
                    temperature=0.1,
                )
                result = response.choices[0].message.content
                if response.usage:
                    self._last_usage["prompt_tokens"] += response.usage.prompt_tokens or 0
                    self._last_usage["completion_tokens"] += response.usage.completion_tokens or 0
                    self._last_usage["total_tokens"] += response.usage.total_tokens or 0
            else:
                raise

        # Validate JSON output — retry once if invalid
        if not self._is_valid_file_json(result):
            self._last_usage["retried"] = True
            # Ask LLM to fix its output
            fix_messages = messages + [
                {"role": "assistant", "content": result},
                {"role": "user", "content": (
                    "Your response is NOT valid JSON or is missing the 'files' array. "
                    "Please output ONLY a valid JSON object with this exact structure:\n"
                    '{"files": [{"path": "...", "content": "..."}], "summary": "..."}\n'
                    "No markdown, no code blocks, no extra text. Just raw JSON."
                )},
            ]
            try:
                fix_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=fix_messages,
                    max_tokens=8192,
                    temperature=0.0,
                )
                fixed_result = fix_response.choices[0].message.content
                if fix_response.usage:
                    self._last_usage["prompt_tokens"] += fix_response.usage.prompt_tokens or 0
                    self._last_usage["completion_tokens"] += fix_response.usage.completion_tokens or 0
                    self._last_usage["total_tokens"] += fix_response.usage.total_tokens or 0
                if self._is_valid_file_json(fixed_result):
                    self._last_usage["latency_ms"] = int((time.time() - start_time) * 1000)
                    return fixed_result
            except Exception:
                pass  # Use original result if retry fails

        self._last_usage["latency_ms"] = int((time.time() - start_time) * 1000)
        return result

    def _is_valid_file_json(self, text: str) -> bool:
        """
        Check if text is valid JSON with a 'files' array.
        
        Returns:
            bool: True if text parses as JSON with files array
        """
        try:
            clean = text.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0].strip()
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(clean)
            files = parsed.get("files", [])
            if not isinstance(files, list) or len(files) == 0:
                return False
            # Check that each file has path and content
            for f in files:
                if "path" not in f or "content" not in f:
                    return False
            return True
        except (json.JSONDecodeError, TypeError, AttributeError):
            return False

    async def _write_generated_files(self, workspace: Path, result: str) -> None:
        """
        Parse LLM output and write generated files to workspace.
        
        Args:
            workspace: Project workspace directory
            result: LLM response (expected JSON with files array)
        """
        try:
            # Try to parse as JSON
            data = result
            if "```json" in result:
                data = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                data = result.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(data)
            files = parsed.get("files", [])
            
            for file_info in files:
                file_path = workspace / file_info["path"]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_info["content"], encoding="utf-8")
                
        except (json.JSONDecodeError, KeyError, TypeError):
            # If not valid JSON, write raw output as a single file
            output_file = workspace / "generated_output.txt"
            output_file.write_text(result, encoding="utf-8")

    async def generate_code(
        self,
        project: Project,
        prompt: str,
        max_turns: int = 20,
    ) -> AgentRun:
        """
        Generate code from a freeform prompt (not tied to a specific task).

        Args:
            project: Project instance
            prompt: Generation prompt
            max_turns: Maximum iterations (unused in API mode)

        Returns:
            AgentRun: Agent run record with execution results
        """
        workspace = self.get_project_workspace(project)

        # Create agent run record
        agent_run = AgentRun(
            project_id=project.id,
            task_id=None,
            agent_name="llm_code_executor",
            input=prompt,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            result = await self._call_llm(prompt, workspace)
            await self._write_generated_files(workspace, result)

            agent_run.output = result
            agent_run.logs = f"Generated code written to {workspace}"
            agent_run.status = AgentStatus.SUCCESS
            agent_run.finished_at = datetime.utcnow()

        except asyncio.TimeoutError:
            agent_run.status = AgentStatus.TIMEOUT
            agent_run.logs = "Execution timed out"
            agent_run.finished_at = datetime.utcnow()
        except Exception as e:
            agent_run.status = AgentStatus.FAILED
            agent_run.logs = f"Execution error: {str(e)}"
            agent_run.finished_at = datetime.utcnow()

        return agent_run
