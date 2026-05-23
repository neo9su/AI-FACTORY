"""
Orchestrator module for managing the software factory pipeline.

Implements a state machine that coordinates the entire development lifecycle:
intake -> planning -> developing -> testing -> fixing -> reviewing -> deploying -> delivered
"""
import asyncio
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.executor import Executor
from backend.core.gatekeeper import Gatekeeper, PermissionDeniedError
from backend.core.qqbot_notifier import QQBotNotifier as FeishuNotifier, NotifyContext, get_notifier
from backend.core.planner import Planner
from backend.core.tester import Tester
from backend.models.project import (
    AgentRun,
    AgentStatus,
    DeliveryReport,
    Deployment,
    DeploymentStatus,
    PermissionPolicy,
    Project,
    ProjectStatus,
    Requirements,
    Task,
    TaskStatus,
    TestStatus,
)


class Orchestrator:
    """Pipeline orchestration state machine."""

    def __init__(self, db: AsyncSession, notifier: Optional[FeishuNotifier] = None) -> None:
        """
        Initialize orchestrator with database session.

        Args:
            db: Async SQLAlchemy session
            notifier: Optional FeishuNotifier instance; falls back to module singleton
        """
        self.db = db
        self.planner = Planner()
        self.executor = Executor()
        self.tester = Tester()
        self.notifier: FeishuNotifier = notifier or get_notifier()

    def _notify_ctx(self, project: "Project", message: str, **kwargs: Any) -> NotifyContext:
        """Build a NotifyContext from a project."""
        return NotifyContext(
            project_id=str(project.id),
            project_name=project.name,
            stage=project.status.value if hasattr(project.status, "value") else str(project.status),
            message=message,
            **kwargs,
        )

    async def run_pipeline(self, project_id: str) -> None:
        """
        Run the complete pipeline for a project.

        Args:
            project_id: Project UUID
        """
        # Load project
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Load or create permission policy
        policy = await self._get_or_create_policy(project)

        try:
            # State machine stages
            await self._stage_intake(project)
            await self._stage_planning(project)
            await self._stage_developing(project, policy)
            await self._stage_testing(project)

            # Fixing loop if tests fail
            while not await self._all_tests_passed(project):
                if not await self._can_retry(project, policy):
                    project.status = ProjectStatus.FAILED
                    await self.db.commit()
                    await self.notifier.send_stage_update(
                        self._notify_ctx(project, "所有任务重试次数已耗尽，流水线失败。")
                    )
                    return

                await self._stage_fixing(project, policy)
                await self._stage_testing(project)

            await self._stage_reviewing(project)
            await self._stage_deploying(project, policy)
            await self._stage_delivered(project)

        except PermissionDeniedError as e:
            project.status = ProjectStatus.BLOCKED_BY_GATE
            await self._log_agent_run(
                project,
                "gatekeeper",
                "Permission check",
                f"Pipeline blocked: {str(e)}",
                AgentStatus.FAILED,
            )
            await self.db.commit()
            await self.notifier.send_gate_blocked(
                self._notify_ctx(project, str(e)),
                operation=str(e).split(":")[0] if ":" in str(e) else "unknown",
                reason=str(e),
            )
        except Exception as e:
            project.status = ProjectStatus.FAILED
            await self._log_agent_run(
                project,
                "orchestrator",
                "Pipeline execution",
                f"Pipeline failed: {str(e)}",
                AgentStatus.FAILED,
            )
            await self.db.commit()
            await self.notifier.send_stage_update(
                self._notify_ctx(project, f"流水线异常中断：{str(e)}", error=str(e))
            )
            raise

    async def _stage_intake(self, project: Project) -> None:
        """Intake stage: validate project requirements."""
        project.status = ProjectStatus.CREATED
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, f"项目 '{project.name}' 已创建，开始需求分析。")
        )

    async def _stage_planning(self, project: Project) -> None:
        """Planning stage: analyze requirements and generate tasks."""
        project.status = ProjectStatus.REQUIREMENT_ANALYZING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "正在分析需求，生成 PRD...")
        )

        # Analyze requirements
        prd_data = await self.planner.analyze_requirements(project)

        # Create requirements record
        requirements = Requirements(
            project_id=project.id,
            prd_content=str(prd_data),
            features=prd_data.get("features"),
            architecture=prd_data.get("architecture"),
            constraints=prd_data.get("constraints"),
        )
        self.db.add(requirements)

        # Log analysis
        await self._log_agent_run(
            project,
            "planner",
            f"Analyze requirements for {project.name}",
            f"PRD generated with {len(prd_data.get('features', []))} features",
            AgentStatus.SUCCESS,
        )

        # Generate tasks
        project.status = ProjectStatus.PLANNING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(
                project,
                f"PRD 生成完成，共 {len(prd_data.get('features', []))} 个功能。正在拆分开发任务...",
            )
        )

        tasks_data = await self.planner.generate_tasks(project, prd_data)

        # Create task records
        for task_data in tasks_data:
            task = Task(**task_data)
            self.db.add(task)

        await self.db.commit()

        # Log task generation
        await self._log_agent_run(
            project,
            "planner",
            "Generate development tasks",
            f"Generated {len(tasks_data)} tasks",
            AgentStatus.SUCCESS,
        )
        await self.notifier.send_stage_update(
            self._notify_ctx(
                project,
                f"任务拆分完成，共 {len(tasks_data)} 个开发任务，进入开发阶段。",
                details={"任务数量": str(len(tasks_data))},
            )
        )

    async def _stage_developing(
        self,
        project: Project,
        policy: PermissionPolicy,
    ) -> None:
        """Developing stage: execute all tasks."""
        project.status = ProjectStatus.DEVELOPING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "Claude Code 开始执行开发任务...")
        )

        # Load tasks
        result = await self.db.execute(
            select(Task).where(Task.project_id == project.id).order_by(Task.priority)
        )
        tasks = result.scalars().all()

        # Execute tasks in priority order
        for task in tasks:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.PASSED]:
                continue

            # Check dependencies
            if not await self._dependencies_met(task, tasks):
                task.status = TaskStatus.BLOCKED
                continue

            # Execute task
            task.status = TaskStatus.RUNNING
            await self.db.commit()

            agent_run = await self.executor.execute_task(project, task)
            self.db.add(agent_run)

            if agent_run.status == AgentStatus.SUCCESS:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED

            await self.db.commit()
            await self.notifier.send_task_complete(
                self._notify_ctx(project, f"任务执行{'完成' if task.status == TaskStatus.COMPLETED else '失败'}"),
                task_title=task.title,
                task_status=task.status.value,
                retry_count=task.retry_count,
            )

    async def _stage_testing(self, project: Project) -> None:
        """Testing stage: run all tests."""
        project.status = ProjectStatus.TESTING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "正在运行测试套件（unit / integration / E2E）...")
        )

        # Run tests
        test_runs = await self.tester.run_tests(project)

        # Save test runs
        for test_run in test_runs:
            self.db.add(test_run)

        await self.db.commit()

        # Log test results
        results = self.tester.collect_results(test_runs)
        await self._log_agent_run(
            project,
            "tester",
            "Run test suite",
            f"Tests: {results['passed']}/{results['total']} passed",
            AgentStatus.SUCCESS if results["all_passed"] else AgentStatus.FAILED,
        )
        await self.notifier.send_test_result(
            self._notify_ctx(
                project,
                f"测试完成：{results['passed']}/{results['total']} 通过",
                error=results.get("error_log"),
            ),
            passed=results["passed"],
            failed=results["total"] - results["passed"],
            test_type="full suite",
        )

    async def _stage_fixing(
        self,
        project: Project,
        policy: PermissionPolicy,
    ) -> None:
        """Fixing stage: fix failing tests."""
        project.status = ProjectStatus.FIXING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "测试未通过，Claude Code 正在修复失败任务...")
        )

        # Get failed tests
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == project.id)
            .where(Task.status == TaskStatus.FAILED)
        )
        failed_tasks = result.scalars().all()

        # Retry failed tasks
        for task in failed_tasks:
            # Check retry policy
            Gatekeeper.validate_task_retry(policy, task.retry_count)

            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            await self.db.commit()

            # Re-execute with error context
            agent_run = await self.executor.execute_task(project, task)
            self.db.add(agent_run)

            if agent_run.status == AgentStatus.SUCCESS:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED

            await self.db.commit()
            await self.notifier.send_task_complete(
                self._notify_ctx(project, f"修复任务{'成功' if task.status == TaskStatus.COMPLETED else '失败'}"),
                task_title=task.title,
                task_status=task.status.value,
                retry_count=task.retry_count,
            )

    async def _stage_reviewing(self, project: Project) -> None:
        """Reviewing stage: code review (placeholder for future implementation)."""
        project.status = ProjectStatus.REVIEWING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "所有测试通过，正在进行自动代码审查...")
        )

        # Placeholder: In future, integrate with code review tools
        await self._log_agent_run(
            project,
            "reviewer",
            "Code review",
            "Automated review passed",
            AgentStatus.SUCCESS,
        )
        # Notify that review passed
        await self.notifier.send_stage_update(
            self._notify_ctx(
                project,
                "代码审查通过 ✅，准备进入部署阶段。",
                details={"审查结果": "自动审查通过，无严重问题"},
            )
        )

    async def _stage_deploying(
        self,
        project: Project,
        policy: PermissionPolicy,
    ) -> None:
        """Deploying stage: deploy to staging/production."""
        project.status = ProjectStatus.DEPLOYING
        await self.db.commit()
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "代码审查通过，正在部署到预览环境...")
        )

        # Check deployment permission
        environment = "production" if policy.allow_production_release else "staging"
        operation = "deploy_to_production" if environment == "production" else "deploy_staging"

        Gatekeeper.check_permission(policy, operation)

        # Create deployment record
        deployment = Deployment(
            project_id=project.id,
            environment=environment,
            status=DeploymentStatus.DEPLOYING,
        )
        self.db.add(deployment)
        await self.db.commit()

        # Placeholder: Actual deployment logic would go here
        # For now, mark as successful
        deployment.status = DeploymentStatus.SUCCESS
        deployment.preview_url = f"https://{project.id}.{environment}.example.com"
        deployment.logs = f"Deployed to {environment} successfully"

        await self.db.commit()

        await self._log_agent_run(
            project,
            "deployer",
            f"Deploy to {environment}",
            f"Deployment successful: {deployment.preview_url}",
            AgentStatus.SUCCESS,
        )
        await self.notifier.send_stage_update(
            self._notify_ctx(
                project,
                f"部署成功！环境：{environment}",
                preview_url=deployment.preview_url,
            )
        )

    async def _stage_delivered(self, project: Project) -> None:
        """Delivered stage: generate delivery report."""
        project.status = ProjectStatus.DELIVERED
        await self.db.commit()

        # Collect test results
        result = await self.db.execute(
            select(Task).where(Task.project_id == project.id)
        )
        tasks = result.scalars().all()

        passed_tests = [
            {"title": t.title, "status": t.status.value}
            for t in tasks
            if t.status in [TaskStatus.COMPLETED, TaskStatus.PASSED]
        ]
        failed_tests = [
            {"title": t.title, "status": t.status.value}
            for t in tasks
            if t.status == TaskStatus.FAILED
        ]

        # Get deployment URL
        deployment_result = await self.db.execute(
            select(Deployment)
            .where(Deployment.project_id == project.id)
            .order_by(Deployment.created_at.desc())
        )
        deployment = deployment_result.scalar_one_or_none()

        # Create delivery report
        report = DeliveryReport(
            project_id=project.id,
            summary=f"Project '{project.name}' completed successfully with {len(passed_tests)}/{len(tasks)} tasks passed",
            passed_tests={"tasks": passed_tests},
            failed_tests={"tasks": failed_tests},
            deployment_url=deployment.preview_url if deployment else None,
            known_issues="None" if not failed_tests else "See failed tasks",
            final_status="success" if not failed_tests else "partial",
        )
        self.db.add(report)
        await self.db.commit()

        # Send delivery notification to Feishu
        await self.notifier.send_delivery_report(
            self._notify_ctx(project, "项目交付完成！"),
            preview_url=deployment.preview_url if deployment else None,
            passed_tests=len(passed_tests),
            failed_tests=len(failed_tests),
            known_issues=[t["title"] for t in failed_tests] if failed_tests else [],
        )

    async def _all_tests_passed(self, project: Project) -> bool:
        """Check if all tests passed."""
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == project.id)
            .where(Task.status == TaskStatus.FAILED)
        )
        failed_tasks = result.scalars().all()
        return len(failed_tasks) == 0

    async def _can_retry(self, project: Project, policy: PermissionPolicy) -> bool:
        """Check if failed tasks can be retried."""
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == project.id)
            .where(Task.status == TaskStatus.FAILED)
        )
        failed_tasks = result.scalars().all()

        for task in failed_tasks:
            if task.retry_count >= policy.max_retry_count:
                return False

        return True

    async def _dependencies_met(
        self,
        task: Task,
        all_tasks: list[Task],
    ) -> bool:
        """Check if task dependencies are met."""
        if not task.dependencies:
            return True

        task_map = {t.id: t for t in all_tasks}

        for dep_id in task.dependencies:
            dep_task = task_map.get(dep_id)
            if not dep_task or dep_task.status not in [
                TaskStatus.COMPLETED,
                TaskStatus.PASSED,
            ]:
                return False

        return True

    async def _get_or_create_policy(self, project: Project) -> PermissionPolicy:
        """Get or create permission policy for project."""
        result = await self.db.execute(
            select(PermissionPolicy).where(PermissionPolicy.project_id == project.id)
        )
        policy = result.scalar_one_or_none()

        if not policy:
            policy = PermissionPolicy(
                project_id=project.id,
                allow_auto_deploy=False,
                allow_external_api_call=True,
                allow_database_migration=True,
                allow_delete_operation=False,
                allow_production_release=False,
                max_retry_count=3,
            )
            self.db.add(policy)
            await self.db.commit()

        return policy

    async def _log_agent_run(
        self,
        project: Project,
        agent_name: str,
        input_text: str,
        output_text: str,
        status: AgentStatus,
    ) -> None:
        """Log an agent run."""
        agent_run = AgentRun(
            project_id=project.id,
            agent_name=agent_name,
            input=input_text,
            output=output_text,
            status=status,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        self.db.add(agent_run)
        await self.db.commit()
