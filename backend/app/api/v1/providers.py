from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.adapters.mock_captcha import MockCaptchaAdapter
from backend.app.adapters.mock_sms import MockSMSAdapter
from backend.app.core.security import encrypt_value, mask_secret
from backend.app.db.base import get_session
from backend.app.models.enums import AuditAction, ProviderStatus, ProviderType
from backend.app.models.provider import ProviderConfig
from backend.app.schemas.provider import (
    ProviderConfigResponse,
    ProviderConfigUpdate,
    ProviderHealthResult,
)
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.get("", response_model=list[ProviderConfigResponse])
async def list_providers(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ProviderConfig))
    return [ProviderConfigResponse.model_validate(p) for p in result.scalars().all()]


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
        adapter = MockSMSAdapter()
        result = await adapter.check_balance()
        return ProviderHealthResult(
            provider_type=provider_type,
            status=ProviderStatus.MOCK_ONLY,
            message=f"Mock SMS adapter active (balance: ${result['balance']})",
            is_mock=True,
        )
    elif provider_type == ProviderType.CAPTCHA:
        adapter = MockCaptchaAdapter()
        result = await adapter.check_balance()
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
