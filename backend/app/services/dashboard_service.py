from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.account import Account
from backend.app.models.audit import AuditLog
from backend.app.models.enums import (
    AccountPlatform,
    AccountStatus,
    JobStatus,
    MailboxStatus,
    ProxyTestStatus,
)

MOCK_STATUSES = {AccountStatus.SIMULATED, AccountStatus.MOCKED, AccountStatus.LOCAL_RECORD_ONLY}
LIVE_STATUSES = {AccountStatus.VERIFIED_LIVE, AccountStatus.REGISTRATION_CONFIRMED, AccountStatus.VERIFIED}
from backend.app.models.job import Job
from backend.app.models.mailbox import Mailbox
from backend.app.models.proxy import Proxy
from backend.app.schemas.dashboard import ActivityDay, DashboardMetrics, RecentActivity


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_metrics(self) -> DashboardMetrics:
        now = datetime.now(UTC)
        day_ago = now - timedelta(hours=24)

        bnet = (await self._session.execute(
            select(func.count(Account.id)).where(Account.platform == AccountPlatform.BATTLENET)
        )).scalar() or 0

        twitch = (await self._session.execute(
            select(func.count(Account.id)).where(Account.platform == AccountPlatform.TWITCH)
        )).scalar() or 0

        mailboxes = (await self._session.execute(select(func.count(Mailbox.id)))).scalar() or 0
        proxies = (await self._session.execute(select(func.count(Proxy.id)))).scalar() or 0

        active_jobs = (await self._session.execute(
            select(func.count(Job.id)).where(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
        )).scalar() or 0

        completed_24h = (await self._session.execute(
            select(func.count(Job.id)).where(
                Job.status == JobStatus.COMPLETED, Job.completed_at >= day_ago
            )
        )).scalar() or 0

        failed_24h = (await self._session.execute(
            select(func.count(Job.id)).where(
                Job.status == JobStatus.FAILED, Job.completed_at >= day_ago
            )
        )).scalar() or 0

        status_rows = (await self._session.execute(
            select(Account.status, func.count(Account.id)).group_by(Account.status)
        )).all()
        accounts_by_status = {str(row[0].value): row[1] for row in status_rows}

        proxies_passed = (await self._session.execute(
            select(func.count(Proxy.id)).where(Proxy.test_status == ProxyTestStatus.PASSED)
        )).scalar() or 0

        proxies_failed = (await self._session.execute(
            select(func.count(Proxy.id)).where(Proxy.test_status == ProxyTestStatus.FAILED)
        )).scalar() or 0

        mailboxes_auth = (await self._session.execute(
            select(func.count(Mailbox.id)).where(Mailbox.status == MailboxStatus.AUTHORIZED)
        )).scalar() or 0

        mock_accounts = (await self._session.execute(
            select(func.count(Account.id)).where(Account.status.in_(MOCK_STATUSES))
        )).scalar() or 0

        live_accounts = (await self._session.execute(
            select(func.count(Account.id)).where(Account.status.in_(LIVE_STATUSES))
        )).scalar() or 0

        job_status_rows = (await self._session.execute(
            select(Job.status, func.count(Job.id)).group_by(Job.status)
        )).all()
        job_status_breakdown = {str(row[0].value): row[1] for row in job_status_rows}

        seven_days_ago = now - timedelta(days=7)
        activity_timeline: list[ActivityDay] = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            day_count = (await self._session.execute(
                select(func.count(Job.id)).where(
                    Job.created_at >= day_start, Job.created_at < day_end
                )
            )).scalar() or 0
            activity_timeline.append(ActivityDay(
                date=day_start.strftime("%Y-%m-%d"),
                count=day_count,
            ))

        return DashboardMetrics(
            total_battlenet_accounts=bnet,
            total_twitch_accounts=twitch,
            total_mailboxes=mailboxes,
            total_proxies=proxies,
            active_jobs=active_jobs,
            completed_jobs_24h=completed_24h,
            failed_jobs_24h=failed_24h,
            accounts_by_status=accounts_by_status,
            proxies_passed=proxies_passed,
            proxies_failed=proxies_failed,
            mailboxes_authorized=mailboxes_auth,
            live_accounts=live_accounts,
            mock_accounts=mock_accounts,
            job_status_breakdown=job_status_breakdown,
            activity_timeline=activity_timeline,
        )

    async def get_recent_activity(self, limit: int = 20) -> list[RecentActivity]:
        result = await self._session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        )
        return [
            RecentActivity(
                id=log.id,
                action=log.action.value,
                entity_type=log.entity_type,
                details=log.details,
                created_at=log.created_at.isoformat(),
            )
            for log in result.scalars().all()
        ]
