"""VideoRenderer — フェードイン・アウト効果適用と MP4 最終出力"""
from __future__ import annotations

from datetime import date
from pathlib import Path

try:
    from moviepy import VideoFileClip, vfx  # type: ignore  (moviepy v2)
except ImportError:
    try:
        from moviepy.editor import VideoFileClip  # type: ignore  (moviepy v1)
        vfx = None  # type: ignore
    except ImportError:  # pragma: no cover
        VideoFileClip = None  # type: ignore
        vfx = None  # type: ignore


class VideoRenderer:
    MAX_FILE_SIZE_MB = 20
    _DEFAULT_BITRATE_KBPS = 3000

    def render(
        self,
        temp_path: Path,
        output_dir: Path,
        csv_stem: str,
        fade_duration: float = 0.5,
    ) -> Path:
        """一時 MP4 にフェードイン・アウトを適用し、output/ に最終 MP4 を保存する。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().strftime("%Y%m%d")
        output_path = output_dir / f"{csv_stem}_{today}.mp4"

        clip = VideoFileClip(str(temp_path))
        duration = clip.duration
        clip = self._apply_fade(clip, fade_duration)

        self._write_video(clip, str(output_path), self._DEFAULT_BITRATE_KBPS)
        clip.close()

        # ファイルサイズが 20MB 超なら自動的にビットレートを下げて再エンコード
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            self._reencode_smaller(output_path, size_mb)

        # 一時ファイルを削除
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

        # 完了情報を表示
        final_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ 動画生成完了!")
        print(f"   出力ファイル: {output_path}")
        print(f"   ファイルサイズ: {final_size_mb:.1f} MB")
        print(f"   動画尺: {duration:.1f} 秒")

        return output_path

    def _apply_fade(self, clip, duration: float):
        """moviepy v1/v2 両対応でフェードイン・アウトを適用する。"""
        if vfx is not None:
            # moviepy v2
            clip = clip.with_effects([vfx.FadeIn(duration), vfx.FadeOut(duration)])
        else:
            # moviepy v1
            clip = clip.fadein(duration).fadeout(duration)
        return clip

    def _write_video(self, clip, path: str, bitrate_kbps: int) -> None:
        """moviepy v1/v2 両対応で動画を書き出す。"""
        if vfx is not None:
            # moviepy v2: bitrate は ffmpeg_params で指定
            clip.write_videofile(
                path,
                codec="libx264",
                ffmpeg_params=["-b:v", f"{bitrate_kbps}k"],
                logger=None,
            )
        else:
            # moviepy v1
            clip.write_videofile(
                path,
                codec="libx264",
                bitrate=f"{bitrate_kbps}k",
                logger=None,
            )
        clip.close()

    def _reencode_smaller(self, output_path: Path, current_size_mb: float) -> None:
        """ビットレートを自動調整して output_path を上書き再エンコードする。"""
        ratio = self.MAX_FILE_SIZE_MB / current_size_mb
        new_bitrate_kbps = int(self._DEFAULT_BITRATE_KBPS * ratio * 0.9)  # 10% マージン
        clip = VideoFileClip(str(output_path))
        self._write_video(clip, str(output_path), new_bitrate_kbps)
