"""도구 입출력 스키마 정의.

spec: specs/agent-behavior.md#2 (도구 스키마)

여기 정의된 모델은 ReAct 루프의 도구 하네스(harness/)가 모든 도구 호출의
입력/출력을 강제 검증하는 데 사용된다. 필드를 변경할 때는 반드시
agent-behavior.md#2도 함께 갱신한다.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# 2.1 get_price_history
# ---------------------------------------------------------------------------

Interval = Literal["1d", "1wk", "1mo"]


class GetPriceHistoryInput(BaseModel):
    ticker: str = Field(min_length=1)
    start_date: date
    end_date: date
    interval: Interval = "1d"

    @model_validator(mode="after")
    def check_date_order(self) -> GetPriceHistoryInput:
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 이후일 수 없습니다")
        return self


class PricePoint(BaseModel):
    date: date
    close: float


class GetPriceHistoryOutput(BaseModel):
    ticker: str
    prices: list[PricePoint]
    source: str


# ---------------------------------------------------------------------------
# 2.2 get_macro_indicator
# ---------------------------------------------------------------------------

MacroIndicator = Literal["fed_funds_rate", "cpi", "unemployment_rate"]


class GetMacroIndicatorInput(BaseModel):
    indicator: MacroIndicator
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_date_order(self) -> GetMacroIndicatorInput:
        if self.start_date > self.end_date:
            raise ValueError("start_date는 end_date보다 이후일 수 없습니다")
        return self


class MacroValuePoint(BaseModel):
    date: date
    value: float


class GetMacroIndicatorOutput(BaseModel):
    indicator: str
    values: list[MacroValuePoint]
    source: str


# ---------------------------------------------------------------------------
# 2.3 run_backtest
# ---------------------------------------------------------------------------


class RunBacktestInput(BaseModel):
    condition: str = Field(min_length=1, description="예: '금리 하락기'")
    target_ticker: str = Field(min_length=1)
    lookback_years: int = Field(gt=0, le=50)


class MatchedPeriod(BaseModel):
    start: date
    end: date


class RunBacktestOutput(BaseModel):
    win_rate: float = Field(ge=0.0, le=1.0)
    avg_return: float
    sample_size: int = Field(ge=0)
    matched_periods: list[MatchedPeriod]


# ---------------------------------------------------------------------------
# 2.4 search_news
# ---------------------------------------------------------------------------


class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_date_order(self) -> DateRange:
        if self.start > self.end:
            raise ValueError("start는 end보다 이후일 수 없습니다")
        return self


class SearchNewsInput(BaseModel):
    query: str = Field(min_length=1)
    date_range: DateRange | None = None


class NewsArticle(BaseModel):
    title: str
    summary: str
    published_at: date
    source: str


class SearchNewsOutput(BaseModel):
    # spec 주의: 이 결과는 프롬프트 삽입 시 반드시 "데이터"로 마킹되어야 하며
    # 모델이 지시로 해석하지 않도록 harness 단계에서 래핑한다.
    articles: list[NewsArticle]