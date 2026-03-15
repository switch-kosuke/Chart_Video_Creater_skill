"""DataAnalyzer — Claude API による CSV データ分析・チャートタイプ推薦"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum

import anthropic

from src.csv_scanner import CSVMetadata


class AnalysisError(Exception):
    """AI 分析エラー"""


class ChartType(Enum):
    BAR_RACE = "bar_race"
    ANIMATED_BAR = "animated_bar"
    ANIMATED_LINE = "animated_line"


@dataclass
class ChartRecommendation:
    chart_type: ChartType
    reason: str
    x_column: str
    y_columns: list[str]
    category_column: str | None = None


_PROMPT_TEMPLATE = """\
あなたはデータビジュアライゼーションの専門家です。
以下の CSV データ構造を分析し、TikTok・YouTube Shorts 向けのショート動画（縦型・30秒）で
最も視聴者を引き付けるチャートタイプを1つ推薦してください。

## CSV情報
- 列名: {columns}
- 行数: {row_count}
- 時系列列あり: {has_datetime}
- サンプルデータ (先頭5行): {sample}

## 選択肢
- bar_race: 時系列 × 複数カテゴリの順位変動（最もバズりやすい）
- animated_bar: カテゴリ比較の棒グラフアニメーション
- animated_line: 時系列推移の折れ線アニメーション

## 出力形式（JSON のみ、他の文字は不要）
{{"chart_type": "bar_race|animated_bar|animated_line",
  "reason": "推薦理由（日本語1文）",
  "x_column": "X軸に使う列名",
  "y_columns": ["Y軸列名1", "Y軸列名2"],
  "category_column": "カテゴリ列名またはnull"}}
"""


class DataAnalyzer:
    MODEL = "claude-haiku-4-5-20251001"

    def analyze(self, metadata: CSVMetadata) -> ChartRecommendation:
        """CSV メタデータを分析してチャートタイプを推薦する。API 失敗時はフォールバック。"""
        try:
            return self._call_api(metadata)
        except Exception as e:
            print(f"⚠️  AI 分析に失敗しました（{e}）。ルールベース推薦に切り替えます。")
            return self._fallback_recommend(metadata)

    def _call_api(self, metadata: CSVMetadata) -> ChartRecommendation:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        prompt = _PROMPT_TEMPLATE.format(
            columns=metadata.columns,
            row_count=metadata.row_count,
            has_datetime=metadata.has_datetime_column,
            sample=json.dumps(metadata.sample_rows[:5], ensure_ascii=False),
        )
        message = client.messages.create(
            model=self.MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        payload = json.loads(raw)
        return self._parse_payload(payload, metadata)

    def _parse_payload(self, payload: dict, metadata: CSVMetadata) -> ChartRecommendation:
        chart_type = ChartType(payload["chart_type"])
        numeric_cols = [
            c for c in metadata.columns
            if c != payload.get("x_column")
        ]
        y_columns = payload.get("y_columns") or numeric_cols[:3]
        return ChartRecommendation(
            chart_type=chart_type,
            reason=payload.get("reason", ""),
            x_column=payload.get("x_column", metadata.columns[0]),
            y_columns=y_columns,
            category_column=payload.get("category_column"),
        )

    def _fallback_recommend(self, metadata: CSVMetadata) -> ChartRecommendation:
        """ルールベースでチャートタイプを推薦する。"""
        numeric_cols = [
            c for c in metadata.columns
            if c != metadata.columns[0]
        ]
        x_col = metadata.columns[0]

        if metadata.has_datetime_column and len(numeric_cols) >= 2:
            return ChartRecommendation(
                chart_type=ChartType.BAR_RACE,
                reason="時系列データと複数カテゴリがあるためバーレースを推薦します",
                x_column=x_col,
                y_columns=numeric_cols,
            )
        if metadata.has_datetime_column:
            return ChartRecommendation(
                chart_type=ChartType.ANIMATED_LINE,
                reason="時系列データの推移を折れ線で表現します",
                x_column=x_col,
                y_columns=numeric_cols[:1] or [metadata.columns[-1]],
            )
        return ChartRecommendation(
            chart_type=ChartType.ANIMATED_BAR,
            reason="カテゴリ比較データのため棒グラフを推薦します",
            x_column=x_col,
            y_columns=numeric_cols[:1] or [metadata.columns[-1]],
        )
