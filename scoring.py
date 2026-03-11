"""
scoring.py — Signal scoring logic (0–10 scale)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

# Location keywords for whole-word matching (to avoid 'Not Australia' false-positives)
_AU_LOCATION_WORDS = [
    "australia", "sydney", "melbourne", "brisbane",
    "perth", "adelaide", "canberra",
]
_AU_LOCATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in _AU_LOCATION_WORDS) + r")\b"
    r"|\bremote\s+au\b",
    re.IGNORECASE,
)

# Source base scores
SOURCE_SCORES = {
    "seek": 5,
    "indeed": 5,
    "jora": 5,
    "wellfound": 5,
    "ats": 4,
    "reddit": 3,
    "slack": 3,
}

# Signal type base scores
SIGNAL_TYPE_SCORES = {
    "job_post": 5,
    "career_page_post": 4,
    "forum_post": 3,
    "growth_signal": 2,
}


def score_signal(
    source: str,
    signal_type: str,
    location: str,
    posted_time: Optional[str],
    raw_text: str = "",
) -> int:
    """
    Score a signal from 0–10.

    Rules:
    - Base score from signal_type (job_post=5, career_page=4, forum=3)
    - Location match (AU city/region): +2
    - Posted within 24h (if posted_time known): +2
    - Cap at 10
    """
    score = SIGNAL_TYPE_SCORES.get(signal_type, 2)

    # Location boost — whole-word match to avoid 'Not Australia' false-positives
    if _AU_LOCATION_PATTERN.search(location):
        score += 2

    # Recency boost
    if posted_time and _within_24h(posted_time):
        score += 2

    return min(score, 10)


def calculate_remote_likelihood(location: str, title: str, text: str) -> str:
    """Determine the likelihood of a role being remote (Low, Med, High)."""
    loc_lower = location.lower()
    title_lower = title.lower()
    combined = f"{loc_lower} {title_lower} {text.lower()}"
    
    if "remote" in loc_lower or "wfh" in loc_lower:
        return "High"
        
    remote_keywords = ["remote", "work from home", "wfh", "work anywhere"]
    if any(k in combined for k in remote_keywords):
        if any(k in title_lower for k in ["remote", "wfh"]):
            return "High"
        return "Med"
        
    return "Low"


def _within_24h(posted_time: str) -> bool:
    """Return True if posted_time is within the last 24 hours."""
    try:
        # Try ISO 8601
        dt = datetime.fromisoformat(posted_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - dt).total_seconds() < 86400
    except Exception:
        return False
