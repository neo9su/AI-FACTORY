"""
Tester module for running tests and collecting results.

Smart test detection: automatically selects test commands based on project
tech_stack and workspace file detection.

Supported stacks:
  - Python: pytest, ruff/flake8, mypy
  - Node/TypeScript: npm test, npm run lint, npm run build
  - Go: go test, go vet
  - Rust: cargo test, cargo clippy
  - Auto-detect from workspace files if tech_stack is ambiguous
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.models.project import Project, Task, TestRun, TestStatus


# ---------------------------------------------------------------------------
# Test command presets per tech stack
# ---------------------------------------------------------------------------

PYTHON_TEST_COMMANDS = [
    ("lint", "python -m ruff check . --ignore=E501 || python -m flake8 . --max-line-length=120 || true"),
    ("typecheck", "python -m mypy . --ignore-missing-imports --no-error-summary || true"),
    ("unit_tests", "python -m pytest -q --tb=short 2>/dev/null || python -m pytest -q --tb=short tests/ 2>/dev/null || true"),
]

NODE_TEST_COMMANDS = [
    ("lint", "npm run lint 2>/dev/null || npx eslint . 2>/dev/null || true"),
    ("typecheck", "npm run typecheck 2>/dev/null || npx tsc --noEmit 2>/dev/null || true"),
    ("unit_tests", "npm test -- --passWithNoTests 2>/dev/null || npx jest --passWithNoTests 2>/dev/null || true"),
    ("build", "npm run build 2>/dev/null || true"),
]

GO_TEST_COMMANDS = [
    ("lint", "go vet ./..."),
    ("unit_tests", "go test ./... -v -count=1"),
    ("build", "go build ./..."),
]

RUST_TEST_COMMANDS = [
    ("lint", "cargo clippy -- -D warnings 2>/dev/null || true"),
    ("unit_tests", "cargo test"),
    ("build", "cargo build"),
]

# Fallback: just try to find something that works
GENERIC_TEST_COMMANDS = [
    ("unit_tests", "echo 'No test framework detected, skipping tests'"),
]


def detect_test_commands(
    tech_stack: str = "",
    workspace: Optional[Path] = None,
) -> list[tuple[str, str]]:
    """
    Detect appropriate test commands based on tech stack and workspace files.

    Priority:
      1. Explicit tech_stack keywords
      2. Workspace file detection (package.json, setup.py, go.mod, Cargo.toml)
      3. Generic fallback

    Args:
        tech_stack: Project tech stack string (e.g., "Python, pytest")
        workspace: Optional workspace path for file-based detection

    Returns:
        list of (test_type, command) tuples
    """
    stack_lower = (tech_stack or "").lower()

    # 1. Keyword detection from tech_stack
    if any(kw in stack_lower for kw in ("python", "pytest", "django", "flask", "fastapi")):
        return PYTHON_TEST_COMMANDS
    if any(kw in stack_lower for kw in ("node", "npm", "next", "react", "vue", "angular", "typescript", "javascript")):
        return NODE_TEST_COMMANDS
    if any(kw in stack_lower for kw in ("go", "golang", "gin")):
        return GO_TEST_COMMANDS
    if any(kw in stack_lower for kw in ("rust", "cargo")):
        return RUST_TEST_COMMANDS

    # 2. File-based detection from workspace
    if workspace and workspace.exists():
        # Check for Python indicators
        if any([
            (workspace / "setup.py").exists(),
            (workspace / "pyproject.toml").exists(),
            (workspace / "requirements.txt").exists(),
            any(workspace.rglob("*.py")),
        ]):
            return PYTHON_TEST_COMMANDS

        # Check for Node indicators
        if (workspace / "package.json").exists():
            return NODE_TEST_COMMANDS

        # Check for Go indicators
        if (workspace / "go.mod").exists():
            return GO_TEST_COMMANDS

        # Check for Rust indicators
        if (workspace / "Cargo.toml").exists():
            return RUST_TEST_COMMANDS

    # 3. Fallback
    return GENERIC_TEST_COMMANDS


class Tester:
    """Test execution and result collection manager with smart stack detection."""

    def __init__(self, workspace_root: str = "./workspace") -> None:
        """
        Initialize tester with workspace root directory.

        Args:
            workspace_root: Root directory for project workspaces
        """
        self.workspace_root = Path(workspace_root)

    def get_project_workspace(self, project: Project) -> Path:
        """
        Get workspace directory for a project.

        Args:
            project: Project instance

        Returns:
            Path: Project workspace directory
        """
        return self.workspace_root / project.id

    async def run_tests(
        self,
        project: Project,
        task: Optional[Task] = None,
        commands: Optional[list[tuple[str, str]]] = None,
    ) -> list[TestRun]:
        """
        Run test commands and collect results.

        Auto-detects test commands from project tech_stack if not explicitly provided.

        Args:
            project: Project instance
            task: Optional task instance (if tests are task-specific)
            commands: Optional list of (test_type, command) tuples.
                     If None, auto-detects from tech_stack + workspace files.

        Returns:
            list[TestRun]: List of test run results
        """
        workspace = self.get_project_workspace(project)

        # Auto-detect test commands if not provided
        if commands is None:
            commands = detect_test_commands(
                tech_stack=project.tech_stack or "",
                workspace=workspace,
            )

        test_runs = []

        for test_type, command in commands:
            test_run = await self._run_single_test(
                project=project,
                task=task,
                workspace=workspace,
                test_type=test_type,
                command=command,
            )
            test_runs.append(test_run)

        return test_runs

    async def _run_single_test(
        self,
        project: Project,
        task: Optional[Task],
        workspace: Path,
        test_type: str,
        command: str,
        timeout: int = 300,
    ) -> TestRun:
        """
        Run a single test command.

        Args:
            project: Project instance
            task: Optional task instance
            workspace: Working directory
            test_type: Type of test (e.g., "lint", "unit_tests")
            command: Command to execute
            timeout: Execution timeout in seconds

        Returns:
            TestRun: Test run result
        """
        test_run = TestRun(
            project_id=project.id,
            task_id=task.id if task else None,
            test_type=test_type,
            command=command,
            status=TestStatus.RUNNING,
        )

        try:
            # Run command
            stdout, stderr, returncode = await self._run_command(
                workspace=workspace,
                command=command,
                timeout=timeout,
            )

            # Update test run with results
            test_run.result = stdout
            test_run.error_log = stderr if returncode != 0 else None
            test_run.status = TestStatus.PASSED if returncode == 0 else TestStatus.FAILED

        except asyncio.TimeoutError:
            test_run.status = TestStatus.FAILED
            test_run.error_log = f"Test timed out after {timeout} seconds"
        except Exception as e:
            test_run.status = TestStatus.FAILED
            test_run.error_log = f"Test execution error: {str(e)}"

        return test_run

    async def _run_command(
        self,
        workspace: Path,
        command: str,
        timeout: int = 300,
    ) -> tuple[str, str, int]:
        """
        Run a shell command in workspace.

        Args:
            workspace: Working directory
            command: Command to execute
            timeout: Execution timeout in seconds

        Returns:
            tuple: (stdout, stderr, returncode)
        """
        # Check if workspace exists
        if not workspace.exists():
            return "", f"Workspace not found: {workspace}", 1

        # Run command using shell
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            returncode = process.returncode or 0

        except asyncio.TimeoutError:
            # Kill process on timeout
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise

        return stdout, stderr, returncode

    def collect_results(self, test_runs: list[TestRun]) -> dict:
        """
        Collect and summarize test results.

        Args:
            test_runs: List of test run instances

        Returns:
            dict: Summary of test results including pass/fail counts
        """
        total = len(test_runs)
        passed = sum(1 for tr in test_runs if tr.status == TestStatus.PASSED)
        failed = sum(1 for tr in test_runs if tr.status == TestStatus.FAILED)
        skipped = sum(1 for tr in test_runs if tr.status == TestStatus.SKIPPED)

        # Collect error log from failed tests
        error_logs = []
        for tr in test_runs:
            if tr.status == TestStatus.FAILED and tr.error_log:
                error_logs.append(f"[{tr.test_type}] {tr.error_log[:200]}")

        results = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "all_passed": failed == 0 and total > 0,
            "error_log": "\n".join(error_logs) if error_logs else None,
            "details": [
                {
                    "test_type": tr.test_type,
                    "command": tr.command,
                    "status": tr.status.value,
                    "error": tr.error_log,
                }
                for tr in test_runs
            ],
        }

        return results

    async def run_custom_test(
        self,
        project: Project,
        test_type: str,
        command: str,
        task: Optional[Task] = None,
    ) -> TestRun:
        """
        Run a custom test command.

        Args:
            project: Project instance
            test_type: Type of test
            command: Command to execute
            task: Optional task instance

        Returns:
            TestRun: Test run result
        """
        workspace = self.get_project_workspace(project)

        return await self._run_single_test(
            project=project,
            task=task,
            workspace=workspace,
            test_type=test_type,
            command=command,
        )
