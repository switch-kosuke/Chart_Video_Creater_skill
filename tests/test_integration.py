"""統合テスト: コンポーネント間の連携を検証する。

- CSVScanner → ChartGenerator（実CSV読み込み + 動画生成）
- ChartGenerator → VideoRenderer（一時MP4→最終MP4）
- イベントアノテーション込みフロー
- VideoApp 全体フロー（E2E）
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.csv_scanner import CSVScanner
from src.models import ChartType, ChartRecommendation
from src.theme_manager import ThemeManager
from src.chart_generator import ChartGenerator, VideoConfig
from src.event_annotator import EventAnnotator
from src.video_renderer import VideoRenderer


# ── フィクスチャ ────────────────────────────────────────────


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
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


# ── CSVScanner ──────────────────────────────────────────────


class TestCSVScanner:
    def test_scanner_produces_metadata(self, sample_csv):
        """CSVScanner が正しいメタデータを返すこと"""
        df, metadata = CSVScanner().load_csv(sample_csv)
        assert metadata.row_count == 3
        assert len(metadata.sample_rows) <= 5

    def test_utf8_csv_loaded_correctly(self, tmp_path):
        csv_path = tmp_path / "utf8.csv"
        csv_path.write_text("日付,売上\n2024-01,100\n2024-02,200\n", encoding="utf-8")
        df, metadata = CSVScanner().load_csv(csv_path)
        assert metadata.row_count == 2
        assert len(df) == 2

    def test_scanner_metadata_has_required_fields(self, sample_csv):
        """メタデータに必要なフィールドが含まれること"""
        _, metadata = CSVScanner().load_csv(sample_csv)
        assert metadata.columns is not None
        assert metadata.dtypes is not None
        assert isinstance(metadata.has_datetime_column, bool)


# ── ChartRecommendation → ChartGenerator ───────────────────


class TestRecommendationToChartGenerator:
    def test_bar_race_calls_bcr(self, sample_csv, tmp_path, theme):
        df, metadata = CSVScanner().load_csv(sample_csv)
        numeric_cols = [c for c in metadata.columns if c != metadata.columns[0]]
        recommendation = ChartRecommendation(
            chart_type=ChartType.BAR_RACE,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=numeric_cols,
        )
        out_path = tmp_path / "out.mp4"
        with patch("src.chart_generator.bcr.bar_chart_race") as mock_bcr:
            ChartGenerator().generate(df, recommendation, theme, VideoConfig(), out_path)
        mock_bcr.assert_called_once()

    def test_animated_bar_calls_func_animation(self, category_csv, tmp_path, theme):
        df, metadata = CSVScanner().load_csv(category_csv)
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
            ChartGenerator().generate(df, recommendation, theme, VideoConfig(), out_path)
        mock_ani.assert_called_once()

    def test_animated_line_calls_func_animation(self, category_csv, tmp_path, theme):
        df, metadata = CSVScanner().load_csv(category_csv)
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
            ChartGenerator().generate(df, recommendation, theme, VideoConfig(), out_path)
        mock_ani.assert_called_once()


# ── ChartGenerator → VideoRenderer ─────────────────────────


class TestChartToVideoRenderer:
    def _make_mock_clip(self, duration: float = 30.0) -> MagicMock:
        clip = MagicMock()
        clip.duration = duration
        clip.fadein.return_value = clip
        clip.fadeout.return_value = clip
        return clip

    def test_renderer_receives_temp_mp4(self, tmp_path, theme, category_csv):
        df, metadata = CSVScanner().load_csv(category_csv)
        recommendation = ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="テスト",
            x_column=metadata.columns[0],
            y_columns=[c for c in metadata.columns if c != metadata.columns[0]],
        )
        tmp_mp4 = tmp_path / "tmp" / "chart_tmp.mp4"
        tmp_mp4.parent.mkdir()

        with patch("src.chart_generator.plt.subplots", return_value=(MagicMock(), MagicMock())), \
             patch("src.chart_generator.FuncAnimation") as mock_ani:
            mock_ani.return_value.save = MagicMock()
            ChartGenerator().generate(df, recommendation, theme, VideoConfig(), tmp_mp4)

        tmp_mp4.touch()
        mock_clip = self._make_mock_clip()
        output_dir = tmp_path / "output"

        def fake_write(path: str, **kwargs) -> None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"x" * 1024)

        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            result = VideoRenderer().render(tmp_mp4, output_dir, "category")

        assert result.suffix == ".mp4"
        assert result.exists()

    def test_event_annotations_loaded(self, tmp_path, category_csv):
        events_csv = tmp_path / "events.csv"
        events_csv.write_text("period,category,text\n2024-02,sales,売上ピーク！\n")
        df, metadata = CSVScanner().load_csv(category_csv)
        time_index = df[metadata.columns[0]].astype(str).tolist()
        annotations = EventAnnotator().load_events(tmp_path, time_index)
        assert len(annotations) == 1
        assert annotations[0].text == "売上ピーク！"

    def test_no_events_csv_returns_empty(self, tmp_path, category_csv):
        df, metadata = CSVScanner().load_csv(category_csv)
        time_index = df[metadata.columns[0]].astype(str).tolist()
        annotations = EventAnnotator().load_events(tmp_path, time_index)
        assert annotations == []


# ── E2E フロー: VideoApp 全体 ───────────────────────────────


class TestE2EFlow:
    def _fake_generate(self, path):
        def inner(df, rec, th, cfg, p, **kw):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
            return p
        return inner

    def _fake_render(self, out_dir):
        def inner(temp, od, stem, **kw):
            od.mkdir(parents=True, exist_ok=True)
            r = od / f"{stem}_20260315.mp4"
            r.touch()
            return r
        return inner

    def test_full_pipeline_bar_race(self, tmp_path):
        from src.app import VideoApp
        csv_path = tmp_path / "ranking.csv"
        csv_path.write_text(
            "month,Apple,Google\n2024-01,100,90\n2024-02,120,95\n", encoding="utf-8"
        )
        app = VideoApp(output_dir=tmp_path / "output")
        with patch.object(app._generator, "generate", side_effect=self._fake_generate(tmp_path)), \
             patch.object(app._renderer, "render", side_effect=self._fake_render(tmp_path / "output")), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv_path, chart_type="bar_race",
                    x_col="month", y_cols=["Apple", "Google"])

    def test_full_pipeline_animated_bar(self, tmp_path):
        from src.app import VideoApp
        csv_path = tmp_path / "sales.csv"
        csv_path.write_text("month,sales\n2024-01,500\n2024-02,600\n", encoding="utf-8")
        app = VideoApp(output_dir=tmp_path / "output")
        with patch.object(app._generator, "generate", side_effect=self._fake_generate(tmp_path)), \
             patch.object(app._renderer, "render", side_effect=self._fake_render(tmp_path / "output")), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv_path, chart_type="animated_bar",
                    x_col="month", y_cols=["sales"])

    def test_full_pipeline_animated_line(self, tmp_path):
        from src.app import VideoApp
        csv_path = tmp_path / "trend.csv"
        csv_path.write_text("month,value\n2024-01,10\n2024-02,20\n2024-03,15\n", encoding="utf-8")
        app = VideoApp(output_dir=tmp_path / "output")
        with patch.object(app._generator, "generate", side_effect=self._fake_generate(tmp_path)), \
             patch.object(app._renderer, "render", side_effect=self._fake_render(tmp_path / "output")), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv_path, chart_type="animated_line",
                    x_col="month", y_cols=["value"])

    def test_output_mp4_in_output_directory(self, tmp_path):
        from src.app import VideoApp
        csv_path = tmp_path / "data.csv"
        csv_path.write_text("month,score\n2024-01,90\n2024-02,80\n", encoding="utf-8")
        output_dir = tmp_path / "output"
        app = VideoApp(output_dir=output_dir)
        result_path: list[Path] = []

        def fake_render(temp, od, stem, **kw):
            od.mkdir(parents=True, exist_ok=True)
            r = od / f"{stem}_20260315.mp4"
            r.touch()
            result_path.append(r)
            return r

        with patch.object(app._generator, "generate", side_effect=self._fake_generate(tmp_path)), \
             patch.object(app._renderer, "render", side_effect=fake_render), \
             patch.object(app._annotator, "load_events", return_value=[]):
            app.run(csv_path=csv_path, chart_type="animated_bar",
                    x_col="month", y_cols=["score"])

        assert result_path[0].parent == output_dir
