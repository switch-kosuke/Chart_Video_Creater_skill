"""DataAnalyzer のテスト"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.csv_scanner import CSVMetadata
from src.data_analyzer import DataAnalyzer, ChartType, ChartRecommendation, AnalysisError


def _make_metadata(
    has_datetime: bool = True,
    columns: list[str] | None = None,
    row_count: int = 12,
) -> CSVMetadata:
    cols = columns or (["month", "Apple", "Google", "Meta"] if has_datetime else ["name", "score"])
    return CSVMetadata(
        path=Path("dummy.csv"),
        row_count=row_count,
        columns=cols,
        dtypes={c: "object" if i == 0 else "int64" for i, c in enumerate(cols)},
        has_datetime_column=has_datetime,
        sample_rows=[{c: f"val_{c}" for c in cols}],
    )


def _mock_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


# ──────────────────────────────────────────────
# 正常系
# ──────────────────────────────────────────────

class TestAnalyzeSuccess:
    def test_returns_chart_recommendation(self):
        payload = {
            "chart_type": "bar_race",
            "reason": "時系列×複数カテゴリなのでバーレースが最適",
            "x_column": "month",
            "y_columns": ["Apple", "Google", "Meta"],
            "category_column": None,
        }
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_response(payload)
            result = DataAnalyzer().analyze(_make_metadata())

        assert isinstance(result, ChartRecommendation)
        assert result.chart_type == ChartType.BAR_RACE
        assert result.reason == "時系列×複数カテゴリなのでバーレースが最適"
        assert result.x_column == "month"
        assert result.y_columns == ["Apple", "Google", "Meta"]

    def test_returns_animated_bar(self):
        payload = {
            "chart_type": "animated_bar",
            "reason": "カテゴリ比較に棒グラフが適切",
            "x_column": "name",
            "y_columns": ["score"],
            "category_column": None,
        }
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_response(payload)
            result = DataAnalyzer().analyze(_make_metadata(has_datetime=False))

        assert result.chart_type == ChartType.ANIMATED_BAR

    def test_returns_animated_line(self):
        payload = {
            "chart_type": "animated_line",
            "reason": "時系列推移に折れ線が最適",
            "x_column": "month",
            "y_columns": ["value"],
            "category_column": None,
        }
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = _mock_response(payload)
            result = DataAnalyzer().analyze(_make_metadata(columns=["month", "value"]))

        assert result.chart_type == ChartType.ANIMATED_LINE

    def test_uses_haiku_model(self):
        payload = {
            "chart_type": "bar_race", "reason": "test",
            "x_column": "month", "y_columns": ["v"], "category_column": None,
        }
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            mock_create = MockClient.return_value.messages.create
            mock_create.return_value = _mock_response(payload)
            DataAnalyzer().analyze(_make_metadata())

        call_kwargs = mock_create.call_args.kwargs
        assert "haiku" in call_kwargs["model"]


# ──────────────────────────────────────────────
# フォールバック（APIエラー・不正JSON）
# ──────────────────────────────────────────────

class TestAnalyzeFallback:
    def test_fallback_on_api_error(self):
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = Exception("API Error")
            result = DataAnalyzer().analyze(_make_metadata())

        assert isinstance(result, ChartRecommendation)
        assert result.chart_type in ChartType.__members__.values()

    def test_fallback_on_invalid_json(self):
        msg = MagicMock()
        msg.content = [MagicMock(text="これはJSONではありません")]
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = msg
            result = DataAnalyzer().analyze(_make_metadata())

        assert isinstance(result, ChartRecommendation)

    def test_fallback_bar_race_for_time_series_multi_columns(self):
        """時系列 + 複数列 → bar_race フォールバック"""
        with patch("src.data_analyzer.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = Exception("down")
            meta = _make_metadata(has_datetime=True, columns=["month", "A", "B", "C"])
            result = DataAnalyzer()._fallback_recommend(meta)

        assert result.chart_type == ChartType.BAR_RACE

    def test_fallback_animated_line_for_time_series_single_column(self):
        """時系列 + 1列 → animated_line フォールバック"""
        meta = _make_metadata(has_datetime=True, columns=["date", "value"])
        result = DataAnalyzer()._fallback_recommend(meta)
        assert result.chart_type == ChartType.ANIMATED_LINE

    def test_fallback_animated_bar_for_no_time_series(self):
        """時系列なし → animated_bar フォールバック"""
        meta = _make_metadata(has_datetime=False, columns=["name", "score"])
        result = DataAnalyzer()._fallback_recommend(meta)
        assert result.chart_type == ChartType.ANIMATED_BAR
