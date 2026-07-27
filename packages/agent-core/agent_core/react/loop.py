"""ReAct 루프 실행기.

spec: specs/agent-behavior.md#3

정지 조건 (하나라도 만족 시 종료):
1. 정책이 결론(conclusion)을 반환
2. 최대 반복 횟수 도달 → uncertain=True로 강제 표시
3. 동일 도구를 동일 인자로 2회 연속 호출 시도 (루프 방지)
4. 타임아웃 초과 → 마지막 관찰까지의 결과로 강제 종료
"""

from __future__ import annotations

import time
from collections.abc import Callable

from pydantic import BaseModel

from agent_core.harness.runner import ToolHarness
from agent_core.react.models import AgentStep, ReActLoopResult, ReActRecord, ToolCall
from agent_core.react.policy import AgentPolicy

ToolRegistryEntry = tuple[Callable[[BaseModel], BaseModel], type[BaseModel], type[BaseModel]]


class ReActLoop:
    def __init__(
        self,
        policy: AgentPolicy,
        tool_harness: ToolHarness,
        tool_registry: dict[str, ToolRegistryEntry],
        max_iterations: int = 6,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._policy = policy
        self._tool_harness = tool_harness
        self._tool_registry = tool_registry
        self._max_iterations = max_iterations
        self._timeout_seconds = timeout_seconds

    def run(self) -> ReActLoopResult:
        records: list[ReActRecord] = []
        last_signature: tuple[str, tuple[tuple[str, object], ...]] | None = None
        start = time.monotonic()

        for step in range(1, self._max_iterations + 1):
            if time.monotonic() - start > self._timeout_seconds:
                return ReActLoopResult(
                    conclusion=None, records=records, stopped_reason="timeout", uncertain=True
                )

            agent_step = self._policy.decide(records)

            if agent_step.action is None:
                records.append(
                    ReActRecord(step=step, thought=agent_step.thought, action=None)
                )
                return ReActLoopResult(
                    conclusion=agent_step.conclusion,
                    records=records,
                    stopped_reason="concluded",
                    uncertain=False,
                )

            signature = self._signature(agent_step.action)
            if signature == last_signature:
                records.append(
                    ReActRecord(
                        step=step,
                        thought=agent_step.thought,
                        action=agent_step.action,
                        error="동일 도구를 동일 인자로 2회 연속 호출 시도 (루프 방지)",
                    )
                )
                return ReActLoopResult(
                    conclusion=None, records=records, stopped_reason="repeated_call", uncertain=True
                )
            last_signature = signature

            records.append(self._execute(step, agent_step))

        return ReActLoopResult(
            conclusion=None, records=records, stopped_reason="max_iterations", uncertain=True
        )

    def _execute(self, step: int, agent_step: AgentStep) -> ReActRecord:
        assert agent_step.action is not None
        tool_name = agent_step.action.tool_name

        if tool_name not in self._tool_registry:
            return ReActRecord(
                step=step,
                thought=agent_step.thought,
                action=agent_step.action,
                error=f"등록되지 않은 도구: {tool_name}",
            )

        fn, input_model, output_model = self._tool_registry[tool_name]
        try:
            payload = input_model.model_validate(agent_step.action.payload)
            result = self._tool_harness.call(tool_name, fn, payload, output_model)
            return ReActRecord(
                step=step,
                thought=agent_step.thought,
                action=agent_step.action,
                observation=result.output,
            )
        except Exception as exc:  # noqa: BLE001 - 도구 실패는 관찰(에러)로 다음 스텝에 전달
            return ReActRecord(
                step=step, thought=agent_step.thought, action=agent_step.action, error=str(exc)
            )

    @staticmethod
    def _signature(action: ToolCall) -> tuple[str, tuple[tuple[str, object], ...]]:
        return (action.tool_name, tuple(sorted(action.payload.items())))