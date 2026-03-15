"""ChartGenerator — チャートタイプ別アニメーション動画生成"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # ヘッドレス環境対応

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
from matplotlib.animation import FuncAnimation, FFMpegWriter


def _setup_japanese_font() -> None:
    """Windows/Mac/Linux で日本語フォントを自動設定する。"""
    candidates = [
        "Yu Gothic", "YuGothic", "Meiryo", "MS Gothic", "MS PGothic",
        "Hiragino Sans", "Hiragino Kaku Gothic Pro",
        "Noto Sans CJK JP", "IPAexGothic", "IPAPGothic",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            return
    # フォールバック: matplotlib デフォルト（□になる可能性あり）


_LABEL_MAP: dict[str, str] = {
    "平均年収": "Average Income / 平均年収",
    "物価指数": "CPI / 物価指数",
    "平均年収(1980=100)": "Average Income / 平均年収",
    "物価指数(1980=100)": "CPI / 物価指数",
}


def _bilingual_label(col: str) -> str:
    """列名を日英併記ラベルに変換する。マッチしなければそのまま返す。"""
    # 完全一致
    if col in _LABEL_MAP:
        return _LABEL_MAP[col]
    # 前方一致（サフィックス付き列名など）
    for key, label in _LABEL_MAP.items():
        if col.startswith(key):
            return label
    return col


import bar_chart_race as bcr

from src.models import ChartRecommendation, ChartType
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
        hold_seconds: int = 3,
    ) -> Path:
        """折れ線が左から右へ描かれ、表示範囲が動的に広がるアニメーションを生成する。"""
        _setup_japanese_font()

        x_col = recommendation.x_column
        # _actual サフィックス列はラベル用なのでプロット対象から除外
        y_cols = [c for c in recommendation.y_columns if not c.endswith("_actual")]
        x_vals = df[x_col].tolist()
        anim_frames = config.fps * config.duration_seconds
        hold_frames = config.fps * hold_seconds
        total_frames = anim_frames + hold_frames

        x_numeric = np.arange(len(x_vals), dtype=float)
        x_interp = np.linspace(0, len(x_vals) - 1, anim_frames)

        # イベントアノテーションを x_numeric 座標へマッピング
        # period が x_vals に完全一致しない場合は最近傍の値を使用
        event_positions: list[tuple[float, str]] = []  # (x_numeric_pos, text)
        if annotations:
            # 数値変換できる場合は数値で近傍探索、できない場合は文字列一致
            x_val_strs = [str(v) for v in x_vals]
            try:
                x_val_nums = [float(v) for v in x_vals]
                numeric_mode = True
            except (ValueError, TypeError):
                numeric_mode = False

            for ev in annotations:
                if ev.period in x_val_strs:
                    idx = x_val_strs.index(ev.period)
                elif numeric_mode:
                    try:
                        ev_num = float(ev.period)
                        idx = min(range(len(x_val_nums)),
                                  key=lambda i: abs(x_val_nums[i] - ev_num))
                    except ValueError:
                        continue
                else:
                    continue
                event_positions.append((x_numeric[idx], ev.text))

        # 全Y列を補間（_actual列も含む）— アニメーション分のみ
        y_interps: dict[str, np.ndarray] = {}
        for col in df.columns:
            if col != x_col:
                y_interps[col] = np.interp(x_interp, x_numeric, df[col].tolist())

        fig, ax = plt.subplots(figsize=config.figsize)
        fig.patch.set_facecolor(theme.background_color)
        ax.set_facecolor(theme.background_color)
        # YouTube Shorts セーフゾーン対応（1080×1920px）
        #   下35%: YouTube UI → bottom=0.37（UIギリギリまで使う）
        #   右18%: ボタン類 → right=0.76
        #   上15%: タブUI → top=0.80（凡例スペース込み）
        fig.subplots_adjust(left=0.12, right=0.76, top=0.80, bottom=0.37)

        # X軸ラベル用: 表示するデータ点のインデックスを間引く
        max_ticks = 6
        step = max(1, len(x_vals) // max_ticks)
        tick_idx = list(range(0, len(x_vals), step))
        if (len(x_vals) - 1) not in tick_idx:
            tick_idx.append(len(x_vals) - 1)

        def update(frame: int) -> None:
            ax.clear()
            ax.set_facecolor(theme.background_color)

            # ホールドフレームは最終アニメーションフレームに固定
            f = min(frame, anim_frames - 1)
            cur_x = x_interp[f]
            cur_data = {y_col: y_interps[y_col][: f + 1] for y_col in y_cols}

            # ── X軸: 描画済み範囲に合わせて拡張 ──
            x_margin = max(0.3, cur_x * 0.05)
            ax.set_xlim(-x_margin, cur_x + x_margin)

            # ── Y軸: 現在描画済みの値に合わせて動的に拡張 ──
            all_visible = np.concatenate(list(cur_data.values()))
            y_min, y_max = all_visible.min(), all_visible.max()
            y_span = max(y_max - y_min, 1.0)
            # 上部に凡例スペース分のヘッドルームを確保（約40%）
            ax.set_ylim(y_min - y_span * 0.08, y_max + y_span * 0.40)

            # ── 各折れ線を描画 ──
            for i, y_col in enumerate(y_cols):
                color = theme.bar_colors[i % len(theme.bar_colors)]
                xs = x_interp[: f + 1]
                ys = cur_data[y_col]
                ax.plot(xs, ys, color=color, linewidth=4, label=_bilingual_label(y_col))
                # 先端に現在値ラベル（_actual列があればそちらを使用）
                actual_col = f"{y_col}_actual"
                if actual_col in y_interps:
                    label_text = f"{y_interps[actual_col][f]:.0f}万円"
                else:
                    label_text = f"{ys[-1]:.1f}"
                ax.annotate(
                    label_text,
                    xy=(xs[-1], ys[-1]),
                    color=color,
                    fontsize=36,
                    fontweight="bold",
                    xytext=(10, 0),
                    textcoords="offset points",
                    va="center",
                )

            # ── イベントアノテーション: 通過済みの年に縦線＋ラベル ──
            ylim = ax.get_ylim()
            for ev_x, ev_text in event_positions:
                if ev_x > cur_x + 0.01:
                    continue  # まだ到達していない
                ax.axvline(x=ev_x, color=theme.text_color, linewidth=1.5,
                           linestyle="--", alpha=0.5)
                ax.text(
                    ev_x, ylim[1] * 0.98, ev_text,
                    color=theme.text_color, fontsize=18, fontweight="bold",
                    ha="center", va="top", alpha=0.85,
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor=theme.background_color,
                              edgecolor=theme.text_color,
                              alpha=0.7, linewidth=1),
                )

            # ── X軸目盛: 現在表示範囲内のものだけ表示 ──
            visible_ticks = [i for i in tick_idx if x_numeric[i] <= cur_x + 0.01]
            if visible_ticks:
                ax.set_xticks([x_numeric[i] for i in visible_ticks])
                ax.set_xticklabels(
                    [str(x_vals[i]) for i in visible_ticks],
                    rotation=45, ha="right", fontsize=22,
                )

            # ── 現在の年を大きく表示 ──
            cur_label_idx = min(int(cur_x + 0.5), len(x_vals) - 1)
            ax.text(
                0.97, 0.08, str(x_vals[cur_label_idx]),
                transform=ax.transAxes,
                fontsize=80, fontweight="bold",
                color=theme.text_color, alpha=0.35,
                ha="right", va="bottom",
            )

            # ── 凡例: プロットエリア外・上部に配置 ──
            if len(y_cols) > 1:
                leg = ax.legend(
                    fontsize=36,
                    loc="lower left",
                    bbox_to_anchor=(0, 1.02),
                    borderaxespad=0,
                    facecolor=theme.background_color,
                    labelcolor=theme.text_color,
                    framealpha=0,
                    edgecolor="none",
                    borderpad=0.5,
                )
                for text in leg.get_texts():
                    text.set_fontweight("bold")
            ax.tick_params(colors=theme.text_color, labelsize=22)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("bottom", "left"):
                ax.spines[side].set_color(theme.text_color)

            if on_progress:
                on_progress(frame / total_frames)

        ani = FuncAnimation(fig, update, frames=total_frames, interval=1000 / config.fps)
        writer = FFMpegWriter(fps=config.fps, bitrate=3000, codec="libx264")
        ani.save(str(output_path), writer=writer, dpi=config.dpi)
        plt.close(fig)
        return output_path

