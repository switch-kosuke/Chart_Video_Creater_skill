"""ChartGenerator — チャートタイプ別アニメーション動画生成"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # ヘッドレス環境対応

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, FFMpegWriter

import bar_chart_race as bcr

from src.data_analyzer import ChartRecommendation, ChartType
from src.theme_manager import ThemeConfig


class RenderingError(Exception):
    """動画生成エラー"""


@dataclass
class VideoConfig:
    figsize: tuple[float, float] = (10.8, 19.2)
    dpi: int = 100
    fps: int = 30
    duration_seconds: int = 30


class ChartGenerator:
    def generate(
        self,
        df: pd.DataFrame,
        recommendation: ChartRecommendation,
        theme: ThemeConfig,
        config: VideoConfig,
        output_path: Path,
        annotations: list | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """チャートタイプに応じてジェネレーターへ委譲する。"""
        match recommendation.chart_type:
            case ChartType.BAR_RACE:
                return BarRaceGenerator().generate(
                    df, recommendation, theme, config, output_path,
                    annotations=annotations, on_progress=on_progress,
                )
            case ChartType.ANIMATED_BAR:
                return AnimatedChartGenerator().generate_bar(
                    df, recommendation, theme, config, output_path,
                    annotations=annotations, on_progress=on_progress,
                )
            case ChartType.ANIMATED_LINE:
                return AnimatedChartGenerator().generate_line(
                    df, recommendation, theme, config, output_path,
                    annotations=annotations, on_progress=on_progress,
                )
            case _:
                raise RenderingError(f"未対応のチャートタイプ: {recommendation.chart_type}")


class BarRaceGenerator:
    def generate(
        self,
        df: pd.DataFrame,
        recommendation: ChartRecommendation,
        theme: ThemeConfig,
        config: VideoConfig,
        output_path: Path,
        annotations: list | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """bar_chart_race で順位変動アニメーションを生成する。"""
        # wide format に変換（x_column を index に設定）
        wide_df = (
            df.set_index(recommendation.x_column)[recommendation.y_columns]
            .copy()
        )

        steps = max(1, config.duration_seconds * config.fps // max(len(wide_df), 1))

        bcr.bar_chart_race(
            df=wide_df,
            filename=str(output_path),
            figsize=config.figsize,
            dpi=config.dpi,
            period_length=int(1000 * config.duration_seconds / max(len(wide_df), 1)),
            steps_per_period=steps,
            colors=theme.bar_colors,
            title="",
            bar_textposition="inside",
            fig_kwargs={"facecolor": theme.background_color},
            bar_kwargs={"edgecolor": "none"},
            tick_label_size=14,
            period_label={"x": 0.95, "y": 0.05, "ha": "right", "color": theme.text_color},
        )

        if on_progress:
            on_progress(1.0)

        return output_path


class AnimatedChartGenerator:
    def generate_bar(
        self,
        df: pd.DataFrame,
        recommendation: ChartRecommendation,
        theme: ThemeConfig,
        config: VideoConfig,
        output_path: Path,
        annotations: list | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """棒グラフが下から伸びるアニメーションを生成する。"""
        x_col = recommendation.x_column
        y_col = recommendation.y_columns[0]
        categories = df[x_col].tolist()
        values = df[y_col].tolist()
        total_frames = config.fps * config.duration_seconds

        fig, ax = plt.subplots(figsize=config.figsize)
        fig.patch.set_facecolor(theme.background_color)
        ax.set_facecolor(theme.background_color)

        def update(frame: int) -> None:
            ax.clear()
            ax.set_facecolor(theme.background_color)
            progress = (frame + 1) / total_frames
            current_vals = [v * min(progress * 2, 1.0) for v in values]
            bars = ax.barh(categories, current_vals, color=theme.bar_colors[: len(categories)])
            ax.set_xlim(0, max(values) * 1.1)
            ax.tick_params(colors=theme.text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(theme.text_color)
            if on_progress:
                on_progress(frame / total_frames)

        ani = FuncAnimation(fig, update, frames=total_frames, interval=1000 / config.fps)
        writer = FFMpegWriter(fps=config.fps, bitrate=3000, codec="libx264")
        ani.save(str(output_path), writer=writer, dpi=config.dpi)
        plt.close(fig)
        return output_path

    def generate_line(
        self,
        df: pd.DataFrame,
        recommendation: ChartRecommendation,
        theme: ThemeConfig,
        config: VideoConfig,
        output_path: Path,
        annotations: list | None = None,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """折れ線が左から右へ描かれるアニメーションを生成する。"""
        x_col = recommendation.x_column
        y_col = recommendation.y_columns[0]
        x_vals = df[x_col].tolist()
        y_vals = df[y_col].tolist()
        total_frames = config.fps * config.duration_seconds

        # x_vals → 等間隔の数値インデックスに変換
        x_numeric = list(range(len(x_vals)))

        # 各データ点間を補間
        x_interp = np.linspace(0, len(x_vals) - 1, total_frames)
        y_interp = np.interp(x_interp, x_numeric, y_vals)

        fig, ax = plt.subplots(figsize=config.figsize)
        fig.patch.set_facecolor(theme.background_color)
        ax.set_facecolor(theme.background_color)
        ax.set_xlim(0, len(x_vals) - 1)
        ax.set_ylim(min(y_vals) * 0.9, max(y_vals) * 1.1)

        line_color = theme.bar_colors[0]

        def update(frame: int) -> None:
            ax.clear()
            ax.set_facecolor(theme.background_color)
            ax.set_xlim(0, len(x_vals) - 1)
            ax.set_ylim(min(y_vals) * 0.9, max(y_vals) * 1.1)
            ax.plot(x_interp[: frame + 1], y_interp[: frame + 1], color=line_color, linewidth=3)
            ax.tick_params(colors=theme.text_color)
            if on_progress:
                on_progress(frame / total_frames)

        ani = FuncAnimation(fig, update, frames=total_frames, interval=1000 / config.fps)
        writer = FFMpegWriter(fps=config.fps, bitrate=3000, codec="libx264")
        ani.save(str(output_path), writer=writer, dpi=config.dpi)
        plt.close(fig)
        return output_path
