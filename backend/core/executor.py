"""
Executor module for code generation using Claude Code subprocess.

Runs claude -p commands in project workspace directories.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.models.project import AgentRun, AgentStatus, Project, Task


class Executor:
    """Code generation executor using Claude Code subprocess."""

    def __init__(self, workspace_root: str = "./workspace") -> None:
        """
        Initialize executor with workspace root directory.

        Args:
            workspace_root: Root directory for project workspaces
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)

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
    ) -> AgentRun:
        """
        Execute a task using Claude Code subprocess.

        Args:
            project: Project instance
            task: Task instance
            max_turns: Maximum conversation turns for Claude Code

        Returns:
            AgentRun: Agent run record with execution results
        """
        workspace = self.get_project_workspace(project)

        # Build task prompt
        prompt = self._build_task_prompt(task, project)

        # Create agent run record
        agent_run = AgentRun(
            project_id=project.id,
            task_id=task.id,
            agent_name="claude_code_executor",
            input=prompt,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            # Execute Claude Code subprocess
            stdout, stderr, returncode = await self._run_claude_subprocess(
                workspace=workspace,
                prompt=prompt,
                max_turns=max_turns,
            )

            # Update agent run with results
            agent_run.output = stdout
            agent_run.logs = stderr
            agent_run.status = (
                AgentStatus.SUCCESS if returncode == 0 else AgentStatus.FAILED
            )
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

    def _build_task_prompt(self, task: Task, project: Project) -> str:
        """
        Build Claude Code prompt from task details.

        Args:
            task: Task instance
            project: Project instance

        Returns:
            str: Formatted prompt for Claude Code
        """
        prompt = f"""
Project: {project.name}
Tech Stack: {project.tech_stack or "As appropriate"}

Task: {task.title}
Role: {task.role}

Description:
{task.description}

Requirements:
1. Follow best practices for {project.tech_stack or "the chosen tech stack"}
2. Include proper error handling and logging
3. Write clean, maintainable code with type hints/annotations
4. Add appropriate tests if applicable
5. Document complex logic with comments

Complete this task fully and ensure all code compiles/runs without errors.
"""
        return prompt

    async def _run_claude_subprocess(
        self,
        workspace: Path,
        prompt: str,
        max_turns: int = 20,
        timeout: int = 600,
    ) -> tuple[str, str, int]:
        """
        Run Claude Code as subprocess.

        Args:
            workspace: Working directory for subprocess
            prompt: Task prompt
            max_turns: Maximum conversation turns
            timeout: Execution timeout in seconds

        Returns:
            tuple: (stdout, stderr, returncode)
        """
        # Escape prompt for shell
        escaped_prompt = prompt.replace("'", "'\"'\"'")

        # Build command
        command = [
            "claude",
            "-p",
            escaped_prompt,
            "--max-turns",
            str(max_turns),
            "--dangerously-skip-permissions",
        ]

        # Run subprocess
        process = await asyncio.create_subprocess_exec(
            *command,
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
            max_turns: Maximum conversation turns

        Returns:
            AgentRun: Agent run record with execution results
        """
        workspace = self.get_project_workspace(project)

        # Create agent run record
        agent_run = AgentRun(
            project_id=project.id,
            task_id=None,
            agent_name="claude_code_executor",
            input=prompt,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            stdout, stderr, returncode = await self._run_claude_subprocess(
                workspace=workspace,
                prompt=prompt,
                max_turns=max_turns,
            )

            agent_run.output = stdout
            agent_run.logs = stderr
            agent_run.status = (
                AgentStatus.SUCCESS if returncode == 0 else AgentStatus.FAILED
            )
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
