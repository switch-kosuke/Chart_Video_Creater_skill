"""VideoApp — メインオーケストレーター（CLIから引数を受け取り全コンポーネントを統合）"""
from __future__ import annotations

import sys
from pathlib import Path

from src.csv_scanner import CSVScanner, CSVScanError
from src.models import ChartRecommendation, ChartType
from src.theme_manager import ThemeManager
from src.chart_generator import ChartGenerator, VideoConfig, RenderingError
from src.event_annotator import EventAnnotator
from src.video_renderer import VideoRenderer


class VideoApp:
    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or Path("output")
        self._scanner = CSVScanner()
        self._theme_manager = ThemeManager()
        self._generator = ChartGenerator()
        self._annotator = EventAnnotator()
        self._renderer = VideoRenderer()

    def run(
        self,
        csv_path: Path,
        chart_type: str,
        x_col: str,
        y_cols: list[str],
        theme_name: str = "default",
    ) -> None:
        """CSV読み込み → チャート生成 → フェード適用 → MP4出力。"""
        print("🎬 動画生成を開始します")
        print("=" * 40)

        try:
            # 1. CSV読み込み
            df, metadata = self._scanner.load_csv(csv_path)

            # 2. ChartRecommendation を構築（Claude が分析済みの情報を使用）
            recommendation = ChartRecommendation(
                chart_type=ChartType(chart_type),
                reason="",
                x_column=x_col,
                y_columns=y_cols,
            )

            # 3. テーマ取得
            theme = self._theme_manager.get_theme(theme_name)

            print(f"\n📊 チャートタイプ: {chart_type}")
            print(f"   X軸: {x_col} / Y軸: {', '.join(y_cols)}")
            print(f"🎨 テーマ: {theme.display_name}")

            # 4. イベントアノテーション検出
            config = VideoConfig()
            time_index = df[x_col].astype(str).tolist()
            steps = max(1, config.duration_seconds * config.fps // max(len(df), 1))
            annotations = self._annotator.load_events(
                csv_path.parent, time_index, fps=config.fps, steps_per_period=steps,
            )

            # 5. 動画生成
            tmp_dir = self._output_dir / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_path = tmp_dir / f"{csv_path.stem}_tmp.mp4"
            print("\n🎨 動画生成中...")
            self._generator.generate(
                df, recommendation, theme, config, tmp_path,
                annotations=annotations,
                on_progress=self._show_progress,
            )
            print()  # プログレスバー後の改行

            # 6. フェード効果・最終出力
            print("🎞️  フェード効果を適用中...")
            self._renderer.render(tmp_path, self._output_dir, csv_path.stem)

        except CSVScanError as e:
            print(f"\n❌ CSVエラー: {e}", file=sys.stderr)
            sys.exit(1)
        except RenderingError as e:
            print(f"\n❌ レンダリングエラー: {e}", file=sys.stderr)
            sys.exit(1)

    def _show_progress(self, progress: float) -> None:
        filled = int(progress * 20)
        bar = "█" * filled + "░" * (20 - filled)
        pct = int(progress * 100)
        print(f"\r  [{bar}] {pct}%", end="", flush=True)
