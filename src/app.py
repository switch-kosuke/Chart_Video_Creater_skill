"""VideoApp — メインオーケストレーター（インタラクティブ CLI + 全コンポーネント統合）"""
from __future__ import annotations

import sys
from pathlib import Path

from src.csv_scanner import CSVScanner, CSVScanError
from src.data_analyzer import DataAnalyzer, ChartRecommendation, ChartType, AnalysisError
from src.theme_manager import ThemeManager, ThemeConfig
from src.chart_generator import ChartGenerator, VideoConfig, RenderingError
from src.event_annotator import EventAnnotator
from src.video_renderer import VideoRenderer


class VideoApp:
    def __init__(
        self,
        work_dir: Path | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self._work_dir = work_dir or Path.cwd()
        self._output_dir = output_dir or Path("output")
        self._scanner = CSVScanner()
        self._analyzer = DataAnalyzer()
        self._theme_manager = ThemeManager()
        self._generator = ChartGenerator()
        self._annotator = EventAnnotator()
        self._renderer = VideoRenderer()

    def run(self) -> None:
        """CSV 選択 → AI 分析 → テーマ選択 → 動画生成 → 完了のメインフロー。"""
        print("🎬 ChartVideoCreater へようこそ！")
        print("=" * 40)

        try:
            # 1. CSV 選択
            csv_files = self._scanner.scan_csv_files(self._work_dir)
            csv_path = self._prompt_csv_selection(csv_files)
            df, metadata = self._scanner.load_csv(csv_path)

            # 2. AI 分析・チャートタイプ確認
            print("\n🤖 AI がデータを分析中...")
            recommendation = self._analyzer.analyze(metadata)
            recommendation = self._prompt_chart_type_selection(recommendation)

            # 3. テーマ選択
            theme = self._prompt_theme_selection()

            # 4. イベントアノテーション検出
            config = VideoConfig()
            time_index = df[recommendation.x_column].astype(str).tolist()
            steps = max(1, config.duration_seconds * config.fps // max(len(df), 1))
            annotations = self._annotator.load_events(
                self._work_dir, time_index, fps=config.fps, steps_per_period=steps,
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
        except AnalysisError as e:
            print(f"\n❌ 分析エラー: {e}", file=sys.stderr)
            sys.exit(1)
        except RenderingError as e:
            print(f"\n❌ レンダリングエラー: {e}", file=sys.stderr)
            sys.exit(1)

    # ── プロンプトメソッド ──────────────────────────────────

    def _prompt_csv_selection(self, files: list[Path]) -> Path:
        """CSV ファイルを選択させる。1ファイルのみなら自動選択。"""
        if len(files) == 1:
            print(f"\n✅ CSVファイルを自動選択しました: {files[0].name}")
            return files[0]

        print("\n📂 CSVファイルを選択してください:")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name}")

        while True:
            choice = input(f"番号を入力 (1-{len(files)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(files):
                return files[int(choice) - 1]
            print(f"⚠️  1 から {len(files)} の番号を入力してください。")

    def _prompt_chart_type_selection(
        self, recommendation: ChartRecommendation
    ) -> ChartRecommendation:
        """AI 推薦チャートタイプを表示し、変更できる1回選択 UI を提供する。"""
        chart_types = list(ChartType)
        print(f"\n📊 AI 推薦チャートタイプ: {recommendation.chart_type.value}")
        print(f"   理由: {recommendation.reason}")
        print("\n  変更する場合は番号を入力（Enter でそのまま続行）:")
        for i, ct in enumerate(chart_types, 1):
            marker = "👉 " if ct == recommendation.chart_type else "   "
            print(f"  {marker}{i}. {ct.value}")

        choice = input("番号 (Enter でスキップ): ").strip()
        if not choice:
            return recommendation
        if choice.isdigit() and 1 <= int(choice) <= len(chart_types):
            selected = chart_types[int(choice) - 1]
            return ChartRecommendation(
                chart_type=selected,
                reason=recommendation.reason,
                x_column=recommendation.x_column,
                y_columns=recommendation.y_columns,
                category_column=recommendation.category_column,
            )
        print("⚠️  無効な入力です。AI 推薦のまま続行します。")
        return recommendation

    def _prompt_theme_selection(self) -> ThemeConfig:
        """カラーテーマを選択させる。Enter でデフォルトを適用。"""
        themes = self._theme_manager.list_themes()
        print("\n🎨 カラーテーマを選択してください（Enter でデフォルト）:")
        for i, t in enumerate(themes, 1):
            print(f"  {i}. {t.display_name}")

        choice = input(f"番号を入力 (1-{len(themes)}, Enter でスキップ): ").strip()
        if not choice:
            return self._theme_manager.get_theme("default")
        if choice.isdigit() and 1 <= int(choice) <= len(themes):
            return themes[int(choice) - 1]
        print("⚠️  無効な入力です。デフォルトテーマを使用します。")
        return self._theme_manager.get_theme("default")

    # ── 内部ユーティリティ ──────────────────────────────────

    def _show_progress(self, progress: float) -> None:
        """プログレスバーをインプレース更新する。"""
        filled = int(progress * 20)
        bar = "█" * filled + "░" * (20 - filled)
        pct = int(progress * 100)
        print(f"\r  [{bar}] {pct}%", end="", flush=True)
