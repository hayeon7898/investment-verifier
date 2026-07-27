"""에이전트 정책 인터페이스.

spec: specs/agent-behavior.md#3

'다음에 뭘 할지'를 결정하는 부분을 추상화한다. 실제 구현은 Claude API를
호출하는 LLM 기반 정책이 되지만(후속 이슈), ReActLoop 자체는 이 정책이
어떻게 구현됐는지 몰라도 되도록 Protocol로만 의존한다. 덕분에 테스트에서는
결정론적인 가짜(fake) 정책을 넣어 루프의 제어 흐름만 검증할 수 있다.
"""

from __future__ import annotations

from typing import Protocol

from agent_core.react.models import AgentStep, ReActRecord


class AgentPolicy(Protocol):
    def decide(self, history: list[ReActRecord]) -> AgentStep:
        """지금까지의 기록을 보고 다음 Thought/Action(또는 결론)을 결정한다."""
        ...