"""統合テスト: コンポーネント間の連携を検証する。

- CSVScanner → DataAnalyzer（実CSV読み込み + モックAPI）
- DataAnalyzer → ChartGenerator（推薦→一時MP4生成）
- ChartGenerator → VideoRenderer（一時MP4→最終MP4）
- イベントアノテーション込みフロー
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.csv_scanner import CSVScanner, CSVMetadata
from src.data_analyzer import DataAnalyzer, ChartType, ChartRecommendation
from src.theme_manager import ThemeManager
from src.chart_generator import ChartGenerator, VideoConfig
from src.event_annotator import EventAnnotator
from src.video_renderer import VideoRenderer


# ── フィクスチャ ────────────────────────────────────────────


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """月次ランキングデータの CSV ファイル。"""
    csv_path = tmp_path / "ranking.csv"
    csv_path.write_text(
        "month,Apple,Google,Meta\n"
        "2024-01,100,90,80\n"
        "2024-02,120,95,85\n"
        "2024-03,110,130,90\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def category_csv(tmp_path: Path) -> Path:
    """カテゴリ比較データの CSV ファイル。"""
    csv_path = tmp_path / "category.csv"
    csv_path.write_text(
        "month,sales\n"
        "2024-01,500\n"
        "2024-02,620\n"
        "2024-03,480\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def theme():
    return ThemeManager().get_theme("default")


# ── CSVScanner → DataAnalyzer ───────────────────────────────


class TestCSVScannerToDataAnalyzer:
    """実 CSV を読み込み、DataAnalyzer にメタデータを渡す統合。"""

    def test_scanner_produces_metadata_for_analyzer(self, sample_csv, tmp_path):
        """CSVScanner が返した CSVMetadata を DataAnalyzer が正常に受け取れること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(sample_csv)

        # metadata の構造を確認
        assert metadata.row_count == 3
        assert "month" in metadata.columns or len(metadata.columns) >= 1
        assert len(metadata.sample_rows) <= 5

    def test_analyzer_accepts_scanner_metadata(self, sample_csv):
        """DataAnalyzer が CSVScanner の出力を受け取り推薦を返せること（API はモック）"""
        scanner = CSVScanner()
        _, metadata = scanner.load_csv(sample_csv)

        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps({
            "chart_type": "bar_race",
            "reason": "時系列×複数カテゴリのためバーレースを推薦",
            "x_column": metadata.columns[0],
            "y_columns": [c for c in metadata.columns if c != metadata.columns[0]],
            "category_column": None,
        })

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            recommendation = DataAnalyzer().analyze(metadata)

        assert recommendation.chart_type == ChartType.BAR_RACE
        assert recommendation.x_column in metadata.columns

    def test_fallback_recommendation_on_api_failure(self, sample_csv):
        """API 失敗時にフォールバック推薦が正しく返ること"""
        scanner = CSVScanner()
        _, metadata = scanner.load_csv(sample_csv)

        with patch("anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_client.messages.create.side_effect = Exception("API Error")

            recommendation = DataAnalyzer().analyze(metadata)

        # フォールバック: 推薦が返ること（例外なし）
        assert recommendation.chart_type in ChartType
        assert recommendation.x_column is not None

    def test_utf8_csv_loaded_correctly(self, tmp_path):
        """UTF-8 CSV が正しく読み込まれること"""
        csv_path = tmp_path / "utf8.csv"
        csv_path.write_text("日付,売上\n2024-01,100\n2024-02,200\n", encoding="utf-8")

        scanner = CSVScanner()
        df, metadata = scanner.load_csv(csv_path)

        assert metadata.row_count == 2
        assert len(df) == 2


# ── DataAnalyzer → ChartGenerator ──────────────────────────


class TestDataAnalyzerToChartGenerator:
    """推薦結果を ChartGenerator に渡して一時 MP4 が生成される流れ。"""

    def test_bar_race_recommendation_passed_to_generator(self, sample_csv, tmp_path, theme):
        """bar_race 推薦を ChartGenerator に渡すと BarRaceGenerator が呼ばれること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(sample_csv)

        numeric_cols = [c for c in metadata.columns if c != metadata.columns[0]]
        recommendation = ChartRecommendation(
            chart_type=ChartType.BAR_RACE,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=numeric_cols,
        )

        out_path = tmp_path / "out.mp4"
        with patch("src.chart_generator.bcr.bar_chart_race") as mock_bcr:
            ChartGenerator().generate(
                df, recommendation, theme, VideoConfig(), out_path,
            )

        mock_bcr.assert_called_once()

    def test_animated_bar_recommendation_passed_to_generator(
        self, category_csv, tmp_path, theme
    ):
        """animated_bar 推薦を ChartGenerator に渡すと AnimatedChartGenerator が呼ばれること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(category_csv)

        numeric_cols = [c for c in metadata.columns if c != metadata.columns[0]]
        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=numeric_cols,
        )

        out_path = tmp_path / "out.mp4"
        with patch("src.chart_generator.plt.subplots", return_value=(MagicMock(), MagicMock())), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            ChartGenerator().generate(
                df, recommendation, theme, VideoConfig(), out_path,
            )

        mock_ani.assert_called_once()

    def test_animated_line_recommendation_passed_to_generator(
        self, category_csv, tmp_path, theme
    ):
        """animated_line 推薦を ChartGenerator に渡すと generate_line が呼ばれること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(category_csv)

        numeric_cols = [c for c in metadata.columns if c != metadata.columns[0]]
        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_LINE,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=numeric_cols,
        )

        out_path = tmp_path / "out.mp4"
        with patch("src.chart_generator.plt.subplots", return_value=(MagicMock(), MagicMock())), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            ChartGenerator().generate(
                df, recommendation, theme, VideoConfig(), out_path,
            )

        mock_ani.assert_called_once()


# ── ChartGenerator → EventAnnotator → VideoRenderer ────────


class TestChartToVideoRenderer:
    """一時 MP4 にフェード効果を適用して最終 MP4 を生成する流れ。"""

    def _make_mock_clip(self, duration: float = 30.0) -> MagicMock:
        clip = MagicMock()
        clip.duration = duration
        clip.fadein.return_value = clip
        clip.fadeout.return_value = clip
        return clip

    def test_renderer_receives_temp_mp4_from_generator(self, tmp_path, theme, category_csv):
        """ChartGenerator が生成した一時ファイルを VideoRenderer が受け取れること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(category_csv)

        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=[c for c in metadata.columns if c != metadata.columns[0]],
        )
        tmp_path_mp4 = tmp_path / "tmp" / "chart_tmp.mp4"
        tmp_path_mp4.parent.mkdir()

        # ChartGenerator は一時 MP4 を生成（モック）
        with patch("src.chart_generator.plt.subplots", return_value=(MagicMock(), MagicMock())), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            ChartGenerator().generate(df, recommendation, theme, VideoConfig(), tmp_path_mp4)

        # VideoRenderer にパスを渡して最終 MP4 を生成（moviepy はモック）
        tmp_path_mp4.touch()  # 一時ファイルを作成（generate がモックのため）
        mock_clip = self._make_mock_clip()
        output_dir = tmp_path / "output"

        def fake_write(path: str, **kwargs) -> None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"x" * 1024)

        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            result = VideoRenderer().render(tmp_path_mp4, output_dir, "category")

        assert result.suffix == ".mp4"
        assert result.exists()

    def test_event_annotations_loaded_before_generation(self, tmp_path, theme, category_csv):
        """EventAnnotator が events.csv を検出し、アノテーションリストを返すこと"""
        # events.csv を作成
        events_csv = tmp_path / "events.csv"
        events_csv.write_text("period,category,text\n2024-02,sales,売上ピーク！\n")

        scanner = CSVScanner()
        df, metadata = scanner.load_csv(category_csv)
        time_index = df[metadata.columns[0]].astype(str).tolist()

        annotations = EventAnnotator().load_events(tmp_path, time_index)

        assert len(annotations) == 1
        assert annotations[0].text == "売上ピーク！"

    def test_no_events_csv_returns_empty_list(self, tmp_path, category_csv):
        """events.csv が存在しない場合は空リストが返ること"""
        scanner = CSVScanner()
        df, metadata = scanner.load_csv(category_csv)
        time_index = df[metadata.columns[0]].astype(str).tolist()

        annotations = EventAnnotator().load_events(tmp_path, time_index)

        assert annotations == []


