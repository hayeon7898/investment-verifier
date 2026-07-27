"""도구 함수 시그니처.

spec: specs/agent-behavior.md#2

이 단계에서는 인터페이스만 확정하고 실제 구현은 하지 않는다.
실제 연동(yfinance / FinanceDataReader / FRED / 뉴스 API)은 후속 이슈에서
harness의 재시도·타임아웃·캐시 로직과 함께 구현한다.
"""

from __future__ import annotations

from agent_core.tools.schemas import (
    GetMacroIndicatorInput,
    GetMacroIndicatorOutput,
    GetPriceHistoryInput,
    GetPriceHistoryOutput,
    RunBacktestInput,
    RunBacktestOutput,
    SearchNewsInput,
    SearchNewsOutput,
)


def get_price_history(payload: GetPriceHistoryInput) -> GetPriceHistoryOutput:
    """spec: agent-behavior.md#2.1"""
    raise NotImplementedError("get_price_history: 실제 시세 API 연동은 후속 이슈에서 구현")


def get_macro_indicator(payload: GetMacroIndicatorInput) -> GetMacroIndicatorOutput:
    """spec: agent-behavior.md#2.2"""
    raise NotImplementedError("get_macro_indicator: FRED 연동은 후속 이슈에서 구현")


def run_backtest(payload: RunBacktestInput) -> RunBacktestOutput:
    """spec: agent-behavior.md#2.3"""
    raise NotImplementedError("run_backtest: 백테스트 계산 로직은 후속 이슈에서 구현")


def search_news(payload: SearchNewsInput) -> SearchNewsOutput:
    """spec: agent-behavior.md#2.4"""
    raise NotImplementedError("search_news: 뉴스 API 연동은 후속 이슈에서 구현")