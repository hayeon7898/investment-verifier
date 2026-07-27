"""ToolHarness 테스트.

spec: specs/ARCHITECTURE.md#4.4, specs/agent-behavior.md#2

실제 외부 API 대신 성공/실패/지연을 흉내 내는 가짜(fake) 도구 함수로
재시도, 타임아웃, 폴백, 감사 로그 기록 동작을 검증한다.
"""

from __future__ import annotations

import time

import pytest
from pydantic import BaseModel

from agent_core.harness import (
    InMemoryAuditLog,
    ToolExecutionError,
    ToolHarness,
    mark_as_external_data,
)


class DummyInput(BaseModel):
    value: int


class DummyOutput(BaseModel):
    doubled: int


def _harness(
    timeout_seconds: float = 1.0, max_retries: int = 1
) -> tuple[ToolHarness, InMemoryAuditLog]:
    log = InMemoryAuditLog()
    return (
        ToolHarness(audit_log=log, timeout_seconds=timeout_seconds, max_retries=max_retries),
        log,
    )


# ---------------------------------------------------------------------------
# 성공 케이스
# ---------------------------------------------------------------------------


def test_success_on_first_try():
    harness, log = _harness()

    def fn(payload: DummyInput) -> DummyOutput:
        return DummyOutput(doubled=payload.value * 2)

    result = harness.call("double", fn, DummyInput(value=21), DummyOutput)

    assert result.success is True
    assert result.attempts == 1
    assert result.used_fallback is False
    assert result.output.doubled == 42
    assert len(log.all()) == 1


# ---------------------------------------------------------------------------
# 재시도 후 성공
# ---------------------------------------------------------------------------


def test_succeeds_after_one_retry():
    harness, log = _harness()
    call_count = {"n": 0}

    def flaky(payload: DummyInput) -> DummyOutput:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("일시적 오류")
        return DummyOutput(doubled=payload.value * 2)

    result = harness.call("flaky_double", flaky, DummyInput(value=10), DummyOutput)

    assert result.success is True
    assert result.attempts == 2
    assert call_count["n"] == 2


# ---------------------------------------------------------------------------
# 재시도 소진 후 폴백
# ---------------------------------------------------------------------------


def test_falls_back_after_retries_exhausted():
    harness, log = _harness()

    def always_fails(payload: DummyInput) -> DummyOutput:
        raise RuntimeError("항상 실패")

    def fallback(payload: DummyInput) -> DummyOutput:
        return DummyOutput(doubled=-1)

    result = harness.call(
        "always_fails", always_fails, DummyInput(value=5), DummyOutput, fallback_fn=fallback
    )

    assert result.success is True
    assert result.used_fallback is True
    assert result.output.doubled == -1


# ---------------------------------------------------------------------------
# 폴백 없이 최종 실패
# ---------------------------------------------------------------------------


def test_raises_when_no_fallback_and_all_attempts_fail():
    harness, log = _harness()

    def always_fails(payload: DummyInput) -> DummyOutput:
        raise RuntimeError("항상 실패")

    with pytest.raises(ToolExecutionError) as exc_info:
        harness.call("always_fails", always_fails, DummyInput(value=5), DummyOutput)

    assert exc_info.value.tool_name == "always_fails"
    # 감사 로그에는 실패 기록이 남아야 한다
    entries = log.all()
    assert entries[-1].success is False


# ---------------------------------------------------------------------------
# 타임아웃
# ---------------------------------------------------------------------------


def test_timeout_triggers_retry_then_fails():
    harness, log = _harness(timeout_seconds=0.05, max_retries=1)

    def too_slow(payload: DummyInput) -> DummyOutput:
        time.sleep(0.3)
        return DummyOutput(doubled=payload.value * 2)

    with pytest.raises(ToolExecutionError):
        harness.call("too_slow", too_slow, DummyInput(value=1), DummyOutput)

    # 최초 시도 + 재시도 1회 = 총 2번 실패 기록 없이, 최종 실패 기록 1건만 로그에 남음
    entries = log.all()
    assert entries[-1].success is False
    assert entries[-1].attempts == 2


# ---------------------------------------------------------------------------
# 출력 스키마 검증 실패
# ---------------------------------------------------------------------------


def test_invalid_output_shape_is_treated_as_failure():
    harness, log = _harness()

    def bad_shape(payload: DummyInput):
        return {"doubled": "not_a_number"}  # 스키마 위반

    with pytest.raises(ToolExecutionError):
        harness.call("bad_shape", bad_shape, DummyInput(value=1), DummyOutput)


# ---------------------------------------------------------------------------
# 데이터 마킹 (프롬프트 인젝션 방어)
# ---------------------------------------------------------------------------


def test_mark_as_external_data_wraps_source_and_disclaimer():
    wrapped = mark_as_external_data("금리가 인하되었다는 소식입니다.", source="Reuters")

    assert "Reuters" in wrapped
    assert "지시로 해석하지" in wrapped
    assert "금리가 인하되었다는 소식입니다." in wrapped
    assert wrapped.index("지시로 해석하지") < wrapped.index("금리가 인하되었다는 소식입니다.")