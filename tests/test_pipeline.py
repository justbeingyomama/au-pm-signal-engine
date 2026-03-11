"""
tests/test_pipeline.py — Unit tests for the processing pipeline using mocks.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from models import Signal
from pipeline import Pipeline, passes_role_filter


def make_test_signal(**kwargs) -> Signal:
    defaults = dict(
        source="seek",
        signal_type="job_post",
        company="TestCo",
        role_title="Product Manager",
        location="Sydney, Australia",
        url="https://example.com/job/1",
        raw_text="Seeking a Product Manager in Sydney",
    )
    defaults.update(kwargs)
    return Signal(**defaults)


class TestPipeline:
    def setup_method(self):
        self.mock_sheets = MagicMock()
        self.mock_sheets.get_all_signal_rows.return_value = []
        self.mock_alerter = MagicMock()
        self.mock_alerter._enabled = False
        self.pipeline = Pipeline(self.mock_sheets, self.mock_alerter)

    def test_valid_signal_is_written(self):
        signal = make_test_signal()
        written = self.pipeline.process([signal])
        assert written == 1
        self.mock_sheets.append_signal.assert_called_once()

    def test_excluded_role_is_not_written(self):
        signal = make_test_signal(role_title="Program Manager")
        written = self.pipeline.process([signal])
        assert written == 0
        self.mock_sheets.append_signal.assert_not_called()

    def test_duplicate_is_not_written(self):
        signal = make_test_signal()
        # First pass writes it
        self.pipeline.process([signal])
        count_before = self.mock_sheets.append_signal.call_count
        # Second pass should dedupe
        self.pipeline.process([signal])
        assert self.mock_sheets.append_signal.call_count == count_before

    def test_score_is_set_on_signal(self):
        signal = make_test_signal(location="Melbourne, Australia")
        self.pipeline.process([signal])
        # After pipeline, score should be >= 5 (job_post base)
        call_args = self.mock_sheets.append_signal.call_args[0][0]
        score = int(call_args[10])  # score is at index 10
        assert score >= 5

    def test_high_priority_triggers_alert(self):
        self.mock_alerter._enabled = True
        self.mock_alerter.send_signal_alert.return_value = True
        # High-scoring: seek job_post + Australia location + recent
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        signal = make_test_signal(location="Sydney, Australia", posted_time=recent)
        self.pipeline.process([signal])
        self.mock_alerter.send_signal_alert.assert_called_once()

    def test_multiple_signals_all_written(self):
        signals = [
            make_test_signal(url=f"https://example.com/job/{i}", role_title="Product Manager")
            for i in range(5)
        ]
        written = self.pipeline.process(signals)
        assert written == 5
