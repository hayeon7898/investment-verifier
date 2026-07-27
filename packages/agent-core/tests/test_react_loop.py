"""ReActLoop 테스트.

spec: specs/agent-behavior.md#3

실제 LLM 대신 스크립트대로 움직이는 가짜 정책(FakePolicy)을 사용해
루프의 제어 흐름(정지 조건)만 검증한다.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel

from agent_core.harness import InMemoryAuditLog, ToolHarness
from agent_core.react import AgentStep, ReActLoop, ToolCall
from agent_core.react.models import ReActRecord


class DummyInput(BaseModel):
    value: int


class DummyOutput(BaseModel):
    doubled: int


def double_tool(payload: DummyInput) -> DummyOutput:
    return DummyOutput(doubled=payload.value * 2)


class FakePolicy:
    """history를 받아 미리 정해둔 함수로 다음 스텝을 결정하는 테스트용 정책."""

    def __init__(self, decide_fn: Callable[[list[ReActRecord]], AgentStep]):
        self._decide_fn = decide_fn

    def decide(self, history: list[ReActRecord]) -> AgentStep:
        return self._decide_fn(history)


def _loop(policy: FakePolicy, max_iterations: int = 6, timeout_seconds: float = 30.0) -> ReActLoop:
    harness = ToolHarness(audit_log=InMemoryAuditLog())
    registry = {"double": (double_tool, DummyInput, DummyOutput)}
    return ReActLoop(
        policy=policy,
        tool_harness=harness,
        tool_registry=registry,
        max_iterations=max_iterations,
        timeout_seconds=timeout_seconds,
    )


# ---------------------------------------------------------------------------
# 정지 조건 1: 결론 도달
# ---------------------------------------------------------------------------


def test_stops_when_policy_concludes_immediately():
    policy = FakePolicy(
        lambda history: AgentStep(thought="바로 결론", action=None, conclusion="OK")
    )
    loop = _loop(policy)

    result = loop.run()

    assert result.stopped_reason == "concluded"
    assert result.conclusion == "OK"
    assert result.uncertain is False
    assert len(result.records) == 1


def test_calls_tool_then_concludes():
    def decide(history: list[ReActRecord]) -> AgentStep:
        if len(history) == 0:
            return AgentStep(
                thought="21을 두 배로 만들어보자",
                action=ToolCall(tool_name="double", payload={"value": 21}),
            )
        return AgentStep(thought="결과 확인 완료", action=None, conclusion="42")

    loop = _loop(FakePolicy(decide))
    result = loop.run()

    assert result.stopped_reason == "concluded"
    assert result.conclusion == "42"
    assert result.records[0].observation.doubled == 42


# ---------------------------------------------------------------------------
# 정지 조건 2: 최대 반복 횟수 도달
# ---------------------------------------------------------------------------


def test_stops_at_max_iterations_and_marks_uncertain():
    def decide(history: list[ReActRecord]) -> AgentStep:
        # 매번 다른 값으로 호출해서 '반복 호출 감지'에 걸리지 않게 함
        next_value = len(history) + 1
        return AgentStep(
            thought=f"{next_value}번째 시도",
            action=ToolCall(tool_name="double", payload={"value": next_value}),
        )

    loop = _loop(FakePolicy(decide), max_iterations=6)
    result = loop.run()

    assert result.stopped_reason == "max_iterations"
    assert result.uncertain is True
    assert result.conclusion is None
    assert len(result.records) == 6


# ---------------------------------------------------------------------------
# 정지 조건 3: 동일 도구 + 동일 인자 2회 연속 호출
# ---------------------------------------------------------------------------


def test_stops_on_repeated_identical_call():
    policy = FakePolicy(
        lambda history: AgentStep(
            thought="같은 걸 또 호출",
            action=ToolCall(tool_name="double", payload={"value": 5}),
        )
    )
    loop = _loop(policy)
    result = loop.run()

    assert result.stopped_reason == "repeated_call"
    assert result.uncertain is True
    assert len(result.records) == 2  # 1회차 호출 + 2회차에서 반복 감지되어 종료


# ---------------------------------------------------------------------------
# 정지 조건 4: 타임아웃
# ---------------------------------------------------------------------------


def test_stops_on_timeout():
    def slow_decide(history: list[ReActRecord]) -> AgentStep:
        time.sleep(0.2)
        return AgentStep(
            thought="느린 정책",
            action=ToolCall(tool_name="double", payload={"value": len(history) + 1}),
        )

    loop = _loop(FakePolicy(slow_decide), max_iterations=100, timeout_seconds=0.05)
    result = loop.run()

    assert result.stopped_reason == "timeout"
    assert result.uncertain is True


# ---------------------------------------------------------------------------
# 등록되지 않은 도구 호출 시 에러가 관찰로 기록되는지
# ---------------------------------------------------------------------------


def test_unknown_tool_is_recorded_as_error_not_crash():
    def decide(history: list[ReActRecord]) -> AgentStep:
        if len(history) == 0:
            return AgentStep(
                thought="없는 도구 호출",
                action=ToolCall(tool_name="does_not_exist", payload={}),
            )
        return AgentStep(thought="포기하고 결론", action=None, conclusion="불확실")

    loop = _loop(FakePolicy(decide))
    result = loop.run()

    assert result.records[0].error is not None
    assert result.stopped_reason == "concluded"