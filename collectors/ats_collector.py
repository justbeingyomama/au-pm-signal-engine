"""
collectors/ats_collector.py — Scrapes company career pages with ATS detection.

Supports: Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Workday, custom HTML.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from collectors.base import CollectorBase
from models import Signal
from sheets.client import SheetsClient

logger = logging.getLogger(__name__)


# ─── ATS Detection ────────────────────────────────────────────────────────────

ATS_PATTERNS = {
    "greenhouse": ["greenhouse.io", "boards.greenhouse.io"],
    "lever": ["lever.co", "jobs.lever.co"],
    "workable": ["workable.com", "apply.workable.com"],
    "ashby": ["ashbyhq.com", "jobs.ashbyhq.com"],
    "smartrecruiters": ["smartrecruiters.com"],
    "workday": ["myworkdayjobs.com", "wd3.myworkday.com"],
}


def detect_ats(careers_url: str, html: str = "") -> str:
    """Auto-detect ATS from URL or HTML content."""
    url_lower = careers_url.lower()
    for ats, domains in ATS_PATTERNS.items():
        if any(d in url_lower for d in domains):
            return ats

    if html:
        html_lower = html[:5000].lower()
        for ats, domains in ATS_PATTERNS.items():
            if any(d in html_lower for d in domains):
                return ats

    return "custom"


# ─── Structured extractors (JSON/API) ─────────────────────────────────────────

def extract_greenhouse(company_name: str, html: str, careers_url: str) -> list[dict]:
    """Parse Greenhouse jobs from embedded JSON or API endpoint."""
    roles = []
    # Try to find board token from URL
    parsed = urlparse(careers_url)
    # Greenhouse API: https://boards-api.greenhouse.io/v1/boards/{token}/jobs
    # Try to extract board token from URL path
    # e.g. boards.greenhouse.io/canva → token = canva
    path_parts = [p for p in parsed.path.split("/") if p]
    token = path_parts[0] if path_parts else None

    if token:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        return [{"_api_url": api_url}]  # Signal caller to use API
    return roles


def extract_lever(company_name: str, html: str, careers_url: str) -> list[dict]:
    """Parse Lever jobs from API endpoint."""
    parsed = urlparse(careers_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    token = path_parts[0] if path_parts else None

    if "lever.co" in careers_url and token:
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        return [{"_api_url": api_url}]
    return []


def extract_workable(company_name: str, html: str, careers_url: str) -> list[dict]:
    """Parse Workable jobs from API."""
    parsed = urlparse(careers_url)
    subdomain = parsed.hostname.split(".")[0] if parsed.hostname else None
    if subdomain and "workable" not in subdomain:
        api_url = f"https://www.workable.com/api/accounts/{subdomain}/jobs?details=true"
        return [{"_api_url": api_url}]
    return []


def extract_ashby(company_name: str, html: str, careers_url: str) -> list[dict]:
    """Parse Ashby jobs via their public API."""
    parsed = urlparse(careers_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    # ashbyhq.com/company → company_name
    if "ashbyhq.com" in careers_url and path_parts:
        org = path_parts[0]
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
        return [{"_api_url": api_url}]
    return []


def extract_html_jobs(html: str, base_url: str, company_name: str) -> list[dict]:
    """Generic fallback: extract job listings from HTML using heuristics."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for tag in soup.find_all(["a", "li", "div", "h2", "h3", "h4"],
                              class_=lambda c: c and any(
                                  kw in str(c).lower()
                                  for kw in ["job", "role", "position", "opening", "career"]
                              )):
        text = tag.get_text(strip=True)
        if not text or len(text) < 5 or len(text) > 200:
            continue

        href = ""
        if tag.name == "a":
            href = tag.get("href", "")
        else:
            a = tag.find("a")
            if a:
                href = a.get("href", "")

        if href and not href.startswith("http"):
            href = urljoin(base_url, href)

        jobs.append({
            "title": text,
            "location": "",
            "url": href or base_url,
        })

    return jobs[:50]  # Cap to avoid noise


# ─── Main Collector ───────────────────────────────────────────────────────────

