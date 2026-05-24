"""
Orchestrator module for managing the software factory pipeline.

Implements a state machine that coordinates the entire development lifecycle:
intake -> planning -> developing -> testing -> fixing -> reviewing -> deploying -> delivered

Now with real-time WebSocket event broadcasting for frontend live updates.
"""
import asyncio
import os
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.ws import (
    send_agent_log,
    send_deployment_update,
    send_pipeline_complete,
    send_project_status,
    send_task_update,
    send_test_result,
)
from backend.core.executor import Executor
from backend.core.gatekeeper import Gatekeeper, PermissionDeniedError
from backend.core.git_manager import GitManager
from backend.core.qqbot_notifier import QQBotNotifier as FeishuNotifier, NotifyContext, get_notifier
from backend.core.planner import Planner
from backend.core.reviewer import Reviewer
from backend.core.tester import Tester
from backend.core.webhook import get_webhook_notifier
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
        self.reviewer = Reviewer()
        self.git = GitManager()
        self.webhook = get_webhook_notifier()
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

    async def _ws_status(self, project: Project) -> None:
        """Push project status update via WebSocket for real-time frontend updates."""
        try:
            await send_project_status(str(project.id), project.status.value)
        except Exception:
            pass  # WebSocket failures should never block the pipeline

    async def _ws_log(self, project: Project, agent: str, message: str, level: str = "info") -> None:
        """Push agent log via WebSocket."""
        try:
            await send_agent_log(str(project.id), agent, message, level)
        except Exception:
            pass

    async def run_pipeline(self, project_id: str) -> None:
        """
        Run the complete pipeline for a project with global timeout protection.

        Args:
            project_id: Project UUID

        Raises:
            asyncio.TimeoutError: If the total pipeline exceeds PIPELINE_TIMEOUT_SECONDS
        """
        import time

        PIPELINE_TIMEOUT_SECONDS = int(os.environ.get("PIPELINE_TIMEOUT", "600"))  # 10 min default
        STAGE_TIMEOUT_SECONDS = int(os.environ.get("STAGE_TIMEOUT", "180"))  # 3 min per stage

        # Load project
        result = await self.db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Load or create permission policy
        policy = await self._get_or_create_policy(project)

        pipeline_start = time.time()

        try:
            # Webhook: pipeline started
            try:
                await self.webhook.notify_pipeline_started(str(project.id), project.name)
            except Exception:
                pass
            # Helper: run a stage with individual timeout
            async def _timed_stage(coro, stage_name: str):
                elapsed = time.time() - pipeline_start
                remaining = PIPELINE_TIMEOUT_SECONDS - elapsed
                if remaining <= 0:
                    raise asyncio.TimeoutError(f"Pipeline global timeout ({PIPELINE_TIMEOUT_SECONDS}s) exceeded at stage: {stage_name}")
                timeout = min(STAGE_TIMEOUT_SECONDS, remaining)
                try:
                    return await asyncio.wait_for(coro, timeout=timeout)
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError(f"Stage '{stage_name}' timed out after {timeout:.0f}s")

            # State machine stages
            await _timed_stage(self._stage_intake(project), "intake")
            await _timed_stage(self._stage_planning(project), "planning")
            await _timed_stage(self._stage_developing(project, policy), "developing")

            # Git: initialize repo after code generation
            try:
                await self.git.init_repo(str(project.id), project.name)
            except Exception:
                pass  # Git failures never block pipeline

            await _timed_stage(self._stage_testing(project), "testing")

            # Fixing loop if tests fail
            fix_round = 0
            while not await self._all_tests_passed(project):
                fix_round += 1
                if not await self._can_retry(project, policy):
                    project.status = ProjectStatus.FAILED
                    await self.db.commit()
                    await self.notifier.send_stage_update(
                        self._notify_ctx(project, "所有任务重试次数已耗尽，流水线失败。")
                    )
                    return

                await _timed_stage(self._stage_fixing(project, policy), f"fixing-{fix_round}")

                # Git: commit fix changes
                try:
                    await self.git.commit_changes(
                        str(project.id),
                        f"fix: automated fix round {fix_round} by AI Factory",
                    )
                except Exception:
                    pass

                await _timed_stage(self._stage_testing(project), f"testing-{fix_round}")

            await _timed_stage(self._stage_reviewing(project), "reviewing")
            await _timed_stage(self._stage_deploying(project, policy), "deploying")
            await _timed_stage(self._stage_delivered(project), "delivered")

        except asyncio.TimeoutError as e:
            project.status = ProjectStatus.FAILED
            elapsed = time.time() - pipeline_start
            await self._log_agent_run(
                project,
                "orchestrator",
                "Pipeline timeout",
                f"Pipeline timed out after {elapsed:.1f}s: {str(e)}",
                AgentStatus.TIMEOUT,
            )
            await self.db.commit()
            await self.notifier.send_stage_update(
                self._notify_ctx(project, f"⏰ 流水线超时（{elapsed:.0f}s）：{str(e)}", error=str(e))
            )
            # Webhook: pipeline failed
            try:
                await self.webhook.notify_pipeline_failed(
                    str(project.id), project.name, str(e), stage="timeout"
                )
            except Exception:
                pass
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
            # Webhook: pipeline failed
            try:
                await self.webhook.pipeline_failed(
                    str(project.id), project.name,
                    error=str(e), stage="unknown",
                )
            except Exception:
                pass
            raise

    async def _stage_intake(self, project: Project) -> None:
        """Intake stage: validate project requirements."""
        project.status = ProjectStatus.CREATED
        await self.db.commit()
        await self._ws_status(project)
        await self.notifier.send_stage_update(
            self._notify_ctx(project, f"项目 '{project.name}' 已创建，开始需求分析。")
        )
        # Webhook: pipeline started
        try:
            await self.webhook.pipeline_started(str(project.id), project.name)
        except Exception:
            pass

    async def _stage_planning(self, project: Project) -> None:
        """Planning stage: analyze requirements and generate tasks."""
        project.status = ProjectStatus.REQUIREMENT_ANALYZING
        await self.db.commit()
        await self._ws_status(project)
        await self._ws_log(project, "planner", "开始分析需求，生成 PRD...")
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
        await self._ws_status(project)
        await self._ws_log(project, "planner", f"PRD 生成完成，正在拆分开发任务...")
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
        """Developing stage: execute tasks with parallel execution for independent tasks.

        Tasks without dependencies (or whose dependencies are already met) are
        executed concurrently using asyncio.gather. Tasks with unmet dependencies
        wait until their predecessors complete, then run in the next wave.
        This dramatically reduces total pipeline time for multi-task projects.
        """
        project.status = ProjectStatus.DEVELOPING
        await self.db.commit()
        await self._ws_status(project)
        await self._ws_log(project, "executor", "AI 开始并行执行开发任务...")
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "AI 开始并行执行开发任务（无依赖任务并发）...")
        )

        # Load tasks
        result = await self.db.execute(
            select(Task).where(Task.project_id == project.id).order_by(Task.priority)
        )
        tasks = list(result.scalars().all())

        # Wave-based parallel execution
        max_waves = 10  # Safety limit to prevent infinite loops
        wave_count = 0

        while wave_count < max_waves:
            wave_count += 1

            # Find tasks ready to execute (deps met, not done/running)
            ready_tasks = []
            for task in tasks:
                if task.status in [TaskStatus.COMPLETED, TaskStatus.PASSED, TaskStatus.RUNNING]:
                    continue
                if await self._dependencies_met(task, tasks):
                    ready_tasks.append(task)

            if not ready_tasks:
                break  # All tasks completed or blocked

            # Mark tasks as running
            for task in ready_tasks:
                task.status = TaskStatus.RUNNING
            await self.db.commit()

            await self._ws_log(
                project, "executor",
                f"Wave {wave_count}: 并行执行 {len(ready_tasks)} 个任务...",
            )

            # Execute ready tasks in parallel
            async def _execute_one(task: Task) -> None:
                agent_run = await self.executor.execute_task(project, task)
                self.db.add(agent_run)
                if agent_run.status == AgentStatus.SUCCESS:
                    task.status = TaskStatus.COMPLETED
                else:
                    task.status = TaskStatus.FAILED
                # WebSocket: real-time task status update
                try:
                    await send_task_update(
                        str(project.id), str(task.id), task.status.value,
                        f"Task '{task.title}' {'completed' if task.status == TaskStatus.COMPLETED else 'failed'}"
                    )
                except Exception:
                    pass

            await asyncio.gather(*[_execute_one(t) for t in ready_tasks])
            await self.db.commit()

            # Notify for all tasks in this wave
            for task in ready_tasks:
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
        await self._ws_status(project)
        await self._ws_log(project, "tester", "正在运行测试套件...")
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
        # WebSocket: push test results
        try:
            await send_test_result(
                str(project.id),
                "full_suite",
                results["all_passed"],
                results.get("error_log") or "",
            )
        except Exception:
            pass
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
        """Fixing stage: fix failing tests with error context passed to LLM."""
        project.status = ProjectStatus.FIXING
        await self.db.commit()
        await self._ws_status(project)
        await self._ws_log(project, "executor", "测试未通过，AI 正在根据错误信息修复代码...")
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "测试未通过，AI 正在根据错误信息修复代码...")
        )

        # Collect error context from latest test runs
        error_context = await self._collect_test_errors(project)

        # Get failed tests
        result = await self.db.execute(
            select(Task)
            .where(Task.project_id == project.id)
            .where(Task.status == TaskStatus.FAILED)
        )
        failed_tasks = result.scalars().all()

        # Retry failed tasks with error context
        for task in failed_tasks:
            # Check retry policy
            Gatekeeper.validate_task_retry(policy, task.retry_count)

            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            await self.db.commit()

            # Re-execute WITH error context so LLM knows what to fix
            agent_run = await self.executor.execute_task(
                project, task, error_context=error_context
            )
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

    async def _collect_test_errors(self, project: Project) -> str:
        """
        Collect error logs from the latest test runs for this project.

        Returns a formatted string with all test failures and their error output.
        """
        from backend.models.project import TestRun, TestStatus

        result = await self.db.execute(
            select(TestRun)
            .where(TestRun.project_id == project.id)
            .where(TestRun.status == TestStatus.FAILED)
            .order_by(TestRun.created_at.desc())
            .limit(10)
        )
        failed_runs = result.scalars().all()

        if not failed_runs:
            return "Tests failed but no error details available."

        error_parts = []
        for run in failed_runs:
            header = f"[{run.test_type}] Command: {run.command}"
            error = run.error_log or run.result or "No output captured"
            error_parts.append(f"{header}\n{error[:500]}")

        return "\n\n---\n\n".join(error_parts)

    async def _stage_reviewing(self, project: Project) -> None:
        """Reviewing stage: LLM-powered code review for security, quality, and best practices."""
        project.status = ProjectStatus.REVIEWING
        await self.db.commit()
        await self._ws_status(project)
        await self._ws_log(project, "reviewer", "正在进行 AI 代码审查...")
        await self.notifier.send_stage_update(
            self._notify_ctx(project, "所有测试通过，正在进行 AI 代码审查（安全性/质量/最佳实践）...")
        )

        # Perform LLM code review
        agent_run, review_result = await self.reviewer.review_project(project)
        self.db.add(agent_run)
        await self.db.commit()

        # Decide if review passes
        if review_result.passed:
            await self.notifier.send_stage_update(
                self._notify_ctx(
                    project,
                    f"代码审查通过 ✅ 评分：{review_result.score}/100",
                    details={
                        "评分": str(review_result.score),
                        "问题数": str(len(review_result.issues)),
                        "摘要": review_result.summary,
                    },
                )
            )
        else:
            # Review failed but don't block pipeline — log issues and continue
            issue_summary = "; ".join(
                f"[{i['severity']}] {i['description']}"
                for i in review_result.issues[:5]
            )
            await self.notifier.send_stage_update(
                self._notify_ctx(
                    project,
                    f"代码审查发现问题（评分：{review_result.score}/100），但不阻断流水线。",
                    details={
                        "评分": str(review_result.score),
                        "关键问题": issue_summary[:200],
                        "建议": "; ".join(review_result.suggestions[:3]),
                    },
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
        await self._ws_status(project)
        await self._ws_log(project, "deployer", "代码审查通过，正在部署...")
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
        # WebSocket: deployment update
        try:
            await send_deployment_update(
                str(project.id), environment, deployment.preview_url, "success"
            )
        except Exception:
            pass
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
        await self._ws_status(project)

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

        # WebSocket: pipeline complete
        try:
            report_url = deployment.preview_url if deployment else f"/projects/{project.id}/delivery-report"
            await send_pipeline_complete(str(project.id), report_url)
        except Exception:
            pass

        # Git: push to GitHub if configured
        try:
            repo_url = await self.git.push_to_github(
                str(project.id), project.name, private=True
            )
            if repo_url:
                await self._ws_log(project, "git", f"代码已推送到 GitHub: {repo_url}")
                # Update deployment with repo URL
                if deployment:
                    deployment.logs = (deployment.logs or "") + f"\nGitHub: {repo_url}"
                    await self.db.commit()
        except Exception:
            repo_url = None

        # Webhook: pipeline completed
        try:
            duration = (project.updated_at - project.created_at).total_seconds() if project.updated_at else 0
            await self.webhook.pipeline_completed(
                str(project.id),
                project.name,
                duration_seconds=duration,
                repo_url=repo_url or "",
                preview_url=deployment.preview_url if deployment else "",
            )
        except Exception:
            pass

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
