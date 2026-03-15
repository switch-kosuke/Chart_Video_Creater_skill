"""ChartGenerator のテスト（bcr / matplotlib はモック）"""
from __future__ import annotations

import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.models import ChartRecommendation, ChartType
from src.theme_manager import ThemeManager
from src.chart_generator import ChartGenerator, VideoConfig


# ── フィクスチャ ──────────────────────────────────

@pytest.fixture
def theme():
    return ThemeManager().get_theme("dark")


@pytest.fixture
def bar_race_rec():
    return ChartRecommendation(
        chart_type=ChartType.BAR_RACE,
        reason="test",
        x_column="month",
        y_columns=["Apple", "Google", "Meta"],
    )


@pytest.fixture
def animated_bar_rec():
    return ChartRecommendation(
        chart_type=ChartType.ANIMATED_BAR,
        reason="test",
        x_column="name",
        y_columns=["score"],
    )


@pytest.fixture
def animated_line_rec():
    return ChartRecommendation(
        chart_type=ChartType.ANIMATED_LINE,
        reason="test",
        x_column="month",
        y_columns=["Apple"],  # time_series_df の列と一致させる
    )


@pytest.fixture
def time_series_df():
    return pd.DataFrame({
        "month": ["2024-01", "2024-02", "2024-03"],
        "Apple": [100, 120, 110],
        "Google": [90, 95, 130],
        "Meta": [80, 85, 90],
    })


@pytest.fixture
def category_df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Carol"],
        "score": [90, 75, 85],
    })


# ── VideoConfig ───────────────────────────────────

class TestVideoConfig:
    def test_default_figsize_is_vertical(self):
        cfg = VideoConfig()
        assert cfg.figsize == (10.8, 19.2)

    def test_default_dpi(self):
        assert VideoConfig().dpi == 100

    def test_default_fps(self):
        assert VideoConfig().fps == 30

    def test_default_duration(self):
        assert VideoConfig().duration_seconds == 30


# ── ChartGenerator ディスパッチ ───────────────────

class TestChartGeneratorDispatch:
    def test_dispatches_bar_race(self, tmp_path, time_series_df, bar_race_rec, theme):
        out = tmp_path / "out.mp4"
        with patch("src.chart_generator.BarRaceGenerator.generate") as mock_gen:
            mock_gen.return_value = out
            result = ChartGenerator().generate(time_series_df, bar_race_rec, theme, VideoConfig(), out)
        mock_gen.assert_called_once()
        assert result == out

    def test_dispatches_animated_bar(self, tmp_path, category_df, animated_bar_rec, theme):
        out = tmp_path / "out.mp4"
        with patch("src.chart_generator.AnimatedChartGenerator.generate_bar") as mock_gen:
            mock_gen.return_value = out
            ChartGenerator().generate(category_df, animated_bar_rec, theme, VideoConfig(), out)
        mock_gen.assert_called_once()

    def test_dispatches_animated_line(self, tmp_path, time_series_df, animated_line_rec, theme):
        out = tmp_path / "out.mp4"
        with patch("src.chart_generator.AnimatedChartGenerator.generate_line") as mock_gen:
            mock_gen.return_value = out
            ChartGenerator().generate(time_series_df, animated_line_rec, theme, VideoConfig(), out)
        mock_gen.assert_called_once()

    def test_passes_progress_callback(self, tmp_path, time_series_df, bar_race_rec, theme):
        out = tmp_path / "out.mp4"
        progress_calls = []
        with patch("src.chart_generator.BarRaceGenerator.generate") as mock_gen:
            mock_gen.return_value = out
            ChartGenerator().generate(
                time_series_df, bar_race_rec, theme, VideoConfig(), out,
                on_progress=lambda p: progress_calls.append(p),
            )
        mock_gen.assert_called_once()


# ── BarRaceGenerator ──────────────────────────────

