"""도구 호출 실행기.

spec: specs/ARCHITECTURE.md#4.4, specs/agent-behavior.md#2

동작 순서 (도구 1회 호출당):
1. 타임아웃 안에서 도구 함수 실행
2. 결과를 output_model로 검증
3. 실패(타임아웃/검증 실패/예외) 시 1회 재시도
4. 재시도도 실패하면 fallback_fn이 있으면 폴백 실행, 없으면 ToolExecutionError
5. 성공/실패/폴백 여부와 관계없이 결과를 감사 로그에 기록
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agent_core.harness.audit import AuditLog, ToolCallResult
from agent_core.harness.errors import ToolExecutionError, ToolTimeoutError

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolHarness:
    def __init__(
        self,
        audit_log: AuditLog,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ) -> None:
        self._audit_log = audit_log
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def call(
        self,
        tool_name: str,
        fn: Callable[[InputT], OutputT],
        payload: InputT,
        output_model: type[OutputT],
        fallback_fn: Callable[[InputT], OutputT] | None = None,
    ) -> ToolCallResult:
        """도구를 호출하고, 실패 시 재시도/폴백을 적용한 뒤 감사 로그에 기록한다.

        성공하면 `ToolCallResult.success=True`, `output`에 검증된 결과가 담긴다.
        재시도와 폴백을 모두 소진하면 `ToolExecutionError`를 raise한다
        (그 경우에도 실패 기록은 감사 로그에 남는다).
        """
        start = time.monotonic()
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 2):  # 최초 시도 + max_retries
            try:
                raw = self._run_with_timeout(fn, payload)
                validated = self._validate_output(raw, output_model)
                return self._record(
                    tool_name, success=True, attempts=attempt,
                    start=start, used_fallback=False, output=validated,
                )
            except (ToolTimeoutError, ValidationError, Exception) as exc:
                last_error = exc
                continue

        if fallback_fn is not None:
            try:
                raw = self._run_with_timeout(fallback_fn, payload)
                validated = self._validate_output(raw, output_model)
                return self._record(
                    tool_name, success=True, attempts=self._max_retries + 1,
                    start=start, used_fallback=True, output=validated,
                )
            except Exception as exc:  # noqa: BLE001 - 폴백까지 실패하면 최종 실패로 처리
                last_error = exc

        self._record(
            tool_name, success=False, attempts=self._max_retries + 1,
            start=start, used_fallback=False, error=str(last_error),
        )
        raise ToolExecutionError(tool_name, self._max_retries + 1, last_error)

    def _run_with_timeout(self, fn: Callable[[InputT], OutputT], payload: InputT) -> OutputT:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, payload)
            try:
                return future.result(timeout=self._timeout_seconds)
            except FutureTimeoutError as exc:
                raise ToolTimeoutError(
                    f"도구 실행이 {self._timeout_seconds}초를 초과했습니다"
                ) from exc

    @staticmethod
    def _validate_output(raw: object, output_model: type[OutputT]) -> OutputT:
        if isinstance(raw, output_model):
            return raw
        return output_model.model_validate(raw)

    def _record(
        self,
        tool_name: str,
        *,
        success: bool,
        attempts: int,
        start: float,
        used_fallback: bool,
        output: object | None = None,
        error: str | None = None,
    ) -> ToolCallResult:
        result = ToolCallResult(
            tool_name=tool_name,
            success=success,
            attempts=attempts,
            latency_ms=(time.monotonic() - start) * 1000,
            used_fallback=used_fallback,
            output=output,
            error=error,
        )
        self._audit_log.append(result)
        return result