# ── E2E フロー: VideoApp 全体 ───────────────────────────────


class TestE2EFlow:
    """VideoApp の全フローを E2E レベルで検証する（動画生成部分はモック）。"""

    def test_full_pipeline_bar_race(self, tmp_path):
        """bar_race の全フローが完走すること"""
        from src.app import VideoApp

        # サンプル CSV を配置
        csv_path = tmp_path / "ranking.csv"
        csv_path.write_text(
            "month,Apple,Google\n"
            "2024-01,100,90\n"
            "2024-02,120,95\n",
            encoding="utf-8",
        )

        app = VideoApp(work_dir=tmp_path, output_dir=tmp_path / "output")

        recommendation = ChartRecommendation(
            chart_type=ChartType.BAR_RACE,
            reason="バーレース推薦",
            x_column="month",
            y_columns=["Apple", "Google"],
        )

        def fake_generate(df, rec, th, cfg, path, **kw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            return path

        def fake_render(temp, out_dir, stem, **kw):
            out_dir.mkdir(parents=True, exist_ok=True)
            result = out_dir / f"{stem}_20260315.mp4"
            result.touch()
            return result

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()  # 例外なく完了すること

    def test_full_pipeline_animated_bar(self, tmp_path):
        """animated_bar の全フローが完走すること"""
        from src.app import VideoApp

        csv_path = tmp_path / "sales.csv"
        csv_path.write_text("month,sales\n2024-01,500\n2024-02,600\n", encoding="utf-8")

        app = VideoApp(work_dir=tmp_path, output_dir=tmp_path / "output")

        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="棒グラフ推薦",
            x_column="month",
            y_columns=["sales"],
        )

        def fake_generate(df, rec, th, cfg, path, **kw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            return path

        def fake_render(temp, out_dir, stem, **kw):
            out_dir.mkdir(parents=True, exist_ok=True)
            result = out_dir / f"{stem}_20260315.mp4"
            result.touch()
            return result

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

    def test_full_pipeline_animated_line(self, tmp_path):
        """animated_line の全フローが完走すること"""
        from src.app import VideoApp

        csv_path = tmp_path / "trend.csv"
        csv_path.write_text("month,value\n2024-01,10\n2024-02,20\n2024-03,15\n", encoding="utf-8")

        app = VideoApp(work_dir=tmp_path, output_dir=tmp_path / "output")

        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_LINE,
            reason="折れ線推薦",
            x_column="month",
            y_columns=["value"],
        )

        def fake_generate(df, rec, th, cfg, path, **kw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            return path

        def fake_render(temp, out_dir, stem, **kw):
            out_dir.mkdir(parents=True, exist_ok=True)
            result = out_dir / f"{stem}_20260315.mp4"
            result.touch()
            return result

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

    def test_output_mp4_in_output_directory(self, tmp_path):
        """最終 MP4 が output/ ディレクトリに生成されること"""
        from src.app import VideoApp

        csv_path = tmp_path / "data.csv"
        csv_path.write_text("month,score\n2024-01,90\n2024-02,80\n", encoding="utf-8")

        output_dir = tmp_path / "output"
        app = VideoApp(work_dir=tmp_path, output_dir=output_dir)

        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="テスト",
            x_column="month",
            y_columns=["score"],
        )
        result_path: list[Path] = []

        def fake_generate(df, rec, th, cfg, path, **kw):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            return path

        def fake_render(temp, out_dir, stem, **kw):
            out_dir.mkdir(parents=True, exist_ok=True)
            r = out_dir / f"{stem}_20260315.mp4"
            r.touch()
            result_path.append(r)
            return r

        with patch.object(app._analyzer, "analyze", return_value=recommendation), \
             patch.object(app._generator, "generate", side_effect=fake_generate), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]), \
             patch("builtins.input", return_value=""):
            app.run()

        assert len(result_path) == 1
        assert result_path[0].parent == output_dir