class ATSCollector(CollectorBase):
    source_name = "ats"

    def collect(self) -> list[Signal]:
        watchlist = self._sheets.get_watchlist()
        signals = []

        for i, company in enumerate(watchlist):
            if i > 0:
                time.sleep(3)  # Stagger requests

            name = company.get("company_name", "").strip()
            url = company.get("careers_url", "").strip()
            known_ats = company.get("ats_provider", "").strip().lower()
            priority = company.get("priority_level", "Med")

            if not name or not url:
                continue

            logger.info(f"[ATS] Scanning: {name} → {url}")
            try:
                resp = self._get(url)
                html = resp.text
                ats = known_ats or detect_ats(url, html)
                company_signals = self._extract_by_ats(ats, name, html, url, priority)
                signals.extend(company_signals)
                logger.info(f"[ATS] {name}: found {len(company_signals)} matching roles")
            except Exception as e:
                logger.warning(f"[ATS] Failed for {name}: {e}")
                self._sheets.upsert_collector_state(
                    self.source_name, url,
                    last_error=f"{name}: {str(e)[:200]}"
                )

        return signals

    def _extract_by_ats(
        self, ats: str, company: str, html: str, careers_url: str, priority: str
    ) -> list[Signal]:
        raw_jobs = []

        if ats == "greenhouse":
            hints = extract_greenhouse(company, html, careers_url)
            if hints and "_api_url" in hints[0]:
                raw_jobs = self._fetch_greenhouse_api(hints[0]["_api_url"])
        elif ats == "lever":
            hints = extract_lever(company, html, careers_url)
            if hints and "_api_url" in hints[0]:
                raw_jobs = self._fetch_lever_api(hints[0]["_api_url"])
        elif ats == "workable":
            hints = extract_workable(company, html, careers_url)
            if hints and "_api_url" in hints[0]:
                raw_jobs = self._fetch_workable_api(hints[0]["_api_url"])
        elif ats == "ashby":
            hints = extract_ashby(company, html, careers_url)
            if hints and "_api_url" in hints[0]:
                raw_jobs = self._fetch_ashby_api(hints[0]["_api_url"])

        if not raw_jobs:
            raw_jobs = extract_html_jobs(html, careers_url, company)

        signals = []
        for job in raw_jobs:
            signals.append(Signal(
                source="ats",
                signal_type="career_page_post",
                company=company,
                role_title=job.get("title", ""),
                location=job.get("location", "Australia"),
                url=job.get("url", careers_url),
                posted_time=job.get("posted_at", ""),
                raw_text=job.get("title", ""),
            ))
        return signals

    def _fetch_greenhouse_api(self, api_url: str) -> list[dict]:
        try:
            resp = self._get(api_url)
            data = resp.json()
            jobs = data.get("jobs", [])
            result = []
            for j in jobs:
                offices = j.get("offices", [])
                location = offices[0].get("name", "") if offices else ""
                result.append({
                    "title": j.get("title", ""),
                    "location": location,
                    "url": j.get("absolute_url", ""),
                    "posted_at": j.get("updated_at", ""),
                })
            return result
        except Exception as e:
            logger.warning(f"Greenhouse API failed: {e}")
            return []

    def _fetch_lever_api(self, api_url: str) -> list[dict]:
        try:
            resp = self._get(api_url)
            jobs = resp.json()
            result = []
            for j in jobs:
                categories = j.get("categories", {})
                result.append({
                    "title": j.get("text", ""),
                    "location": categories.get("location", ""),
                    "url": j.get("hostedUrl", ""),
                    "posted_at": "",
                })
            return result
        except Exception as e:
            logger.warning(f"Lever API failed: {e}")
            return []

    def _fetch_workable_api(self, api_url: str) -> list[dict]:
        try:
            resp = self._get(api_url)
            data = resp.json()
            jobs = data.get("results", [])
            result = []
            for j in jobs:
                result.append({
                    "title": j.get("title", ""),
                    "location": j.get("location", {}).get("city", ""),
                    "url": j.get("url", ""),
                    "posted_at": j.get("published_on", ""),
                })
            return result
        except Exception as e:
            logger.warning(f"Workable API failed: {e}")
            return []

    def _fetch_ashby_api(self, api_url: str) -> list[dict]:
        try:
            resp = self._get(api_url)
            data = resp.json()
            jobs = data.get("jobPostings", [])
            result = []
            for j in jobs:
                result.append({
                    "title": j.get("title", ""),
                    "location": j.get("locationName", ""),
                    "url": j.get("jobPostingLink", ""),
                    "posted_at": j.get("publishedDate", ""),
                })
            return result
        except Exception as e:
            logger.warning(f"Ashby API failed: {e}")
            return []
