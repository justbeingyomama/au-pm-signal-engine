"""
alerter.py — Send Slack alerts for high-priority signals.
No-op when SLACK_WEBHOOK_URL is not configured.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class Alerter:
    def __init__(self, slack_webhook_url: Optional[str] = None):
        self._slack_url = slack_webhook_url or os.getenv("SLACK_WEBHOOK_URL", "").strip()
        self._enabled = bool(self._slack_url)
        if not self._enabled:
            logger.info("Alerter: no Slack webhook configured — alerts disabled.")

    def send_signal_alert(self, signal) -> bool:
        """
        Send a Slack alert for a high-priority signal.
        Returns True if sent successfully, False otherwise.
        """
        if not self._enabled:
            return False

        score_bar = "🟢" if signal.score >= 8 else "🟡"
        text = (
            f"{score_bar} *New PM Signal* — Score {signal.score}/10\n"
            f"*Company:* {signal.company}\n"
            f"*Role:* {signal.role_title}\n"
            f"*Location:* {signal.location}\n"
            f"*Source:* {signal.source.upper()}\n"
            f"*Posted:* {signal.posted_time or 'Unknown'}\n"
            f"<{signal.url}|View Listing>"
        )

        payload = {
            "text": text,
            "unfurl_links": False,
            "unfurl_media": False,
        }

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    self._slack_url,
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
            if resp.status_code == 200:
                logger.info(f"Slack alert sent for {signal.company} — {signal.role_title}")
                return True
            else:
                logger.warning(f"Slack alert failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Slack alert exception: {e}")
            return False
