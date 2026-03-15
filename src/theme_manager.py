"""ThemeManager — カラーテーマ定義と適用"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeConfig:
    name: str
    display_name: str
    background_color: str
    bar_colors: list[str]
    text_color: str
    font_family: str


_THEMES: dict[str, ThemeConfig] = {
    "dark": ThemeConfig(
        name="dark",
        display_name="ダーク（YouTube向け）",
        background_color="#0f0f0f",
        bar_colors=[
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
        ],
        text_color="#FFFFFF",
        font_family="DejaVu Sans",
    ),
    "pastel": ThemeConfig(
        name="pastel",
        display_name="パステル（TikTok向け）",
        background_color="#FFF9F9",
        bar_colors=[
            "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9",
            "#BAE1FF", "#E8BAFF", "#FFB3F7", "#B3FFE8",
        ],
        text_color="#333333",
        font_family="DejaVu Sans",
    ),
    "default": ThemeConfig(
        name="default",
        display_name="デフォルト（汎用）",
        background_color="#FFFFFF",
        bar_colors=[
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        ],
        text_color="#000000",
        font_family="DejaVu Sans",
    ),
}


class ThemeManager:
    def get_theme(self, name: str) -> ThemeConfig:
        """テーマ名で ThemeConfig を返す。存在しなければ KeyError。"""
        if name not in _THEMES:
            raise KeyError(f"テーマ '{name}' が見つかりません。利用可能: {list(_THEMES.keys())}")
        return _THEMES[name]

    def list_themes(self) -> list[ThemeConfig]:
        """全テーマを定義順で返す。"""
        return list(_THEMES.values())
