"""EventAnnotator — events.csv の読み込みと吹き出しアノテーション制御"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class EventAnnotation:
    frame: int
    period: str
    text: str
    category: str = ""


# 表示パラメータ（フレーム数） — 合計30フレーム（1秒@30fps）
_FADE_IN_FRAMES = 10
_HOLD_FRAMES = 10
_FADE_OUT_FRAMES = 10
_TOTAL_DISPLAY = _FADE_IN_FRAMES + _HOLD_FRAMES + _FADE_OUT_FRAMES  # = 30


class EventAnnotator:
    def load_events(
        self,
        directory: Path,
        time_index: list[str],
        fps: int = 30,
        steps_per_period: int = 30,
    ) -> list[EventAnnotation]:
        """events.csv を読み込んでフレーム番号付きイベントリストを返す。"""
        events_path = directory / "events.csv"
        if not events_path.exists():
            return []

        df = pd.read_csv(events_path, encoding="utf-8")
        period_to_frame = {
            period: idx * steps_per_period
            for idx, period in enumerate(time_index)
        }

        # 数値近傍マッチ用
        try:
            time_index_nums = [float(t) for t in time_index]
            numeric_mode = True
        except (ValueError, TypeError):
            numeric_mode = False

        result: list[EventAnnotation] = []
        for _, row in df.iterrows():
            period = str(row["period"])
            if period in period_to_frame:
                matched_period = period
                frame = period_to_frame[period]
            elif numeric_mode:
                try:
                    ev_num = float(period)
                    nearest_idx = min(range(len(time_index_nums)),
                                      key=lambda i: abs(time_index_nums[i] - ev_num))
                    matched_period = time_index[nearest_idx]
                    frame = period_to_frame[matched_period]
                except (ValueError, KeyError):
                    continue
            else:
                continue
            result.append(EventAnnotation(
                frame=frame,
                period=matched_period,
                text=str(row["text"]),
                category=str(row["category"]) if "category" in df.columns else "",
            ))

        if result:
            print(f"\n📌 イベントアノテーション {len(result)} 件を検出しました")
            for ev in result:
                print(f"   フレーム {ev.frame}: [{ev.category}] {ev.text}")

        return result

    def get_frame_annotations(
        self,
        frame: int,
        events: list[EventAnnotation],
    ) -> list[dict]:
        """指定フレームで表示すべきアノテーション（category, text, alpha）を返す。"""
        result = []
        for ev in events:
            offset = frame - ev.frame
            if offset < 0 or offset >= _TOTAL_DISPLAY:
                continue

            if offset < _FADE_IN_FRAMES:
                alpha = offset / _FADE_IN_FRAMES
            elif offset < _FADE_IN_FRAMES + _HOLD_FRAMES:
                alpha = 1.0
            else:
                fade_progress = (offset - _FADE_IN_FRAMES - _HOLD_FRAMES) / _FADE_OUT_FRAMES
                alpha = 1.0 - fade_progress

            result.append({
                "category": ev.category,
                "text": ev.text,
                "alpha": round(alpha, 4),
            })
        return result
