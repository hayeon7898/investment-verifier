"""ReAct 루프 데이터 모델.

spec: specs/agent-behavior.md#3
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ToolCall(BaseModel):
    """에이전트가 다음에 실행하고 싶은 도구 호출."""

    tool_name: str
    payload: dict[str, Any]


class AgentStep(BaseModel):
    """정책(policy)이 한 스텝마다 반환하는 결정.

    action이 None이면 결론에 도달한 것으로 간주하고 conclusion을 채운다.
    action이 있으면 conclusion은 무시된다.
    """

    thought: str
    action: ToolCall | None = None
    conclusion: str | None = None


class ReActRecord(BaseModel):
    """루프 1스텝의 실행 기록 (Thought-Action-Observation)."""

    step: int
    thought: str
    action: ToolCall | None = None
    observation: Any | None = None
    error: str | None = None


StopReason = Literal["concluded", "max_iterations", "repeated_call", "timeout"]


class ReActLoopResult(BaseModel):
    """루프 전체 실행 결과."""

    conclusion: str | None
    records: list[ReActRecord]
    stopped_reason: StopReason
    uncertain: bool = False