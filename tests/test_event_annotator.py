"""EventAnnotator のテスト"""
from __future__ import annotations

import pytest
from pathlib import Path

from src.event_annotator import EventAnnotator, EventAnnotation


# ── 6.1: events.csv 読み込みとフレーム番号変換 ────────

class TestLoadEvents:
    def test_loads_events_from_csv(self, tmp_path):
        csv = tmp_path / "events.csv"
        csv.write_text("period,category,text\n2024-01,Apple,新製品発表\n2024-03,Google,大型アップデート", encoding="utf-8")
        time_index = ["2024-01", "2024-02", "2024-03"]
        events = EventAnnotator().load_events(tmp_path, time_index)
        assert len(events) == 2

    def test_returns_empty_when_no_events_csv(self, tmp_path):
        events = EventAnnotator().load_events(tmp_path, ["2024-01", "2024-02"])
        assert events == []

    def test_maps_period_to_frame_number(self, tmp_path):
        csv = tmp_path / "events.csv"
        csv.write_text("period,category,text\n2024-02,Apple,テスト", encoding="utf-8")
        time_index = ["2024-01", "2024-02", "2024-03"]
        events = EventAnnotator().load_events(tmp_path, time_index, fps=30, steps_per_period=30)
        # 2024-02 は index 1 → フレーム 30
        assert events[0].frame == 30

    def test_event_has_correct_category_and_text(self, tmp_path):
        csv = tmp_path / "events.csv"
        csv.write_text("period,category,text\n2024-01,Meta,買収完了", encoding="utf-8")
        events = EventAnnotator().load_events(tmp_path, ["2024-01", "2024-02"])
        assert events[0].category == "Meta"
        assert events[0].text == "買収完了"

    def test_skips_unknown_period(self, tmp_path):
        csv = tmp_path / "events.csv"
        csv.write_text("period,category,text\n9999-99,Apple,未来のイベント", encoding="utf-8")
        events = EventAnnotator().load_events(tmp_path, ["2024-01", "2024-02"])
        assert events == []

    def test_multiple_events_same_period(self, tmp_path):
        csv = tmp_path / "events.csv"
        csv.write_text(
            "period,category,text\n2024-01,Apple,発表A\n2024-01,Google,発表B",
            encoding="utf-8",
        )
        events = EventAnnotator().load_events(tmp_path, ["2024-01", "2024-02"])
        assert len(events) == 2


# ── 6.2: 吹き出しアルファ値（フェード処理）────────────

class TestGetFrameAnnotations:
    @pytest.fixture
    def annotator(self):
        return EventAnnotator()

    @pytest.fixture
    def single_event(self):
        return [EventAnnotation(frame=60, category="Apple", text="テスト")]

    def test_no_annotation_before_event_frame(self, annotator, single_event):
        result = annotator.get_frame_annotations(59, single_event)
        assert result == []

    def test_annotation_starts_at_event_frame(self, annotator, single_event):
        result = annotator.get_frame_annotations(60, single_event)
        assert len(result) == 1
        assert result[0]["category"] == "Apple"

    def test_fade_in_alpha_increases(self, annotator, single_event):
        alpha_start = annotator.get_frame_annotations(60, single_event)[0]["alpha"]
        alpha_mid = annotator.get_frame_annotations(67, single_event)[0]["alpha"]
        assert alpha_start < alpha_mid

    def test_full_visible_at_mid_point(self, annotator, single_event):
        # フェードイン完了後（15フレーム後）は alpha=1.0
        result = annotator.get_frame_annotations(75, single_event)
        assert result[0]["alpha"] == pytest.approx(1.0)

    def test_fade_out_alpha_decreases(self, annotator, single_event):
        alpha_after_peak = annotator.get_frame_annotations(85, single_event)[0]["alpha"]
        alpha_near_end = annotator.get_frame_annotations(88, single_event)[0]["alpha"]
        assert alpha_after_peak > alpha_near_end

    def test_annotation_gone_after_display_period(self, annotator, single_event):
        # 60 + 30フレーム(1秒) 後は非表示
        result = annotator.get_frame_annotations(91, single_event)
        assert result == []

    def test_annotation_contains_text(self, annotator, single_event):
        result = annotator.get_frame_annotations(60, single_event)
        assert result[0]["text"] == "テスト"
