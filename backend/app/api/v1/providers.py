from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.adapters.mock_captcha import MockCaptchaAdapter
from backend.app.adapters.mock_sms import MockSMSAdapter
from backend.app.api.v1.health import _resolve_provider_status
from backend.app.core.security import encrypt_value
from backend.app.db.base import get_session
from backend.app.models.enums import AuditAction, ProviderStatus, ProviderType
from backend.app.models.provider import ProviderConfig
from backend.app.schemas.provider import (
    ProviderConfigResponse,
    ProviderConfigUpdate,
    ProviderHealthResult,
    ProviderStatusSummary,
)
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/providers", tags=["Providers"])

_PROVIDER_CAPABILITIES: dict[str, list[str]] = {
    "sms": ["send_sms", "check_balance", "receive_code"],
    "captcha": ["solve_captcha", "check_balance"],
    "msgraph": ["oauth_authorize", "read_mail", "search_messages", "validate_token"],
    "browser": ["launch", "screenshot", "navigate", "close"],
}


@router.get("", response_model=list[ProviderConfigResponse])
async def list_providers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ProviderConfig))
    return [ProviderConfigResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/status/all", response_model=list[ProviderStatusSummary])
async def get_all_provider_statuses():
    results = []
    for name in ("sms", "captcha", "msgraph", "browser"):
        status = _resolve_provider_status(name)
        is_mock = status in (ProviderStatus.MOCK_ONLY, ProviderStatus.UNCONFIGURED, ProviderStatus.DISABLED)
        results.append(ProviderStatusSummary(
            provider=name,
            status=status,
            is_mock=is_mock,
            capabilities=_PROVIDER_CAPABILITIES.get(name, []),
        ))
    return results


@router.get("/{provider_type}", response_model=ProviderConfigResponse)
async def get_provider(provider_type: ProviderType, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ProviderConfig).where(ProviderConfig.provider_type == provider_type)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not configured")
    return ProviderConfigResponse.model_validate(provider)


@router.put("/{provider_type}", response_model=ProviderConfigResponse)
async def update_provider(
    provider_type: ProviderType,
    data: ProviderConfigUpdate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProviderConfig).where(ProviderConfig.provider_type == provider_type)
    )
    provider = result.scalar_one_or_none()
    if not provider:
        provider = ProviderConfig(provider_type=provider_type)
        session.add(provider)

    if data.config_values:
        provider.encrypted_config_json = encrypt_value(json.dumps(data.config_values))
        provider.status = ProviderStatus.CONFIGURED
    if data.notes is not None:
        provider.notes = data.notes

    audit = AuditService(session)
    await audit.log(AuditAction.PROVIDER_CONFIGURED, "provider", details=provider_type.value)
    await session.commit()
    return ProviderConfigResponse.model_validate(provider)


@router.post("/{provider_type}/health", response_model=ProviderHealthResult)
async def check_health(provider_type: ProviderType, session: AsyncSession = Depends(get_session)):
    if provider_type == ProviderType.SMS:
        sms_adapter = MockSMSAdapter()
        result = await sms_adapter.check_balance()
        return ProviderHealthResult(
            provider_type=provider_type,
            status=ProviderStatus.MOCK_ONLY,
            message=f"Mock SMS adapter active (balance: ${result['balance']})",
            is_mock=True,
        )
    elif provider_type == ProviderType.CAPTCHA:
        captcha_adapter = MockCaptchaAdapter()
        result = await captcha_adapter.check_balance()
        return ProviderHealthResult(
            provider_type=provider_type,
            status=ProviderStatus.MOCK_ONLY,
            message=MockCaptchaAdapter.POLICY_MESSAGE,
            is_mock=True,
        )
    elif provider_type == ProviderType.MSGRAPH:
        return ProviderHealthResult(
            provider_type=provider_type,
            status=ProviderStatus.UNCONFIGURED,
            message="Microsoft Graph requires OAuth configuration. See Settings > Microsoft Graph.",
            is_mock=False,
        )
    raise HTTPException(status_code=400, detail="Unknown provider type")
