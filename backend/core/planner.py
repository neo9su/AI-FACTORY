"""
Planner module for requirements analysis and task generation.

Uses Claude API to analyze user requirements and generate structured PRD and tasks.
"""
import json
import os
from typing import Any

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from backend.models.project import Project, Task, TaskStatus

load_dotenv()


class Planner:
    """Requirements analyzer and task planner using Claude API."""

    def __init__(self) -> None:
        """Initialize planner with Anthropic client."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    async def analyze_requirements(self, project: Project) -> dict[str, Any]:
        """
        Analyze user requirements and generate structured PRD.

        Args:
            project: Project instance with user_requirement

        Returns:
            dict: Structured PRD containing features, architecture, constraints
        """
        prompt = f"""
Analyze the following software project requirement and create a structured Product Requirements Document (PRD).

User Requirement:
{project.user_requirement}

Project Goal:
{project.goal or "Not specified"}

Desired Tech Stack:
{project.tech_stack or "Choose appropriate stack"}

Generate a structured PRD in JSON format with the following sections:
1. features: List of key features and functionality
2. architecture: Technical architecture decisions (frontend, backend, database, etc.)
3. constraints: Technical constraints, limitations, and considerations
4. success_criteria: Measurable success criteria

Return ONLY valid JSON, no markdown formatting.
"""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content
        prd_text = response.content[0].text

        # Parse JSON response
        try:
            prd = json.loads(prd_text)
        except json.JSONDecodeError:
            # Fallback if response contains markdown
            if "```json" in prd_text:
                prd_text = prd_text.split("```json")[1].split("```")[0].strip()
                prd = json.loads(prd_text)
            else:
                raise ValueError("Invalid JSON response from Claude API")

        return prd

    async def generate_tasks(
        self,
        project: Project,
        prd: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate development tasks from PRD.

        Args:
            project: Project instance
            prd: Structured PRD dictionary

        Returns:
            list: List of task dictionaries ready for database insertion
        """
        prompt = f"""
Based on the following PRD, generate a list of development tasks that need to be completed.

Project: {project.name}
PRD: {json.dumps(prd, indent=2)}

Generate tasks in JSON format as an array of objects, each with:
- title: Brief task title (max 100 chars)
- description: Detailed task description
- role: Role responsible (e.g., "frontend", "backend", "devops", "testing")
- priority: Priority level (0=highest, higher numbers=lower priority)
- dependencies: Array of task indices this task depends on (use index in the array)

Create tasks in logical execution order:
1. Setup tasks (project structure, dependencies)
2. Backend tasks (API, database, core logic)
3. Frontend tasks (UI components, pages)
4. Integration tasks
5. Testing tasks
6. Deployment tasks

Return ONLY valid JSON array, no markdown formatting.
"""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text content
        tasks_text = response.content[0].text

        # Parse JSON response
        try:
            tasks_data = json.loads(tasks_text)
        except json.JSONDecodeError:
            # Fallback if response contains markdown
            if "```json" in tasks_text:
                tasks_text = tasks_text.split("```json")[1].split("```")[0].strip()
                tasks_data = json.loads(tasks_text)
            else:
                raise ValueError("Invalid JSON response from Claude API")

        # Convert to Task-compatible format
        tasks = []
        task_ids = []  # Track generated task IDs for dependency mapping

        for idx, task_data in enumerate(tasks_data):
            # Generate a temporary ID for dependency tracking
            temp_id = f"task_{idx}"
            task_ids.append(temp_id)

            # Map dependency indices to temporary IDs
            dependencies = []
            if "dependencies" in task_data and task_data["dependencies"]:
                for dep_idx in task_data["dependencies"]:
                    if 0 <= dep_idx < len(task_ids):
                        dependencies.append(task_ids[dep_idx])

            tasks.append({
                "project_id": project.id,
                "title": task_data.get("title", f"Task {idx + 1}"),
                "description": task_data.get("description", ""),
                "role": task_data.get("role", "general"),
                "priority": task_data.get("priority", idx),
                "status": TaskStatus.PENDING,
                "retry_count": 0,
                "max_retries": 3,
                "dependencies": dependencies,
            })

        return tasks
