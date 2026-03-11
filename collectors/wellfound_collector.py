"""
collectors/wellfound_collector.py — Wellfound (AngelList Talent) collector.

Wellfound uses Cloudflare protection and blocks most automated requests with 403.
This collector fails gracefully: logs the block to collector_state and skips,
rather than retrying and generating noise.

If you have a Wellfound account, you can export job alerts via email and feed
them in separately. For now, this collector is a no-op when blocked.
"""
from __future__ import annotations

import logging

from collectors.base import CollectorBase
from models import Signal

logger = logging.getLogger(__name__)

WELLFOUND_BASE = "https://wellfound.com"

WELLFOUND_SEARCHES = [
    ("product-manager", "australia"),
    ("product-manager", "remote"),
    ("head-of-product", "australia"),
]


class WellfoundCollector(CollectorBase):
    source_name = "wellfound"

    def collect(self) -> list[Signal]:
        signals = []

        for role, location in WELLFOUND_SEARCHES:
            url = f"{WELLFOUND_BASE}/jobs?role={role}&location={location}"
            try:
                resp = self._get(url, headers={
                    "Accept": "text/html",
                    "Referer": WELLFOUND_BASE,
                    "Accept-Language": "en-AU,en;q=0.9",
                })

                from bs4 import BeautifulSoup
                import json
                soup = BeautifulSoup(resp.text, "lxml")

                # Try Next.js embedded data first
                next_data = soup.find("script", id="__NEXT_DATA__")
                if next_data:
                    try:
                        data = json.loads(next_data.string or "{}")
                        signals.extend(self._parse_next_data(data, url))
                        continue
                    except Exception:
                        pass

                # HTML fallback
                signals.extend(self._parse_html(soup, url))

            except Exception as e:
                err = str(e)
                if "403" in err:
                    msg = (
                        f"Wellfound blocked with 403 for {role}/{location}. "
                        "Cloudflare protection active. Skipping — no retry."
                    )
                    logger.warning(f"[Wellfound] {msg}")
                    try:
                        self._sheets.upsert_collector_state(
                            self.source_name,
                            f"{role}/{location}",
                            last_error=msg[:300],
                        )
                    except Exception:
                        pass
                else:
                    logger.warning(f"[Wellfound] {role}/{location} failed: {e}")

        return signals

    def _parse_next_data(self, data: dict, source_url: str) -> list[Signal]:
        signals = []
        try:
            props = data.get("props", {}).get("pageProps", {})
            jobs = (
                props.get("jobs")
                or props.get("jobListings")
                or props.get("data", {}).get("jobListings")
                or []
            )
            for job in jobs[:30]:
                title = job.get("title") or job.get("role", "")
                startup = job.get("startup", {})
                company = startup.get("name", "Unknown") if isinstance(startup, dict) else "Unknown"
                location_names = job.get("locationNames", [])
                location = location_names[0] if location_names else "Australia"
                slug = job.get("slug") or job.get("id", "")
                url = f"{WELLFOUND_BASE}/jobs/{slug}" if slug else source_url
                if title:
                    signals.append(Signal(
                        source="wellfound",
                        signal_type="job_post",
                        company=company,
                        role_title=title,
                        location=location,
                        url=url,
                        raw_text=f"{title} at {company} -- {location}",
                    ))
        except Exception as e:
            logger.debug(f"[Wellfound] JSON parse error: {e}")
        return signals

    def _parse_html(self, soup, source_url: str) -> list[Signal]:
        signals = []
        cards = soup.find_all(
            ["div", "li"],
            class_=lambda c: c and any(
                kw in str(c).lower() for kw in ["job-listing", "job_listing", "listing", "role"]
            )
        )
        for card in cards[:30]:
            try:
                title_el = card.find(["h2", "h3", "a"])
                title = title_el.get_text(strip=True) if title_el else ""
                company_el = card.find(class_=lambda c: c and "company" in str(c).lower())
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                loc_el = card.find(class_=lambda c: c and "location" in str(c).lower())
                location = loc_el.get_text(strip=True) if loc_el else "Australia"
                link_el = card.find("a", href=True)
                href = link_el["href"] if link_el else ""
                url = href if href.startswith("http") else f"{WELLFOUND_BASE}{href}"
                if title:
                    signals.append(Signal(
                        source="wellfound",
                        signal_type="job_post",
                        company=company,
                        role_title=title,
                        location=location,
                        url=url or source_url,
                        raw_text=f"{title} at {company} -- {location}",
                    ))
            except Exception:
                continue
        return signals
