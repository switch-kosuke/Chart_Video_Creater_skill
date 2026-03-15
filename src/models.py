"""共通データモデル — ChartType / ChartRecommendation"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
