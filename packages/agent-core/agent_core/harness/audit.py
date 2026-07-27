"""도구 호출 감사 로그.

spec: specs/ARCHITECTURE.md#5 (보안/거버넌스 — 모든 도구 호출·모델 호출을 감사 로그로 보존)

지금은 in-memory 구현체만 제공한다. 백엔드 연동 시 Postgres에 적재하는
구현체(예: `PostgresAuditLog`)를 추가하되, 이 모듈의 `AuditLog` 인터페이스는
그대로 유지해 harness/runner.py가 구현체를 몰라도 되게 한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field


class ToolCallResult(BaseModel):
    """도구 호출 1건에 대한 감사 기록."""

    tool_name: str
    success: bool
    attempts: int
    latency_ms: float
    used_fallback: bool
    output: Any | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditLog(Protocol):
    """감사 로그 저장소 인터페이스. 구현체를 교체해도 harness는 영향받지 않는다."""

    def append(self, result: ToolCallResult) -> None: ...

    def all(self) -> list[ToolCallResult]: ...


class InMemoryAuditLog:
    """개발/테스트용 in-memory 감사 로그. 프로세스 종료 시 사라진다."""

    def __init__(self) -> None:
        self._entries: list[ToolCallResult] = []

    def append(self, result: ToolCallResult) -> None:
        self._entries.append(result)

    def all(self) -> list[ToolCallResult]:
        return list(self._entries)