"""
collectors/indeed_collector.py — Indeed AU job board collector.

Indeed's RSS feeds were discontinued. This uses structured HTML scraping only.
"""
from __future__ import annotations

import logging
import os
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as c_requests

from collectors.base import CollectorBase
from models import Signal

logger = logging.getLogger(__name__)

INDEED_SEARCHES = [
    "product manager",
    "senior product manager",
    "head of product",
    "product lead",
    "group product manager",
]

INDEED_BASE = "https://au.indeed.com"


class IndeedCollector(CollectorBase):
    source_name = "indeed"

    def collect(self) -> list[Signal]:
        signals = []
        for i, query in enumerate(INDEED_SEARCHES):
            if i > 0:
                time.sleep(5)
            signals.extend(self._search_html(query))
        return signals

    def _search_html(self, query: str) -> list[Signal]:
        """Scrape Indeed AU search results via curl_cffi and fetch full jobs via ZenRows."""
        signals = []
        encoded_q = quote_plus(query)
        url = f"{INDEED_BASE}/jobs?q={encoded_q}&l=Australia&sort=date"
        # 1. Fetch search results to get job links
        try:
            logger.info(f"[Indeed] Fetching search page: {url}")
            resp = c_requests.get(url, impersonate="chrome120", timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            # Indeed job cards
            cards = soup.find_all("div", class_=lambda c: c and "job_seen_beacon" in str(c))
            if not cards:
                cards = soup.find_all("div", attrs={"data-testid": "slider_item"})

            # Limit to top 15 results per query to avoid burning too much time/getting rate limited
            for card in cards[:15]:
                try:
                    title_el = card.find("h2") or card.find("a", attrs={"data-jk": True})
                    title = title_el.get_text(strip=True) if title_el else ""

                    company_el = (
                        card.find(attrs={"data-testid": "company-name"})
                        or card.find("span", class_=lambda c: c and "company" in str(c).lower())
                    )
                    company = company_el.get_text(strip=True) if company_el else "Unknown"

                    loc_el = card.find(attrs={"data-testid": "text-location"})
                    location = loc_el.get_text(strip=True) if loc_el else "Australia"

                    # Job key from link attribute -> build canonical URL
                    link_el = card.find("a", attrs={"data-jk": True})
                    jk = link_el["data-jk"] if link_el else ""
                    if not jk:
                        link_el = card.find("a", href=lambda h: h and "/rc/clk" in str(h))
                        href = link_el["href"] if link_el else ""
                        job_url = f"{INDEED_BASE}{href}" if href else ""
                    else:
                        job_url = f"{INDEED_BASE}/viewjob?jk={jk}"

                    if title and jk:
                        # Removed secondary API call to fetch full job description by request
                        raw_text = f"{title} at {company} — {location}"

                        signals.append(Signal(
                            source="indeed",
                            signal_type="job_post",
                            company=company,
                            role_title=title,
                            location=location,
                            url=job_url,
                            raw_text=raw_text,
                        ))
                except Exception:
                    continue

            if not signals:
                logger.warning(
                    f"[Indeed] '{query}': 0 results -- Indeed may be blocking. "
                    "Try again later or reduce cadence."
                )
            else:
                logger.info(f"[Indeed] '{query}': {len(signals)} listings successfully fetched")

        except Exception as e:
            logger.warning(f"[Indeed] Search failed for '{query}': {e}")
            try:
                self._sheets.upsert_collector_state(
                    self.source_name, query, last_error=str(e)[:200]
                )
            except Exception:
                pass

        return signals
