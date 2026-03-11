"""
models.py — Core data classes for AU PM Hiring Signal Engine
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Signal:
    """A single hiring signal emitted by any collector."""

    # Required fields (Collector contract)
    source: str          # ats / seek / indeed / jora / wellfound / reddit / slack
    signal_type: str     # job_post / career_page_post / forum_post / growth_signal
    company: str
    role_title: str
    location: str
    url: str
    raw_text: str

    # Optional fields
    posted_time: Optional[str] = None   # ISO string or blank
    notes: Optional[str] = None

    # Fields set by pipeline
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    dedupe_hash: str = ""
    discovered_time: str = field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    score: int = 0
    is_high_priority: bool = False
    remote_likelihood: str = "Low"
    status: str = "New"  # New / Notified / Archived

    def to_sheet_row(self) -> list:
        """Return ordered list matching hiring_signals tab columns."""
        return [
            self.signal_id,
            self.dedupe_hash,
            self.source,
            self.signal_type,
            self.company,
            self.role_title,
            self.location,
            self.url,
            self.posted_time or "",
            self.discovered_time,
            self.score,
            str(self.is_high_priority).upper(),
            self.remote_likelihood,
            self.raw_text[:500],  # truncate for sheet
            self.notes or "",
            self.status,
        ]


@dataclass
class CollectorState:
    """Tracks runtime state for each collector/query."""

    source: str
    key: str
    last_run_time: str = ""
    last_success_time: str = ""
    last_cursor: str = ""
    last_error: str = ""

    def to_sheet_row(self) -> list:
        return [
            self.source,
            self.key,
            self.last_run_time,
            self.last_success_time,
            self.last_cursor,
            self.last_error,
        ]
