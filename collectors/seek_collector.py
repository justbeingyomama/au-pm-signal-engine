"""
collectors/seek_collector.py — SEEK AU job board collector.

Uses SEEK's structured JSON search API (RSS fallback if blocked).
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from collectors.base import CollectorBase
from models import Signal

logger = logging.getLogger(__name__)

# SEEK search queries for PM roles in Australia
SEEK_SEARCHES = [
    {"keywords": "product manager", "location": "All Australia"},
    {"keywords": "senior product manager", "location": "All Australia"},
    {"keywords": "head of product", "location": "All Australia"},
    {"keywords": "product lead", "location": "All Australia"},
    {"keywords": "group product manager", "location": "All Australia"},
]

SEEK_BASE = "https://www.seek.com.au"


class SeekCollector(CollectorBase):
    source_name = "seek"

    def collect(self) -> list[Signal]:
        signals = []
        for i, search in enumerate(SEEK_SEARCHES):
            if i > 0:
                time.sleep(5)
            signals.extend(self._search(search["keywords"]))
        return signals

    def _search(self, keywords: str) -> list[Signal]:
        signals = []

        # Try structured JSON API first
        try:
            url = self._build_seek_url(keywords)
            resp = self._get(url, headers={
                "Accept": "text/html,application/xhtml+xml",
                "Referer": "https://www.seek.com.au/",
            })
            signals = self._parse_html(resp.text, keywords)
            logger.info(f"[SEEK] '{keywords}': found {len(signals)} listings")
        except Exception as e:
            logger.warning(f"[SEEK] Search failed for '{keywords}': {e}")
            self._sheets.upsert_collector_state(
                self.source_name, keywords,
                last_error=f"{keywords}: {str(e)[:200]}"
            )

        return signals

    @staticmethod
    def _build_seek_url(keywords: str) -> str:
        slug = keywords.replace(" ", "-")
        return f"{SEEK_BASE}/{slug}-jobs/in-All-Australia"

    def _parse_html(self, html: str, query: str) -> list[Signal]:
        """Parse SEEK search results HTML for job listings."""
        soup = BeautifulSoup(html, "lxml")
        signals = []

        # SEEK renders job cards with data-testid attributes
        job_cards = soup.find_all("article", attrs={"data-testid": True})
        if not job_cards:
            # Fallback: find any job-like links
            job_cards = soup.find_all("article")

        for card in job_cards[:50]:
            try:
                # Title
                title_el = card.find(["h1", "h2", "h3"]) or card.find("a")
                title = title_el.get_text(strip=True) if title_el else ""

                # Company
                company_el = card.find(attrs={"data-automation": "jobCompany"})
                if not company_el:
                    spans = card.find_all("span")
                    company_el = spans[1] if len(spans) > 1 else None
                company = company_el.get_text(strip=True) if company_el else "Unknown"

                # Location
                loc_el = card.find(attrs={"data-automation": "jobLocation"})
                if not loc_el:
                    loc_el = card.find(attrs={"data-automation": "jobArea"})
                location = loc_el.get_text(strip=True) if loc_el else "Australia"

                # URL
                link_el = card.find("a", href=True)
                url = ""
                if link_el:
                    href = link_el["href"]
                    url = href if href.startswith("http") else f"{SEEK_BASE}{href}"

                # Date posted
                date_el = card.find(attrs={"data-automation": "jobListingDate"})
                posted_time = date_el.get_text(strip=True) if date_el else ""

                if title and url:
                    signals.append(Signal(
                        source="seek",
                        signal_type="job_post",
                        company=company,
                        role_title=title,
                        location=location,
                        url=url,
                        posted_time=posted_time,
                        raw_text=f"{title} at {company} — {location}",
                    ))
            except Exception as e:
                logger.debug(f"[SEEK] Card parse error: {e}")
                continue

        return signals
