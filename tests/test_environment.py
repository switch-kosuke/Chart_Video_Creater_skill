"""環境チェック機能のテスト"""
import os
import pytest
from unittest.mock import patch
from main import check_environment


def test_check_env_fails_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        ok, errors = check_environment()
    assert not ok
    assert any("ANTHROPIC_API_KEY" in e for e in errors)


def test_check_env_fails_without_ffmpeg(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("shutil.which", return_value=None):
        ok, errors = check_environment()
    assert not ok
    assert any("FFmpeg" in e for e in errors)


def test_check_env_passes_with_all_requirements(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        ok, errors = check_environment()
    assert ok
    assert errors == []
