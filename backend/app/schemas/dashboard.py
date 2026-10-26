from __future__ import annotations

from pydantic import BaseModel

from backend.app.models.enums import AccountStatus, JobStatus


class DashboardMetrics(BaseModel):
    total_battlenet_accounts: int = 0
    total_twitch_accounts: int = 0
    total_mailboxes: int = 0
    total_proxies: int = 0
    active_jobs: int = 0
    completed_jobs_24h: int = 0
    failed_jobs_24h: int = 0
    accounts_by_status: dict[str, int] = {}
    proxies_passed: int = 0
    proxies_failed: int = 0
    mailboxes_authorized: int = 0


class RecentActivity(BaseModel):
    id: int
    action: str
    entity_type: str | None
    details: str | None
    created_at: str
