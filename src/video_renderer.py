"""VideoRenderer — フェードイン・アウト効果適用と MP4 最終出力"""
from __future__ import annotations

from datetime import date
from pathlib import Path

try:
    from moviepy.editor import VideoFileClip  # type: ignore
except ImportError:  # pragma: no cover
    VideoFileClip = None  # type: ignore


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
        clip = clip.fadein(fade_duration).fadeout(fade_duration)

        bitrate = f"{self._DEFAULT_BITRATE_KBPS}k"
        clip.write_videofile(
            str(output_path),
            codec="libx264",
            bitrate=bitrate,
            logger=None,
        )
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

    def _reencode_smaller(self, output_path: Path, current_size_mb: float) -> None:
        """ビットレートを自動調整して output_path を上書き再エンコードする。"""
        ratio = self.MAX_FILE_SIZE_MB / current_size_mb
        new_bitrate_kbps = int(self._DEFAULT_BITRATE_KBPS * ratio * 0.9)  # 10% マージン
        new_bitrate = f"{new_bitrate_kbps}k"

        clip = VideoFileClip(str(output_path))
        clip.write_videofile(
            str(output_path),
            codec="libx264",
            bitrate=new_bitrate,
            logger=None,
        )
        clip.close()
