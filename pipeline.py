"""
pipeline.py — Shared processing pipeline: normalize → dedupe → score → write → alert
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from alerter import Alerter
from deduper import existing_hashes, make_dedupe_hash
from models import Signal
from scoring import score_signal, calculate_remote_likelihood
from sheets.client import SheetsClient

logger = logging.getLogger(__name__)

# ── Role keyword filters ──────────────────────────────────────────────────────

INCLUDE_KEYWORDS = [
    "product manager",
    "senior product manager",
    "product lead",
    "head of product",
    "group product manager",
    "principal product manager",
    "technical product manager",
    "product management",
]

EXCLUDE_KEYWORDS = [
    "project manager",
    "program manager",
    "delivery manager",
    "account manager",
    "product marketing manager",
    "product marketing lead",
]


def _normalize_str(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip()) if s else ""


def normalize_signal(signal: Signal) -> Signal:
    """Normalize all string fields in place."""
    signal.company = _normalize_str(signal.company)
    signal.role_title = _normalize_str(signal.role_title)
    signal.location = _normalize_str(signal.location)
    signal.url = signal.url.strip()
    signal.raw_text = _normalize_str(signal.raw_text)[:1000]
    return signal


def passes_role_filter(title: str, text: str = "") -> bool:
    """
    Return True if the role title (or text) matches include keywords
    and does NOT match any exclude keywords.
    """
    combined = (title + " " + text).lower()

    # Must match at least one include keyword
    if not any(kw in combined for kw in INCLUDE_KEYWORDS):
        return False

    # Must NOT match any exclude keyword
    if any(kw in combined for kw in EXCLUDE_KEYWORDS):
        return False

    return True


class Pipeline:
    def __init__(self, sheets: SheetsClient, alerter: Optional[Alerter] = None):
        self._sheets = sheets
        self._alerter = alerter or Alerter()
        self._known_hashes: Optional[set[str]] = None

    def _refresh_hashes(self):
        rows = self._sheets.get_all_signal_rows()
        self._known_hashes = existing_hashes(rows)

    def process(self, signals: list[Signal]) -> int:
        """
        Run all signals through the pipeline.
        Returns count of new signals written to the sheet.
        """
        if self._known_hashes is None:
            self._refresh_hashes()

        written = 0
        for signal in signals:
            # 1. Filter by role keywords
            if not passes_role_filter(signal.role_title, signal.raw_text):
                logger.debug(f"Filtered out: {signal.role_title} @ {signal.company}")
                continue

            # 2. Normalize
            signal = normalize_signal(signal)

            # 3. Dedupe
            h = make_dedupe_hash(signal.company, signal.role_title, signal.location, signal.url)
            signal.dedupe_hash = h
            if h in self._known_hashes:
                logger.debug(f"Duplicate skipped: {signal.role_title} @ {signal.company}")
                continue

            # 4. Score & Likelihood
            signal.score = score_signal(
                source=signal.source,
                signal_type=signal.signal_type,
                location=signal.location,
                posted_time=signal.posted_time,
                raw_text=signal.raw_text,
            )
            signal.remote_likelihood = calculate_remote_likelihood(
                location=signal.location,
                title=signal.role_title,
                text=signal.raw_text,
            )
            signal.is_high_priority = signal.score >= 6

            # 5. Write to sheet
            try:
                self._sheets.append_signal(signal.to_sheet_row())
                self._known_hashes.add(h)
                written += 1
                logger.info(
                    f"✅ Wrote signal [{signal.score}/10] {signal.role_title} @ "
                    f"{signal.company} ({signal.source})"
                )
            except Exception as e:
                logger.error(f"Failed to write signal to sheet: {e}")
                continue

            # 6. Alert if high-priority
            if signal.is_high_priority:
                sent = self._alerter.send_signal_alert(signal)
                if sent:
                    try:
                        self._sheets.update_signal_status(signal.signal_id, "Notified")
                    except Exception as e:
                        logger.warning(f"Could not update status to Notified: {e}")

        return written
