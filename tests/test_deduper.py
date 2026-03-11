"""
tests/test_deduper.py — Unit tests for deduplication logic.
"""
from deduper import make_dedupe_hash, existing_hashes


def test_same_input_yields_same_hash():
    h1 = make_dedupe_hash("Canva", "Product Manager", "Sydney", "https://canva.com/jobs/1")
    h2 = make_dedupe_hash("Canva", "Product Manager", "Sydney", "https://canva.com/jobs/1")
    assert h1 == h2


def test_different_role_yields_different_hash():
    h1 = make_dedupe_hash("Canva", "Product Manager", "Sydney", "https://canva.com/jobs/1")
    h2 = make_dedupe_hash("Canva", "Senior Product Manager", "Sydney", "https://canva.com/jobs/1")
    assert h1 != h2


def test_case_insensitive():
    h1 = make_dedupe_hash("CANVA", "PRODUCT MANAGER", "SYDNEY", "HTTPS://CANVA.COM/JOBS/1")
    h2 = make_dedupe_hash("canva", "product manager", "sydney", "https://canva.com/jobs/1")
    assert h1 == h2


def test_whitespace_stripped():
    h1 = make_dedupe_hash("  Canva  ", " Product Manager ", " Sydney ", " https://canva.com/jobs/1 ")
    h2 = make_dedupe_hash("Canva", "Product Manager", "Sydney", "https://canva.com/jobs/1")
    assert h1 == h2


def test_hash_is_32_char_hex():
    h = make_dedupe_hash("X", "Y", "Z", "U")
    assert len(h) == 32
    assert all(c in "0123456789abcdef" for c in h)


def test_existing_hashes_extracts_correctly():
    rows = [
        ["sig1", "aabbcc", "ats", "job_post", "Canva", "PM", "Sydney", "url"],
        ["sig2", "ddeeff", "seek", "job_post", "Atlassian", "SPM", "Melb", "url2"],
    ]
    hashes = existing_hashes(rows)
    assert "aabbcc" in hashes
    assert "ddeeff" in hashes
    assert len(hashes) == 2


def test_existing_hashes_empty_rows():
    hashes = existing_hashes([])
    assert hashes == set()
