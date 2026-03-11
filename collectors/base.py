"""
collectors/base.py — Abstract base class for all collectors.
Provides shared HTTP client, retry logic, and state tracking.
"""
from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from curl_cffi import requests as c_requests
from curl_cffi.requests.exceptions import RequestException
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from models import Signal
from sheets.client import SheetsClient

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


class CollectorBase(ABC):
    """
    Abstract base for all signal collectors.
    Subclasses implement `collect()` to return a list of Signal objects.
    """

    # Subclasses set this
    source_name: str = "unknown"

    def __init__(self, sheets: SheetsClient):
        self._sheets = sheets
        self._http = c_requests.Session(
            impersonate="chrome120",
            timeout=REQUEST_TIMEOUT,
        )

    def __del__(self):
        try:
            self._http.close()
        except Exception:
            pass

    @abstractmethod
    def collect(self) -> list[Signal]:
        """Run collection logic and return a list of Signal objects."""
        ...

    def run(self) -> list[Signal]:
        """Run collect(), update collector state, handle errors."""
        now = datetime.now(timezone.utc).isoformat()
        key = self.source_name

        try:
            self._sheets.upsert_collector_state(
                self.source_name, key, last_run_time=now
            )
        except Exception:
            pass  # Don't let sheet errors stop collection

        try:
            signals = self.collect()
            try:
                self._sheets.upsert_collector_state(
                    self.source_name, key,
                    last_success_time=now,
                    last_error="",
                )
            except Exception:
                pass
            return signals
        except Exception as e:
            logger.error(f"[{self.source_name}] Collection failed: {e}")
            try:
                self._sheets.upsert_collector_state(
                    self.source_name, key, last_error=str(e)[:300]
                )
            except Exception:
                pass
            return []

    @retry(
        retry=retry_if_exception_type(RequestException),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(MAX_RETRIES),
        reraise=True,
    )
    def _get(self, url: str, **kwargs) -> c_requests.Response:
        """GET with automatic retry and exponential backoff."""
        resp = self._http.get(url, **kwargs)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 30))
            logger.warning(f"Rate limited by {url} — sleeping {retry_after}s")
            time.sleep(retry_after)
            resp.raise_for_status()
        resp.raise_for_status()
        return resp

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
