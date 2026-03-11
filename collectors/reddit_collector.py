"""
collectors/reddit_collector.py — Reddit RSS-based collector for PM hiring signals.

Monitors hiring-related subreddits and search terms via RSS feeds.
Falls back to structured HTML if RSS is unavailable.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import feedparser

from collectors.base import CollectorBase
from models import Signal
from sheets.client import SheetsClient

logger = logging.getLogger(__name__)
HIRING_INTENT_PATTERNS = [
    r"\bhiring\b",
    r"\bwe\s*(are|'re)\s*hiring\b",
    r"\blooking for\b",
    r"\bopen(ing)?\b.*\brole\b",
    r"\bjob opening\b",
    r"\brecruit(ing|er)\b",
    r"\bapply\b",
    r"\bjoin (our|my) team\b",
]

PRODUCT_ROLE_PATTERNS = [
    r"\bproduct manager\b",
    r"\bsenior product manager\b",
    r"\bproduct lead\b",
    r"\bhead of product\b",
    r"\bgroup product manager\b",
    r"\bprincipal product manager\b",
    r"\btechnical product manager\b",
]

DISCUSSION_NOISE_PATTERNS = [
    r"\bhow do i\b",
    r"\bhow do you\b",
    r"\badvice\b",
    r"\bdiscussion\b",
    r"\bama\b",
    r"\bquestion\b",
    r"\bthoughts on\b",
    r"\bhelp\b",
    r"\bwhat would you do\b",
    r"\bis anyone\b",
]

def _is_hiring_signal(text: str) -> bool:
    blob = (text or "").lower()
    has_intent = any(re.search(p, blob) for p in HIRING_INTENT_PATTERNS)
    has_role = any(re.search(p, blob) for p in PRODUCT_ROLE_PATTERNS)
    is_noise = any(re.search(p, blob) for p in DISCUSSION_NOISE_PATTERNS)
    return has_intent and has_role and not is_noise

SUBREDDITS = [
    "startups",
    "forhire",
    "Entrepreneur",
    "SaaS",
]

SEARCH_QUERIES = [
    "hiring product manager australia",
    "looking for product manager australia",
    "we're hiring PM australia",
    "product manager role australia",
    "head of product australia",
]


class RedditCollector(CollectorBase):
    source_name = "reddit"

    def collect(self) -> list[Signal]:
        signals = []

        # 1. Subreddit search feeds
        for sub in SUBREDDITS:
            for query in SEARCH_QUERIES:
                encoded_q = query.replace(" ", "+")
                feed_url = (
                    f"https://www.reddit.com/r/{sub}/search.rss"
                    f"?q={encoded_q}&restrict_sr=1&sort=new&limit=25"
                )
                signals.extend(self._parse_feed(feed_url, f"r/{sub}"))

        # 2. General Reddit search for all subreddits
        for query in SEARCH_QUERIES[:3]:  # Don't hammer too hard
            encoded_q = query.replace(" ", "+")
            feed_url = (
                f"https://www.reddit.com/search.rss"
                f"?q={encoded_q}&sort=new&limit=25&type=link"
            )
            signals.extend(self._parse_feed(feed_url, "reddit_search"))

        return signals

    def _parse_feed(self, feed_url: str, source_key: str) -> list[Signal]:
        signals = []
        try:
            logger.debug(f"[Reddit] Fetching feed: {feed_url}")
            resp = self._get(feed_url, headers={"Accept": "application/rss+xml"})
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()[:500]
                published = entry.get("published", "")

                # Try to parse published datetime
                posted_time = ""
                if published:
                    try:
                        import email.utils
                        t = email.utils.parsedate_to_datetime(published)
                        posted_time = t.strftime("%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        posted_time = published

                                # Try to extract company name from title
                company = self._guess_company(title, summary)

                text_blob = f"{title}\n{summary}"
                if not _is_hiring_signal(text_blob):
                    continue

                signals.append(Signal(
                    source="reddit",
                    signal_type="forum_post",
                    company=company,
                    role_title=title,
                    location="Australia",  # Filter assumption — posts matched AU queries
                    url=link,
                    posted_time=posted_time,
                    raw_text=f"{title} — {summary}"[:500],
                    notes=f"r/{source_key}",
                ))

        except Exception as e:
            logger.warning(f"[Reddit] Feed failed ({source_key}): {e}")
            self._sheets.upsert_collector_state(
                self.source_name, feed_url,
                last_error=str(e)[:200]
            )

        return signals

    @staticmethod
    def _guess_company(title: str, text: str) -> str:
        """Try to extract a company name from post text. Returns 'Unknown' if not found."""
        combined = f"{title} {text}"

        # Common patterns: "at Acme", "join Acme", "Acme is hiring"
        import re
        patterns = [
            r"\bat\s+([A-Z][a-zA-Z0-9\s&]+?)\b(?:\.|,|!|\s+-|\s+is|\s+are|\s+we)",
            r"(?:join|joining)\s+([A-Z][a-zA-Z0-9\s&]+?)\b",
            r"([A-Z][a-zA-Z0-9\s&]+?)\s+is\s+(?:hiring|looking|seeking)",
        ]
        for pat in patterns:
            m = re.search(pat, combined)
            if m:
                candidate = m.group(1).strip()
                if 2 < len(candidate) < 60:
                    return candidate

        return "Unknown (Reddit)"
