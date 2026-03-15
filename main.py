"""
ChartVideoCreater - CSVデータからショート動画を生成するアプリ

Claude Code スキル (/create-chart-video) から呼び出されることを想定しています。
Claude がCSVを分析してチャートタイプ・列情報を決定し、引数として渡します。
"""
import argparse
import shutil
import sys
from pathlib import Path


def check_ffmpeg() -> bool:
    """FFmpeg が利用可能か確認する。"""
    if shutil.which("ffmpeg"):
        return True
    try:
        import imageio_ffmpeg  # type: ignore
        imageio_ffmpeg.get_ffmpeg_exe()
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CSVからチャート動画（縦型MP4）を生成します",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --csv data.csv --chart-type bar_race --x-col month --y-cols "Apple,Google,Meta"
  python main.py --csv sales.csv --chart-type animated_bar --x-col name --y-cols score --theme dark
        """,
    )
    parser.add_argument("--csv", required=True, help="CSVファイルパス")
    parser.add_argument(
        "--chart-type", required=True,
        choices=["bar_race", "animated_bar", "animated_line"],
        help="チャートタイプ",
    )
    parser.add_argument("--x-col", required=True, help="X軸列名")
    parser.add_argument("--y-cols", required=True, help="Y軸列名（カンマ区切り）")
    parser.add_argument(
        "--theme", default="default",
        choices=["dark", "pastel", "default"],
        help="カラーテーマ（default: default）",
    )
    parser.add_argument("--output-dir", default="output", help="出力ディレクトリ（default: output）")

    args = parser.parse_args()

    if not check_ffmpeg():
        print("❌ FFmpeg が見つかりません。")
        print("  インストール方法: pip install imageio-ffmpeg")
        sys.exit(1)

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)

    y_cols = [c.strip() for c in args.y_cols.split(",") if c.strip()]

    from src.app import VideoApp
    VideoApp(output_dir=Path(args.output_dir)).run(
        csv_path=csv_path,
        chart_type=args.chart_type,
        x_col=args.x_col,
        y_cols=y_cols,
        theme_name=args.theme,
    )


if __name__ == "__main__":
    main()
