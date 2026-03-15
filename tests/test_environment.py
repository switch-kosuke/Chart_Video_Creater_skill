"""環境チェック機能のテスト"""
import sys
import types
import pytest
from unittest.mock import patch, MagicMock
from main import check_ffmpeg


def test_check_ffmpeg_true_when_ffmpeg_in_path():
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        assert check_ffmpeg() is True


def test_check_ffmpeg_true_when_imageio_ffmpeg_available():
    mock_imageio = types.ModuleType("imageio_ffmpeg")
    mock_imageio.get_ffmpeg_exe = lambda: "/some/ffmpeg"
    with patch("shutil.which", return_value=None), \
         patch.dict(sys.modules, {"imageio_ffmpeg": mock_imageio}):
        assert check_ffmpeg() is True


def test_check_ffmpeg_false_when_neither_available():
    mock_imageio = types.ModuleType("imageio_ffmpeg")
    mock_imageio.get_ffmpeg_exe = MagicMock(side_effect=Exception("not found"))
    with patch("shutil.which", return_value=None), \
         patch.dict(sys.modules, {"imageio_ffmpeg": mock_imageio}):
        assert check_ffmpeg() is False
