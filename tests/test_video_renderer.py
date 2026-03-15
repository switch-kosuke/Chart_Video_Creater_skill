"""VideoRenderer のテスト（moviepy はモック）"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.video_renderer import VideoRenderer


def _make_mock_clip(duration: float = 30.0) -> MagicMock:
    """chainable な mock clip を生成する。"""
    clip = MagicMock()
    clip.duration = duration
    clip.fadein.return_value = clip
    clip.fadeout.return_value = clip
    return clip


def _fake_write_small(path: str, **kwargs) -> None:
    """write_videofile のフェイク実装（小さいファイルを作成）。"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b"x" * 1024)  # 1 KB


# ── 出力パス ────────────────────────────────────────────────


class TestOutputPath:
    def test_filename_format(self, tmp_path):
        """{csv_stem}_{YYYYMMDD}.mp4 形式になること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        output_dir = tmp_path / "output"
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip), \
             patch("src.video_renderer.date") as mock_date:
            mock_date.today.return_value.strftime.return_value = "20260315"
            result = VideoRenderer().render(temp_mp4, output_dir, "sales_data")

        assert result.name == "sales_data_20260315.mp4"

    def test_output_dir_created_if_missing(self, tmp_path):
        """output_dir が存在しない場合に自動作成されること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        output_dir = tmp_path / "output" / "nested"
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, output_dir, "data")

        assert output_dir.exists()

    def test_returns_path_in_output_dir(self, tmp_path):
        """render() が output_dir 内のパスを返すこと"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        output_dir = tmp_path / "output"
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            result = VideoRenderer().render(temp_mp4, output_dir, "data")

        assert result.parent == output_dir
        assert result.suffix == ".mp4"


# ── フェード効果 ────────────────────────────────────────────


class TestFadeEffects:
    def test_fadein_applied_with_default_duration(self, tmp_path):
        """fadein が 0.5 秒で呼ばれること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        mock_clip.fadein.assert_called_once_with(0.5)

    def test_fadeout_applied_with_default_duration(self, tmp_path):
        """fadeout が 0.5 秒で呼ばれること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        mock_clip.fadeout.assert_called_once_with(0.5)

    def test_custom_fade_duration(self, tmp_path):
        """カスタムフェード時間が fadein/fadeout 両方に適用されること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data", fade_duration=1.0)

        mock_clip.fadein.assert_called_once_with(1.0)
        mock_clip.fadeout.assert_called_once_with(1.0)


# ── エンコード設定 ──────────────────────────────────────────


class TestEncoding:
    def _capture_write_args(self, tmp_path):
        """write_videofile に渡された kwargs を記録するフェイクを返す。"""
        captured: dict = {}

        def fake_write(path: str, **kwargs) -> None:
            captured.update(kwargs)
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_bytes(b"x" * 1024)

        return captured, fake_write

    def test_uses_h264_codec(self, tmp_path):
        """H.264 コーデック (libx264) でエンコードされること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        captured, fake_write = self._capture_write_args(tmp_path)
        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert captured.get("codec") == "libx264"

    def test_uses_3000k_bitrate(self, tmp_path):
        """ビットレート 3000k でエンコードされること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        captured, fake_write = self._capture_write_args(tmp_path)
        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert captured.get("bitrate") == "3000k"


# ── 一時ファイル削除 ────────────────────────────────────────


class TestTempFileDeletion:
    def test_temp_file_deleted_after_render(self, tmp_path):
        """レンダリング後に一時ファイルが削除されること"""
        temp_mp4 = tmp_path / "tmp_chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert not temp_mp4.exists()

    def test_missing_temp_file_does_not_raise(self, tmp_path):
        """一時ファイルが既に存在しない場合もエラーにならないこと"""
        temp_mp4 = tmp_path / "nonexistent.mp4"  # 意図的に作成しない
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")  # 例外なし


# ── ファイルサイズ最適化 ────────────────────────────────────


class TestFileSizeOptimization:
    def test_no_reencode_when_under_20mb(self, tmp_path):
        """20MB 以下の場合は write_videofile が1回だけ呼ばれること"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        mock_clip.write_videofile.side_effect = _fake_write_small  # 小さいファイル

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert mock_clip.write_videofile.call_count == 1

    def test_reencode_when_over_20mb(self, tmp_path):
        """20MB 超の場合は write_videofile が2回呼ばれること（再エンコード）"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        call_count = [0]

        def fake_write(path: str, **kwargs) -> None:
            call_count[0] += 1
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if call_count[0] == 1:
                p.write_bytes(b"x" * (25 * 1024 * 1024))  # 25 MB
            else:
                p.write_bytes(b"x" * 1024)

        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert mock_clip.write_videofile.call_count == 2

    def test_reencode_uses_lower_bitrate(self, tmp_path):
        """再エンコード時のビットレートが初回より低いこと"""
        temp_mp4 = tmp_path / "chart.mp4"
        temp_mp4.touch()
        mock_clip = _make_mock_clip()
        recorded_bitrates: list[str] = []
        call_count = [0]

        def fake_write(path: str, **kwargs) -> None:
            call_count[0] += 1
            recorded_bitrates.append(kwargs.get("bitrate", ""))
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if call_count[0] == 1:
                p.write_bytes(b"x" * (25 * 1024 * 1024))
            else:
                p.write_bytes(b"x" * 1024)

        mock_clip.write_videofile.side_effect = fake_write

        with patch("src.video_renderer.VideoFileClip", return_value=mock_clip):
            VideoRenderer().render(temp_mp4, tmp_path / "out", "data")

        assert len(recorded_bitrates) == 2
        br1 = int(recorded_bitrates[0].replace("k", ""))
        br2 = int(recorded_bitrates[1].replace("k", ""))
        assert br2 < br1
