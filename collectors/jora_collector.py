"""
collectors/jora_collector.py — Jora AU job board collector.
Uses structured HTML parsing.
"""
from __future__ import annotations

import logging
import time
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from collectors.base import CollectorBase
from models import Signal

logger = logging.getLogger(__name__)

JORA_BASE = "https://au.jora.com"

JORA_SEARCHES = [
    "product manager",
    "head of product",
    "product lead",
]


class JoraCollector(CollectorBase):
    source_name = "jora"

    def collect(self) -> list[Signal]:
        signals = []
        for i, query in enumerate(JORA_SEARCHES):
            if i > 0:
                time.sleep(5)
            signals.extend(self._search(query))
        return signals

    def _search(self, query: str) -> list[Signal]:
        encoded_q = quote_plus(query)
        url = f"{JORA_BASE}/jobs?q={encoded_q}&l=Australia&sort=date"
        signals = []

        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            # Jora uses article or div tags for job cards
            cards = soup.find_all(
                ["article", "div"],
                class_=lambda c: c and any(
                    kw in str(c).lower()
                    for kw in ["job-card", "result", "listing", "job_listing"]
                )
            )

            if not cards:
                # Broader fallback
                cards = soup.find_all("article")

            for card in cards[:30]:
                try:
                    title_el = card.find(["h1", "h2", "h3"]) or card.find("a")
                    title = title_el.get_text(strip=True) if title_el else ""

                    company_el = card.find(class_=lambda c: c and "company" in str(c).lower())
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    loc_el = card.find(class_=lambda c: c and "location" in str(c).lower())
                    location = loc_el.get_text(strip=True) if loc_el else "Australia"

                    link_el = card.find("a", href=True)
                    href = link_el["href"] if link_el else ""
                    full_url = href if href.startswith("http") else f"{JORA_BASE}{href}"

                    if title:
                        signals.append(Signal(
                            source="jora",
                            signal_type="job_post",
                            company=company,
                            role_title=title,
                            location=location,
                            url=full_url or url,
                            raw_text=f"{title} at {company} — {location}",
                        ))
                except Exception as e:
                    logger.debug(f"[Jora] Card parse error: {e}")

            logger.info(f"[Jora] '{query}': {len(signals)} listings")

        except Exception as e:
            logger.warning(f"[Jora] Search failed for '{query}': {e}")
            self._sheets.upsert_collector_state(
                self.source_name, query, last_error=str(e)[:200]
            )

        return signals
