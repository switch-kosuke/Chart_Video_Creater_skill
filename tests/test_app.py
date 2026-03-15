"""VideoApp のテスト（全コンポーネントをモック）"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.app import VideoApp
from src.csv_scanner import CSVScanError
from src.models import ChartRecommendation, ChartType
from src.chart_generator import RenderingError
from src.theme_manager import ThemeManager


# ── フィクスチャ ────────────────────────────────────────────


@pytest.fixture
def app(tmp_path):
    return VideoApp(output_dir=tmp_path / "output")


def _make_csv(tmp_path: Path, name: str = "data.csv") -> Path:
    p = tmp_path / name
    p.write_text("date,score\n2024-01,90\n2024-02,80\n")
    return p


def _run(app, csv_path, chart_type="animated_bar", x_col="date", y_cols=None, theme="default"):
    """VideoApp.run() のヘルパー。"""
    with patch.object(app._generator, "generate", return_value=csv_path.parent / "tmp.mp4"), \
         patch.object(app._renderer, "render", return_value=csv_path.parent / "output.mp4"), \
         patch.object(app._annotator, "load_events", return_value=[]):
        app.run(
            csv_path=csv_path,
            chart_type=chart_type,
            x_col=x_col,
            y_cols=y_cols or ["score"],
            theme_name=theme,
        )


# ── 正常フロー ──────────────────────────────────────────────


class TestRunSuccess:
    def test_bar_race_completes(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        _run(app, csv, chart_type="bar_race")

    def test_animated_bar_completes(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        _run(app, csv, chart_type="animated_bar")

    def test_animated_line_completes(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        _run(app, csv, chart_type="animated_line")

    def test_dark_theme_applied(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        captured_theme = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_theme.append(th)
            return path

        with patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=csv.parent / "out.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv, chart_type="animated_bar", x_col="date",
                    y_cols=["score"], theme_name="dark")

        assert captured_theme[0].name == "dark"

    def test_recommendation_built_from_args(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        captured_rec = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_rec.append(rec)
            return path

        with patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=csv.parent / "out.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv, chart_type="bar_race", x_col="date",
                    y_cols=["score"], theme_name="default")

        assert captured_rec[0].chart_type == ChartType.BAR_RACE
        assert captured_rec[0].x_column == "date"
        assert captured_rec[0].y_columns == ["score"]


# ── エラーハンドリング ──────────────────────────────────────


class TestErrorHandling:
    def test_csv_scan_error_exits(self, app, tmp_path):
        csv = tmp_path / "nonexistent.csv"
        with pytest.raises(SystemExit):
            app.run(csv_path=csv, chart_type="animated_bar",
                    x_col="date", y_cols=["score"])

    def test_rendering_error_exits(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        with patch.object(app._generator, "generate",
                          side_effect=RenderingError("テスト失敗")), \
             patch.object(app._annotator, "load_events", return_value=[]):
            with pytest.raises(SystemExit):
                app.run(csv_path=csv, chart_type="animated_bar",
                        x_col="date", y_cols=["score"])


# ── 進捗表示 ────────────────────────────────────────────────


class TestProgressDisplay:
    def test_progress_callback_called(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        progress_calls: list[float] = []

        def fake_generate(df, rec, th, cfg, path, annotations=None, on_progress=None):
            if on_progress:
                on_progress(0.5)
                on_progress(1.0)
                progress_calls.extend([0.5, 1.0])
            return path

        with patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=csv.parent / "out.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv, chart_type="animated_bar",
                    x_col="date", y_cols=["score"])

        assert 0.5 in progress_calls

    def test_progress_bar_shown(self, app, tmp_path, capsys):
        csv = _make_csv(tmp_path)

        def fake_generate(df, rec, th, cfg, path, annotations=None, on_progress=None):
            if on_progress:
                on_progress(0.6)
            return path

        with patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=csv.parent / "out.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv, chart_type="animated_bar",
                    x_col="date", y_cols=["score"])

        out = capsys.readouterr().out
        assert "%" in out or "█" in out


# ── フル統合フロー ──────────────────────────────────────────


class TestFullFlow:
    def test_generate_and_render_called(self, app, tmp_path):
        csv = _make_csv(tmp_path)
        call_order: list[str] = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            call_order.append("generate")
            return path

        def fake_render(temp, out_dir, stem, **kw):
            call_order.append("render")
            return out_dir / "result.mp4"

        with patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv, chart_type="animated_bar",
                    x_col="date", y_cols=["score"])

        assert call_order == ["generate", "render"]