class TestBarRaceGenerator:
    def test_prepares_wide_format_df(self, tmp_path, time_series_df, bar_race_rec, theme):
        """month を index にした wide format に変換されること"""
        from src.chart_generator import BarRaceGenerator
        captured = {}

        def fake_bcr(df, filename, **kwargs):
            captured["df"] = df
            captured["figsize"] = kwargs.get("figsize")

        with patch("src.chart_generator.bcr.bar_chart_race", side_effect=fake_bcr):
            BarRaceGenerator().generate(
                time_series_df, bar_race_rec, theme, VideoConfig(),
                tmp_path / "out.mp4",
            )

        assert "month" not in captured["df"].columns
        assert set(captured["df"].columns) == {"Apple", "Google", "Meta"}

    def test_uses_vertical_figsize(self, tmp_path, time_series_df, bar_race_rec, theme):
        from src.chart_generator import BarRaceGenerator
        captured = {}

        def fake_bcr(df, filename, **kwargs):
            captured["figsize"] = kwargs.get("figsize")

        with patch("src.chart_generator.bcr.bar_chart_race", side_effect=fake_bcr):
            BarRaceGenerator().generate(
                time_series_df, bar_race_rec, theme, VideoConfig(),
                tmp_path / "out.mp4",
            )

        assert captured["figsize"] == (10.8, 19.2)

    def test_applies_theme_background(self, tmp_path, time_series_df, bar_race_rec, theme):
        from src.chart_generator import BarRaceGenerator
        captured = {}

        def fake_bcr(df, filename, **kwargs):
            captured["kwargs"] = kwargs

        with patch("src.chart_generator.bcr.bar_chart_race", side_effect=fake_bcr):
            BarRaceGenerator().generate(
                time_series_df, bar_race_rec, theme, VideoConfig(),
                tmp_path / "out.mp4",
            )

        assert captured["kwargs"].get("fig_kwargs", {}).get("facecolor") == theme.background_color

    def test_returns_output_path(self, tmp_path, time_series_df, bar_race_rec, theme):
        from src.chart_generator import BarRaceGenerator
        out = tmp_path / "result.mp4"

        with patch("src.chart_generator.bcr.bar_chart_race"):
            result = BarRaceGenerator().generate(
                time_series_df, bar_race_rec, theme, VideoConfig(), out,
            )

        assert result == out


# ── AnimatedChartGenerator ────────────────────────

class TestAnimatedChartGenerator:
    def test_bar_uses_vertical_figsize(self, tmp_path, category_df, animated_bar_rec, theme):
        from src.chart_generator import AnimatedChartGenerator
        captured = {}

        def fake_subplots(**kwargs):
            captured["figsize"] = kwargs.get("figsize")
            fig = MagicMock()
            ax = MagicMock()
            return fig, ax

        with patch("src.chart_generator.plt.subplots", side_effect=fake_subplots), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            AnimatedChartGenerator().generate_bar(
                category_df, animated_bar_rec, theme, VideoConfig(),
                tmp_path / "out.mp4",
            )

        assert captured["figsize"] == (10.8, 19.2)

    def test_line_uses_vertical_figsize(self, tmp_path, time_series_df, animated_line_rec, theme):
        from src.chart_generator import AnimatedChartGenerator
        captured = {}

        def fake_subplots(**kwargs):
            captured["figsize"] = kwargs.get("figsize")
            return MagicMock(), MagicMock()

        with patch("src.chart_generator.plt.subplots", side_effect=fake_subplots), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            AnimatedChartGenerator().generate_line(
                time_series_df, animated_line_rec, theme, VideoConfig(),
                tmp_path / "out.mp4",
            )

        assert captured["figsize"] == (10.8, 19.2)

    def test_bar_returns_output_path(self, tmp_path, category_df, animated_bar_rec, theme):
        from src.chart_generator import AnimatedChartGenerator
        out = tmp_path / "bar.mp4"

        with patch("src.chart_generator.plt.subplots", return_value=(MagicMock(), MagicMock())), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            result = AnimatedChartGenerator().generate_bar(
                category_df, animated_bar_rec, theme, VideoConfig(), out,
            )

        assert result == out
