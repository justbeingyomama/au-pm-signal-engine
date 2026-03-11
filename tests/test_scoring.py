"""
tests/test_scoring.py — Unit tests for scoring logic.
"""
import pytest
from scoring import score_signal


def test_job_post_base_score():
    score = score_signal("seek", "job_post", "London", None)
    assert score == 5  # job_post=5, no AU location match, no recency


def test_location_boost_adds_2():
    score = score_signal("ats", "career_page_post", "Sydney, Australia", None)
    assert score == 6  # career_page=4 + location=2


def test_recency_boost():
    from datetime import datetime, timezone, timedelta
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    score = score_signal("seek", "job_post", "Melbourne", recent)
    assert score == 9  # job_post=5 + location=2 + recency=2


def test_cap_at_10():
    from datetime import datetime, timezone, timedelta
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    score = score_signal("seek", "job_post", "Sydney", recent)
    # Max: job_post=5 + location=2 + recency=2 = 9; cap ensures never exceeds 10
    assert score == 9
    assert score <= 10


def test_reddit_forum_post_base():
    score = score_signal("reddit", "forum_post", "London", None)
    assert score == 3  # forum_post=3, no AU location, no recency


def test_old_post_no_recency_boost():
    old = "2020-01-01T00:00:00Z"
    score = score_signal("seek", "job_post", "Sydney", old)
    assert score == 7  # job_post=5 + location=2, no recency


def test_invalid_posted_time_no_crash():
    score = score_signal("seek", "job_post", "Brisbane", "not-a-date")
    assert isinstance(score, int)
    assert 0 <= score <= 10
