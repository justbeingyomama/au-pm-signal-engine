from __future__ import annotations

import logging
from bs4 import BeautifulSoup
from models import Signal
from sheets.client import SheetsClient
from collectors.base import CollectorBase

logger = logging.getLogger(__name__)

class RecruiterCollector(CollectorBase):
    """
    Scrapes highly-focused PM recruitment agencies in Australia.
    Currently supports: Brightbox Consulting, Parity Consulting, S2M
    """
    source_name = "recruiters"

    def __init__(self, sheets: SheetsClient):
        super().__init__(sheets)
        
    def collect(self) -> list[Signal]:
        signals = []
        signals.extend(self._scrape_brightbox())
        signals.extend(self._scrape_parity())
        signals.extend(self._scrape_s2m())
        return signals

    def _scrape_brightbox(self) -> list[Signal]:
        signals = []
        seen_urls = set()
        url = "https://brightboxconsulting.com.au/jobs/"
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # The exact HTML structure depends on their job board plugin (looks like JobAdder/Bullhorn)
            # As a broad fallback, we look at article or div tags containing 'job' classes
            jobs = soup.find_all(['li', 'div', 'article'], class_=lambda c: c and ('job' in c.lower() or 'listing' in c.lower()))
            
            for job in jobs[:20]:
                title_el = job.find(['h2', 'h3', 'a'])
                if not title_el: continue
                
                title = title_el.get_text(strip=True).lower()
                if 'product' not in title: continue
                # False positives: project manager, senior manager
                if 'project' in title or title == 'senior manager': continue

                link = job.find("a", href=True)
                if not link: continue
                job_url = link['href']
                if not job_url.startswith("http"):
                    job_url = f"https://brightboxconsulting.com.au{job_url}"
                
                # Prevent duplicates
                if job_url in seen_urls: continue
                seen_urls.add(job_url)

                signals.append(Signal(
                    source="brightbox_consulting",
                    signal_type="job_post",
                    company="Brightbox Consulting (Agency)",
                    role_title=title_el.get_text(strip=True),
                    location="Australia",
                    url=job_url,
                    raw_text=title_el.get_text(strip=True)
                ))
        except Exception as e:
            logger.error(f"[Recruiters] Failed to scrape Brightbox: {e}")
        return signals

    def _scrape_parity(self) -> list[Signal]:
        signals = []
        seen_urls = set()
        # Parity covers PM roles across East Coast
        url = "https://parityconsulting.com.au/jobs/?category=Product"
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            jobs = soup.find_all(['div', 'li'], class_=lambda c: c and 'job' in c.lower())
            for job in jobs[:20]:
                title_el = job.find(['h2', 'h3', 'a'])
                if not title_el: continue
                
                title = title_el.get_text(strip=True)
                title_lower = title.lower()
                if 'product' not in title_lower: continue
                if 'project' in title_lower: continue

                link = job.find("a", href=True)
                if not link: continue
                job_url = link['href']
                if not job_url.startswith("http"):
                    job_url = f"https://parityconsulting.com.au{job_url}"
                
                if job_url in seen_urls: continue
                seen_urls.add(job_url)

                signals.append(Signal(
                    source="parity_consulting",
                    signal_type="job_post",
                    company="Parity Consulting (Agency)",
                    role_title=title,
                    location="Australia",
                    url=job_url,
                    raw_text=title
                ))
        except Exception as e:
            logger.error(f"[Recruiters] Failed to scrape Parity: {e}")
        return signals

    def _scrape_s2m(self) -> list[Signal]:
        import httpx
        signals = []
        seen_urls = set()
        url = "https://s2m.com.au/jobs/?category=Product"
        try:
            # S2M's SSL/DNS has issues with curl_cffi, fallback to httpx
            resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(resp.text, 'lxml')
            
            jobs = soup.find_all(['div', 'li'], class_=lambda c: c and 'job' in c.lower())
            for job in jobs[:20]:
                title_el = job.find(['h2', 'h3', 'a'])
                if not title_el: continue
                
                title = title_el.get_text(strip=True)
                title_lower = title.lower()
                if 'product' not in title_lower: continue
                if 'project' in title_lower: continue

                link = job.find("a", href=True)
                if not link: continue
                job_url = link['href']
                if not job_url.startswith("http"):
                    job_url = f"https://s2m.com.au{job_url}"
                    
                if job_url in seen_urls: continue
                seen_urls.add(job_url)

                signals.append(Signal(
                    source="s2m",
                    signal_type="job_post",
                    company="S2M (Agency)",
                    role_title=title,
                    location="Australia",
                    url=job_url,
                    raw_text=title
                ))
        except Exception as e:
            logger.error(f"[Recruiters] Failed to scrape S2M: {e}")
        return signals
