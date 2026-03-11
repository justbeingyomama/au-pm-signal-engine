"""
deduper.py — MD5-based deduplication for hiring signals
"""
from __future__ import annotations

import hashlib


def make_dedupe_hash(company: str, role_title: str, location: str, url: str) -> str:
    """
    Create a stable MD5 dedupe hash from the four key fields.
    Normalizes input to lowercase + stripped before hashing.
    """
    parts = [
        company.lower().strip(),
        role_title.lower().strip(),
        location.lower().strip(),
        url.lower().strip(),
    ]
    raw = "|".join(parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def existing_hashes(signals_rows: list[list]) -> set[str]:
    """
    Extract the set of existing dedupe_hash values from sheet rows.
    Assumes dedupe_hash is the second column (index 1).
    """
    return {row[1] for row in signals_rows if len(row) > 1 and row[1]}
