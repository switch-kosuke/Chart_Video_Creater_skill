"""
ChartVideoCreater - CSVデータからショート動画を生成するアプリ
"""
import os
import shutil
import sys
from pathlib import Path


def check_environment() -> tuple[bool, list[str]]:
    """起動前提条件を確認する。(ok, errors) を返す。"""
    errors: list[str] = []

    if not os.environ.get("ANTHROPIC_API_KEY"):
        errors.append(
            "ANTHROPIC_API_KEY が設定されていません。\n"
            "  設定方法: export ANTHROPIC_API_KEY='your-api-key'"
        )

    if shutil.which("ffmpeg") is None:
        errors.append(
            "FFmpeg が見つかりません。\n"
            "  インストール方法: pip install imageio-ffmpeg\n"
            "  または: https://ffmpeg.org/download.html"
        )

    return len(errors) == 0, errors


def main() -> None:
    ok, errors = check_environment()
    if not ok:
        print("❌ セットアップが必要です:\n")
        for error in errors:
            print(f"  • {error}\n")
        sys.exit(1)

    from src.app import VideoApp
    VideoApp().run()


if __name__ == "__main__":
    main()
