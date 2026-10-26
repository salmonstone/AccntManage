from __future__ import annotations

import logging
import re
import time
from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import encrypt_value
from backend.app.models.enums import ProxyProtocol, ProxyTestStatus
from backend.app.models.proxy import Proxy
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.proxy import ProxyCreate, ProxyResponse, ProxyTestResult

logger = logging.getLogger(__name__)

PROXY_TEST_URL = "https://httpbin.org/ip"
PROXY_TEST_TIMEOUT = 15


class ProxyService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: ProxyCreate) -> Proxy:
        existing = await self._session.execute(
            select(Proxy).where(Proxy.host == data.host, Proxy.port == data.port)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Proxy already exists: {data.host}:{data.port}")

        proxy = Proxy(
            protocol=data.protocol,
            host=data.host,
            port=data.port,
            username=data.username,
            encrypted_password=encrypt_value(data.password) if data.password else None,
        )
        self._session.add(proxy)
        await self._session.commit()
        return proxy

    async def get(self, proxy_id: int) -> Proxy | None:
        result = await self._session.execute(select(Proxy).where(Proxy.id == proxy_id))
        return result.scalar_one_or_none()

    async def list_proxies(
        self,
        status: ProxyTestStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> PaginatedResponse[ProxyResponse]:
        query = select(Proxy)
        count_query = select(func.count(Proxy.id))

        if status:
            query = query.where(Proxy.test_status == status)
            count_query = count_query.where(Proxy.test_status == status)

        total = (await self._session.execute(count_query)).scalar() or 0
        offset = (page - 1) * page_size
        result = await self._session.execute(
            query.order_by(Proxy.created_at.desc()).offset(offset).limit(page_size)
        )
        items = [ProxyResponse.model_validate(p) for p in result.scalars().all()]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    async def delete(self, proxy_id: int) -> None:
        proxy = await self.get(proxy_id)
        if not proxy:
            raise ValueError("Proxy not found")
        await self._session.delete(proxy)
        await self._session.commit()

    async def test_proxy(self, proxy_id: int) -> ProxyTestResult:
        proxy = await self.get(proxy_id)
        if not proxy:
            raise ValueError("Proxy not found")

        proxy.test_status = ProxyTestStatus.TESTING
        await self._session.commit()

        proxy_url = f"{proxy.protocol.value}://"
        if proxy.username:
            proxy_url += f"{proxy.username}:****@"
        proxy_url += f"{proxy.host}:{proxy.port}"

        try:
            start = time.monotonic()
            transport = httpx.AsyncHTTPTransport(proxy=proxy_url.replace("****", ""))
            async with httpx.AsyncClient(transport=transport, timeout=PROXY_TEST_TIMEOUT) as client:
                resp = await client.get(PROXY_TEST_URL)
                resp.raise_for_status()
            latency = (time.monotonic() - start) * 1000

            proxy.test_status = ProxyTestStatus.PASSED
            proxy.last_latency_ms = latency
            proxy.last_error = None
            proxy.last_test_at = datetime.now(UTC)
            await self._session.commit()

            return ProxyTestResult(
                proxy_id=proxy_id,
                status=ProxyTestStatus.PASSED,
                latency_ms=latency,
                ip_address=resp.json().get("origin"),
                dns_ok=True,
                tls_ok=True,
            )
        except httpx.TimeoutException:
            proxy.test_status = ProxyTestStatus.TIMEOUT
            proxy.last_error = "Connection timed out"
            proxy.last_test_at = datetime.now(UTC)
            await self._session.commit()
            return ProxyTestResult(proxy_id=proxy_id, status=ProxyTestStatus.TIMEOUT, error="Timeout")
        except Exception as e:
            error_msg = str(e)[:500]
            proxy.test_status = ProxyTestStatus.FAILED
            proxy.last_error = error_msg
            proxy.last_test_at = datetime.now(UTC)
            await self._session.commit()
            return ProxyTestResult(proxy_id=proxy_id, status=ProxyTestStatus.FAILED, error=error_msg)

    async def import_proxies(self, raw_text: str, default_protocol: ProxyProtocol) -> dict:
        lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
        imported = 0
        skipped = 0
        invalid = 0

        for line in lines:
            parsed = self._parse_proxy_line(line, default_protocol)
            if not parsed:
                invalid += 1
                continue
            existing = await self._session.execute(
                select(Proxy).where(Proxy.host == parsed["host"], Proxy.port == parsed["port"])
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            proxy = Proxy(
                protocol=parsed["protocol"],
                host=parsed["host"],
                port=parsed["port"],
                username=parsed.get("username"),
                encrypted_password=encrypt_value(parsed["password"]) if parsed.get("password") else None,
            )
            self._session.add(proxy)
            imported += 1

        await self._session.commit()
        return {"imported": imported, "skipped": skipped, "invalid": invalid}

    @staticmethod
    def _parse_proxy_line(line: str, default_protocol: ProxyProtocol) -> dict | None:
        protocol = default_protocol
        for proto in ProxyProtocol:
            if line.lower().startswith(f"{proto.value}://"):
                protocol = proto
                line = line[len(f"{proto.value}://"):]
                break

        parts = re.split(r"[:@]", line)
        if len(parts) < 2:
            return None

        try:
            if len(parts) == 2:
                return {"protocol": protocol, "host": parts[0], "port": int(parts[1])}
            elif len(parts) == 4:
                return {
                    "protocol": protocol,
                    "host": parts[0],
                    "port": int(parts[1]),
                    "username": parts[2],
                    "password": parts[3],
                }
        except (ValueError, IndexError):
            return None
        return None
