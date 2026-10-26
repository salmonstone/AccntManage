"""Microsoft Graph OAuth endpoints for mailbox authorization.

Implements the Authorization Code flow:
1. /auth/msgraph/authorize  → redirects user to Microsoft login
2. /auth/msgraph/callback   → exchanges code for tokens, stores encrypted

The state parameter uses a random nonce mapped server-side to the mailbox ID
so the mailbox_id is never exposed in the redirect URL.
"""
from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import encrypt_value
from backend.app.db.base import get_session
from backend.app.models.enums import MailboxStatus
from backend.app.models.mailbox import Mailbox

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

AUTHORITY = "https://login.microsoftonline.com"
GRAPH_SCOPES = "Mail.Read offline_access"

_pending_oauth_states: dict[str, dict] = {}


def _check_msgraph_configured() -> None:
    if not settings.MSGRAPH_CLIENT_ID or not settings.MSGRAPH_TENANT_ID:
        raise HTTPException(
            status_code=503,
            detail="Microsoft Graph not configured. Set MSGRAPH_CLIENT_ID and MSGRAPH_TENANT_ID in .env",
        )


@router.get("/msgraph/authorize")
async def msgraph_authorize(
    mailbox_id: int = Query(..., gt=0),
    session: AsyncSession = Depends(get_session),
):
    _check_msgraph_configured()

    result = await session.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    state = secrets.token_urlsafe(32)
    _pending_oauth_states[state] = {"mailbox_id": mailbox_id}

    params = {
        "client_id": settings.MSGRAPH_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.MSGRAPH_REDIRECT_URI,
        "scope": GRAPH_SCOPES,
        "state": state,
        "response_mode": "query",
    }
    auth_url = f"{AUTHORITY}/{settings.MSGRAPH_TENANT_ID}/oauth2/v2.0/authorize?{urlencode(params)}"
    return {"authorize_url": auth_url}


@router.get("/msgraph/callback")
async def msgraph_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    error_description: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    if error:
        logger.warning("OAuth error: %s — %s", error, error_description)
        raise HTTPException(status_code=400, detail=f"OAuth error: {error_description or error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    if state not in _pending_oauth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    pending = _pending_oauth_states.pop(state)
    mailbox_id = pending["mailbox_id"]

    _check_msgraph_configured()

    result = await session.execute(select(Mailbox).where(Mailbox.id == mailbox_id))
    mailbox = result.scalar_one_or_none()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    token_url = f"{AUTHORITY}/{settings.MSGRAPH_TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "client_id": settings.MSGRAPH_CLIENT_ID,
        "scope": GRAPH_SCOPES,
        "code": code,
        "redirect_uri": settings.MSGRAPH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(token_url, data=token_data)

    if resp.status_code != 200:
        logger.error("Token exchange failed: %d %s", resp.status_code, resp.text[:500])
        raise HTTPException(status_code=502, detail="Token exchange failed")

    token_resp = resp.json()
    access_token = token_resp.get("access_token", "")
    refresh_token = token_resp.get("refresh_token", "")
    expires_in = int(token_resp.get("expires_in", 3600))

    mailbox.encrypted_token = encrypt_value(access_token)
    mailbox.token_type = "bearer"
    mailbox.token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    mailbox.scopes = GRAPH_SCOPES
    mailbox.status = MailboxStatus.AUTHORIZED

    if refresh_token:
        mailbox.client_id = settings.MSGRAPH_CLIENT_ID
        mailbox.encrypted_password = encrypt_value(refresh_token)

    await session.commit()

    logger.info("Mailbox %d authorized via OAuth", mailbox_id)
    return {
        "status": "authorized",
        "mailbox_id": mailbox_id,
        "email": mailbox.email,
        "expires_in": expires_in,
    }
