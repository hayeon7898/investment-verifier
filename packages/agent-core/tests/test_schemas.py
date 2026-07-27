"""도구 스키마 계약 테스트.

spec: specs/agent-behavior.md#2

각 도구가 스펙에 정의된 필드를 정확히 가지고 있는지, 잘못된 입력을
거부하는지 검증한다. 이 테스트가 통과해야 이후 ReAct 루프/하네스가
이 스키마를 신뢰하고 사용할 수 있다.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from agent_core.tools.schemas import (
    DateRange,
    GetMacroIndicatorInput,
    GetPriceHistoryInput,
    GetPriceHistoryOutput,
    MatchedPeriod,
    PricePoint,
    RunBacktestInput,
    RunBacktestOutput,
    SearchNewsInput,
)

# ---------------------------------------------------------------------------
# get_price_history
# ---------------------------------------------------------------------------


def test_get_price_history_input_valid():
    payload = GetPriceHistoryInput(
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        interval="1d",
    )
    assert payload.ticker == "AAPL"


def test_get_price_history_input_rejects_invalid_interval():
    with pytest.raises(ValidationError):
        GetPriceHistoryInput(
            ticker="AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            interval="1h",  # 스펙에 없는 값
        )


def test_get_price_history_input_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        GetPriceHistoryInput(
            ticker="AAPL",
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),
        )


def test_get_price_history_output_shape():
    output = GetPriceHistoryOutput(
        ticker="AAPL",
        prices=[PricePoint(date=date(2024, 1, 2), close=185.0)],
        source="yfinance",
    )
    assert output.prices[0].close == 185.0


# ---------------------------------------------------------------------------
# get_macro_indicator
# ---------------------------------------------------------------------------


def test_get_macro_indicator_rejects_unknown_indicator():
    with pytest.raises(ValidationError):
        GetMacroIndicatorInput(
            indicator="gdp_growth",  # 스펙에 정의되지 않은 지표
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )


def test_get_macro_indicator_accepts_known_indicator():
    payload = GetMacroIndicatorInput(
        indicator="fed_funds_rate",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )
    assert payload.indicator == "fed_funds_rate"


# ---------------------------------------------------------------------------
# run_backtest
# ---------------------------------------------------------------------------


def test_run_backtest_input_rejects_non_positive_lookback():
    with pytest.raises(ValidationError):
        RunBacktestInput(condition="금리 하락기", target_ticker="QQQ", lookback_years=0)


def test_run_backtest_output_rejects_win_rate_out_of_range():
    with pytest.raises(ValidationError):
        RunBacktestOutput(
            win_rate=1.5,  # 0~1 범위를 벗어남
            avg_return=0.08,
            sample_size=12,
            matched_periods=[MatchedPeriod(start=date(2020, 1, 1), end=date(2020, 6, 1))],
        )


# ---------------------------------------------------------------------------
# search_news
# ---------------------------------------------------------------------------


def test_search_news_input_allows_null_date_range():
    payload = SearchNewsInput(query="기준금리 인하", date_range=None)
    assert payload.date_range is None


def test_search_news_date_range_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        DateRange(start=date(2024, 12, 31), end=date(2024, 1, 1))