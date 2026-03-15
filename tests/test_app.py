"""VideoApp のテスト（全コンポーネントをモック）"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.app import VideoApp
from src.csv_scanner import CSVScanError
from src.data_analyzer import ChartRecommendation, ChartType, AnalysisError
from src.chart_generator import RenderingError
from src.theme_manager import ThemeManager


# ── フィクスチャ ────────────────────────────────────────────


@pytest.fixture
def recommendation():
    return ChartRecommendation(
        chart_type=ChartType.ANIMATED_BAR,
        reason="テスト推薦",
        x_column="date",
        y_columns=["score"],
    )


@pytest.fixture
def theme():
    return ThemeManager().get_theme("default")


@pytest.fixture
def app(tmp_path):
    """テスト用 VideoApp（tmp_path を作業ディレクトリ・出力ディレクトリに設定）"""
    return VideoApp(work_dir=tmp_path, output_dir=tmp_path / "output")


def _make_csv(tmp_path: Path, name: str = "data.csv") -> Path:
    p = tmp_path / name
    # date 列: datetime と認識されるので CSVScanner がフィルタせず保持する
    p.write_text("date,score\n2024-01,90\n2024-02,80\n")
    return p


# ── CSV 選択 ────────────────────────────────────────────────


class TestCSVSelection:
    def test_single_csv_auto_selected(self, app, tmp_path, recommendation, theme, capsys):
        """CSV が1ファイルだけのとき自動選択されること"""
        _make_csv(tmp_path)

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._theme_manager, "get_theme", return_value=theme), \
             patch.object(app._generator, "generate", return_value=tmp_path / "tmp.mp4"), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        out = capsys.readouterr().out
        assert "自動選択" in out

    def test_multiple_csv_shows_prompt(self, app, tmp_path, recommendation, theme, capsys):
        """CSV が複数のとき選択プロンプトが表示されること"""
        _make_csv(tmp_path, "a.csv")
        _make_csv(tmp_path, "b.csv")

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._theme_manager, "get_theme", return_value=theme), \
             patch.object(app._generator, "generate", return_value=tmp_path / "tmp.mp4"), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", side_effect=["1", "", ""]):
            app.run()

        out = capsys.readouterr().out
        assert "a.csv" in out or "選択" in out

    def test_invalid_csv_number_reprompts(self, app, tmp_path, recommendation, theme):
        """無効な番号を入力したとき再入力が促されること"""
        _make_csv(tmp_path, "a.csv")
        _make_csv(tmp_path, "b.csv")

        inputs = iter(["99", "abc", "1", "", ""])
        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._theme_manager, "get_theme", return_value=theme), \
             patch.object(app._generator, "generate", return_value=tmp_path / "tmp.mp4"), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", side_effect=inputs):
            app.run()  # 例外なく完了すること


# ── チャートタイプ選択 ──────────────────────────────────────


class TestChartTypeSelection:
    def test_enter_keeps_ai_recommendation(self, app, tmp_path, recommendation, theme):
        """Enter でスキップしたとき AI 推薦のまま進むこと"""
        _make_csv(tmp_path)
        captured_rec: list[ChartRecommendation] = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_rec.append(rec)
            return path

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._theme_manager, "get_theme", return_value=theme), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        assert captured_rec[0].chart_type == ChartType.ANIMATED_BAR

    def test_valid_number_changes_chart_type(self, app, tmp_path, recommendation, theme):
        """有効な番号入力でチャートタイプが変更されること"""
        _make_csv(tmp_path)
        captured_rec: list[ChartRecommendation] = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_rec.append(rec)
            return path

        # ChartType の順序: BAR_RACE=1, ANIMATED_BAR=2, ANIMATED_LINE=3
        # "1" を入力 → BAR_RACE に変更
        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._theme_manager, "get_theme", return_value=theme), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", side_effect=["1", ""]):
            app.run()

        assert captured_rec[0].chart_type == ChartType.BAR_RACE


# ── テーマ選択 ──────────────────────────────────────────────


class TestThemeSelection:
    def test_enter_uses_default_theme(self, app, tmp_path, recommendation):
        """テーマ選択で Enter → デフォルトテーマが使われること"""
        _make_csv(tmp_path)
        captured_theme = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_theme.append(th)
            return path

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        assert captured_theme[0].name == "default"

    def test_valid_theme_number_selected(self, app, tmp_path, recommendation):
        """有効な番号でテーマが選択されること"""
        _make_csv(tmp_path)
        captured_theme = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_theme.append(th)
            return path

        # "" → チャートタイプスキップ、"1" → dark テーマ
        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", side_effect=["", "1"]):
            app.run()

        assert captured_theme[0].name == "dark"

    def test_invalid_theme_uses_default(self, app, tmp_path, recommendation):
        """無効なテーマ番号 → デフォルトテーマが使われること"""
        _make_csv(tmp_path)
        captured_theme = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            captured_theme.append(th)
            return path

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value="999"):
            app.run()

        assert captured_theme[0].name == "default"


# ── エラーハンドリング ──────────────────────────────────────


class TestErrorHandling:
    def test_csv_scan_error_exits(self, app, tmp_path, capsys):
        """CSV が見つからないとき SystemExit が発生すること"""
        # CSV ファイルを置かない → CSVScanError が発生
        with pytest.raises(SystemExit):
            app.run()

    def test_rendering_error_exits(self, app, tmp_path, recommendation, capsys):
        """RenderingError 発生時に SystemExit すること"""
        _make_csv(tmp_path)

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch.object(app._generator, "generate",
                         side_effect=RenderingError("テスト失敗")), \
             patch("builtins.input", return_value=""):
            with pytest.raises(SystemExit):
                app.run()


# ── 進捗表示 ────────────────────────────────────────────────


class TestProgressDisplay:
    def test_progress_callback_updates_display(self, app, tmp_path, recommendation, capsys):
        """generate() に渡された on_progress コールバックが呼ばれること"""
        _make_csv(tmp_path)
        progress_calls: list[float] = []

        def fake_generate(df, rec, th, cfg, path, annotations=None, on_progress=None):
            if on_progress:
                on_progress(0.5)
                on_progress(1.0)
                progress_calls.extend([0.5, 1.0])
            return path

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        assert 0.5 in progress_calls
        assert 1.0 in progress_calls

    def test_progress_bar_format_shown(self, app, tmp_path, recommendation, capsys):
        """プログレスバー形式の文字列が出力されること"""
        _make_csv(tmp_path)

        def fake_generate(df, rec, th, cfg, path, annotations=None, on_progress=None):
            if on_progress:
                on_progress(0.6)
            return path

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", return_value=tmp_path / "output.mp4"), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        out = capsys.readouterr().out
        assert "%" in out or "█" in out


# ── フル統合フロー ──────────────────────────────────────────


class TestFullFlow:
    def test_all_components_called_in_order(self, app, tmp_path, recommendation, theme):
        """CSV選択→分析→テーマ→生成→レンダーの順で呼ばれること"""
        csv_path = _make_csv(tmp_path)
        call_order: list[str] = []

        def fake_analyze(meta):
            call_order.append("analyze")
            return recommendation

        def fake_generate(df, rec, th, cfg, path, **kw):
            call_order.append("generate")
            return path

        def fake_render(temp, out_dir, stem, **kw):
            call_order.append("render")
            return out_dir / "result.mp4"

        with patch.object(app._analyzer, "analyze", side_effect=fake_analyze), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        assert call_order == ["analyze", "generate", "render"]
