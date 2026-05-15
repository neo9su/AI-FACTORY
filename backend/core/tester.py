"""
Tester module for running tests and collecting results.

Executes test commands in project workspace and collects results.
"""
import asyncio
from pathlib import Path
from typing import Optional

from backend.models.project import Project, Task, TestRun, TestStatus


class Tester:
    """Test execution and result collection manager."""

    DEFAULT_TEST_COMMANDS = [
        ("lint", "npm run lint"),
        ("typecheck", "npm run typecheck"),
        ("unit_tests", "npm test -- --passWithNoTests"),
        ("build", "npm run build"),
    ]

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

        Args:
            project: Project instance
            task: Optional task instance (if tests are task-specific)
            commands: Optional list of (test_type, command) tuples

        Returns:
            list[TestRun]: List of test run results
        """
        workspace = self.get_project_workspace(project)
        commands = commands or self.DEFAULT_TEST_COMMANDS

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

    def collect_results(self, test_runs: list[TestRun]) -> dict[str, any]:
        """
        Collect and summarize test results.

        Args:
            test_runs: List of test run instances

        Returns:
            dict: Summary of test results
        """
        total = len(test_runs)
        passed = sum(1 for tr in test_runs if tr.status == TestStatus.PASSED)
        failed = sum(1 for tr in test_runs if tr.status == TestStatus.FAILED)
        skipped = sum(1 for tr in test_runs if tr.status == TestStatus.SKIPPED)

        results = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "all_passed": failed == 0 and total > 0,
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
