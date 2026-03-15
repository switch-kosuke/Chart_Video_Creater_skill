"""ThemeManager のテスト"""
import pytest
from src.theme_manager import ThemeManager, ThemeConfig


class TestThemeManager:
    def test_list_themes_returns_three(self):
        themes = ThemeManager().list_themes()
        assert len(themes) == 3

    def test_all_theme_names_present(self):
        tm = ThemeManager()
        names = {t.name for t in tm.list_themes()}
        assert names == {"dark", "pastel", "default"}

    def test_get_dark_theme(self):
        t = ThemeManager().get_theme("dark")
        assert isinstance(t, ThemeConfig)
        assert t.name == "dark"
        assert t.background_color.startswith("#")
        assert len(t.bar_colors) >= 5

    def test_get_pastel_theme(self):
        t = ThemeManager().get_theme("pastel")
        assert t.name == "pastel"

    def test_get_default_theme(self):
        t = ThemeManager().get_theme("default")
        assert t.name == "default"

    def test_invalid_name_raises_key_error(self):
        with pytest.raises(KeyError):
            ThemeManager().get_theme("nonexistent")

    def test_theme_is_immutable(self):
        t = ThemeManager().get_theme("dark")
        with pytest.raises(Exception):
            t.name = "changed"  # frozen dataclass

    def test_display_name_contains_platform_hint(self):
        dark = ThemeManager().get_theme("dark")
        pastel = ThemeManager().get_theme("pastel")
        assert "YouTube" in dark.display_name
        assert "TikTok" in pastel.display_name

    def test_each_theme_has_text_color(self):
        for theme in ThemeManager().list_themes():
            assert theme.text_color.startswith("#")

    def test_each_theme_has_font_family(self):
        for theme in ThemeManager().list_themes():
            assert len(theme.font_family) > 0
