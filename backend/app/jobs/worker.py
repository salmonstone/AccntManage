from __future__ import annotations

import asyncio
import json
import logging

from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.db.base import async_session_factory
from backend.app.models.enums import JobStatus, JobType
from backend.app.models.job import Job
from backend.app.services.job_service import JobService

logger = logging.getLogger(__name__)


class WorkerSupervisor:
    def __init__(self) -> None:
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(settings.MAX_WORKER_COUNT)

    async def start(self) -> None:
        self._running = True
        logger.info("Worker supervisor starting with %d max workers", settings.MAX_WORKER_COUNT)

        async with async_session_factory() as session:
            svc = JobService(session)
            recovered = await svc.recover_interrupted()
            if recovered:
                logger.info("Recovered %d interrupted jobs", recovered)

        asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Worker supervisor stopped")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Job)
                        .where(Job.status == JobStatus.QUEUED)
                        .order_by(Job.created_at.asc())
                        .limit(settings.MAX_WORKER_COUNT)
                    )
                    jobs = result.scalars().all()

                for job in jobs:
                    if not self._running:
                        break
                    await self._semaphore.acquire()
                    task = asyncio.create_task(self._run_job(job.id, job.job_type))
                    self._tasks.append(task)
                    task.add_done_callback(lambda t: self._task_done(t))

            except Exception:
                logger.exception("Worker poll error")

            await asyncio.sleep(2)

    def _task_done(self, task: asyncio.Task) -> None:
        self._semaphore.release()
        if task in self._tasks:
            self._tasks.remove(task)

    async def _run_job(self, job_id: int, job_type: JobType) -> None:
        async with async_session_factory() as session:
            svc = JobService(session)
            await svc.mark_running(job_id)

            try:
                await asyncio.wait_for(
                    self._execute_job(job_id, job_type, svc),
                    timeout=settings.JOB_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                await svc.mark_failed(job_id, "Job timed out")
            except asyncio.CancelledError:
                await svc.mark_failed(job_id, "Job cancelled during shutdown")
            except Exception as e:
                await svc.mark_failed(job_id, str(e)[:2000])

    async def _execute_job(self, job_id: int, job_type: JobType, svc: JobService) -> None:
        job = await svc.get(job_id)
        if not job:
            return

        params = json.loads(job.params_json) if job.params_json else {}

        if job_type == JobType.PROXY_TEST:
            await self._run_proxy_test(job_id, params, svc)
        elif job_type == JobType.ACCOUNT_SIMULATE:
            await self._run_account_simulation(job_id, params, svc)
        elif job_type in (JobType.BATTLENET_WORKFLOW, JobType.TWITCH_WORKFLOW):
            await self._run_workflow(job_id, params, svc)
        else:
            await svc.mark_completed(job_id, {"message": f"Job type {job_type.value} executed"})

    async def _run_proxy_test(self, job_id: int, params: dict, svc: JobService) -> None:
        from backend.app.services.proxy_service import ProxyService

        proxy_ids = params.get("proxy_ids", [])
        total = len(proxy_ids)

        async with async_session_factory() as session:
            proxy_svc = ProxyService(session)
            completed = 0
            failed = 0

            for pid in proxy_ids:
                if not self._running:
                    break
                try:
                    result = await proxy_svc.test_proxy(pid)
                    if result.status.value == "failed":
                        failed += 1
                except Exception:
                    failed += 1
                completed += 1
                progress = (completed / total * 100) if total > 0 else 100
                await svc.update_progress(job_id, progress, completed, failed)

        await svc.mark_completed(job_id, {"tested": total, "failed": failed})

    async def _run_workflow(self, job_id: int, params: dict, svc: JobService) -> None:
        workflow_execution_id = params.get("workflow_execution_id")
        if not workflow_execution_id:
            await svc.mark_failed(job_id, "Missing workflow_execution_id in params")
            return

        from backend.app.models.workflow import WorkflowExecution as WorkflowModel
        from backend.app.services.workflow_service import WorkflowService
        from backend.app.workflows.battlenet import create_battlenet_workflow
        from backend.app.workflows.engine import WorkflowEngine
        from backend.app.workflows.engine import WorkflowExecution as EngineExecution
        from backend.app.workflows.twitch import create_twitch_workflow

        async with async_session_factory() as session:
            result = await session.execute(
                select(WorkflowModel).where(WorkflowModel.id == workflow_execution_id)
            )
            wf_model = result.scalar_one_or_none()
            if not wf_model:
                await svc.mark_failed(job_id, f"Workflow execution {workflow_execution_id} not found")
                return

            from backend.app.models.account import Account
            account_result = await session.execute(
                select(Account).where(Account.id == wf_model.account_id)
            )
            account = account_result.scalar_one_or_none()

            from backend.app.services.browser_service import BrowserConfig, BrowserService

            if settings.MOCK_MODE:
                from backend.app.adapters.mock_captcha import MockCaptchaAdapter
                from backend.app.adapters.mock_mailbox import MockMailboxAdapter
                from backend.app.adapters.mock_sms import MockSMSAdapter

                browser_svc = None
                captcha_adapter = MockCaptchaAdapter()
                mailbox_adapter = MockMailboxAdapter()
                sms_adapter = MockSMSAdapter()
                logger.info("Mock mode: using mock adapters for workflow %s", workflow_execution_id)
            else:
                proxy_cfg = None
                if settings.PROXY_URL:
                    proxy_cfg = {"server": settings.PROXY_URL}

                browser_svc = BrowserService(BrowserConfig(
                    headless=settings.BROWSER_HEADLESS,
                    timeout_ms=settings.BROWSER_TIMEOUT_MS,
                    proxy=proxy_cfg,
                ))

                try:
                    await browser_svc.start()
                except Exception as exc:
                    logger.warning("Browser unavailable, workflows will run without browser: %s", exc)
                    browser_svc = None

                captcha_adapter = None
                if settings.CAPSOLVER_API_KEY and settings.CAPTCHA_SOLVE_ENABLED:
                    from backend.app.adapters.capsolver import CapSolverAdapter
                    captcha_adapter = CapSolverAdapter(api_key=settings.CAPSOLVER_API_KEY)

                mailbox_adapter = None
                sms_adapter = None
                if settings.SMS_PROVIDER_API_KEY and settings.SMS_PROVIDER_BASE_URL:
                    from backend.app.adapters.live_sms import LiveSMSAdapter
                    sms_adapter = LiveSMSAdapter(
                        api_key=settings.SMS_PROVIDER_API_KEY,
                        base_url=settings.SMS_PROVIDER_BASE_URL,
                        provider_name=settings.SMS_PROVIDER_NAME,
                    )

            if wf_model.platform == "battlenet":
                defn = create_battlenet_workflow(
                    browser_service=browser_svc,
                    mailbox_adapter=mailbox_adapter,
                    sms_adapter=sms_adapter,
                    captcha_adapter=captcha_adapter,
                )
            elif wf_model.platform == "twitch":
                defn = create_twitch_workflow(
                    browser_service=browser_svc,
                    captcha_adapter=captcha_adapter,
                )
            else:
                if browser_svc:
                    await browser_svc.stop()
                await svc.mark_failed(job_id, f"Unknown platform: {wf_model.platform}")
                return

            execution = EngineExecution(defn, wf_model.account_id)
            execution.context["mock_mode"] = settings.MOCK_MODE
            if account:
                execution.context["email"] = account.email
                if account.display_name:
                    execution.context["display_name"] = account.display_name

            engine = WorkflowEngine()
            try:
                execution = await engine.run(execution)
            finally:
                if browser_svc:
                    await browser_svc.stop()

            if account and execution.context.get("generated_username"):
                account.display_name = execution.context["generated_username"]
            if account and execution.context.get("generated_password"):
                from backend.app.core.security import encrypt_value
                account.credentials_enc = encrypt_value(execution.context["generated_password"])
            if execution.status.value == "completed":
                from backend.app.models.enums import AccountStatus
                if account:
                    if wf_model.platform == "twitch":
                        account.status = AccountStatus.UNVERIFIED
                    else:
                        account.status = AccountStatus.VERIFIED_LIVE

            wf_svc = WorkflowService(session)
            await wf_svc.update_from_execution(workflow_execution_id, execution)
            await session.commit()

            await svc.mark_completed(job_id, {
                "workflow_status": execution.status.value,
                "steps_completed": len(execution.step_results),
            })

    async def _run_account_simulation(self, job_id: int, params: dict, svc: JobService) -> None:
        """
        Simulates account creation workflow with mock states.
        This NEVER contacts Battle.net or Twitch — it only updates local records.
        """
        await asyncio.sleep(1)
        await svc.update_progress(job_id, 25.0)
        await asyncio.sleep(1)
        await svc.update_progress(job_id, 50.0)
        await asyncio.sleep(1)
        await svc.update_progress(job_id, 75.0)
        await asyncio.sleep(1)
        await svc.mark_completed(job_id, {
            "message": "Simulation complete",
            "is_mock": True,
            "note": "No live account operations were performed",
        })


worker_supervisor = WorkerSupervisor()
