from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    accounts,
    auth,
    backups,
    dashboard,
    diagnostics,
    health,
    jobs,
    mailboxes,
    providers,
    proxies,
    settings_routes,
    workflows,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(accounts.router)
api_router.include_router(mailboxes.router)
api_router.include_router(proxies.router)
api_router.include_router(jobs.router)
api_router.include_router(providers.router)
api_router.include_router(settings_routes.router)
api_router.include_router(backups.router)
api_router.include_router(diagnostics.router)
api_router.include_router(workflows.router)
