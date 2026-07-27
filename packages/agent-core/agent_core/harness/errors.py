"""하네스 전용 예외.

spec: specs/ARCHITECTURE.md#4.4
"""

from __future__ import annotations


class ToolTimeoutError(Exception):
    """도구 실행이 제한 시간을 초과했을 때 발생."""


class ToolExecutionError(Exception):
    """재시도와 폴백을 모두 소진했는데도 도구 호출이 실패했을 때 발생."""

    def __init__(self, tool_name: str, attempts: int, last_error: Exception | None):
        self.tool_name = tool_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"'{tool_name}' 도구 호출 실패 ({attempts}회 시도 후, "
            f"마지막 에러: {last_error!r})"
        )