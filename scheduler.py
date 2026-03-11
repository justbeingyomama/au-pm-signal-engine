"""
scheduler.py — APScheduler-based job scheduler for all collectors.
Runs ATS + Reddit every 30 min, job boards every 60 min.
"""
from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from alerter import Alerter
from collectors.ats_collector import ATSCollector
from collectors.indeed_collector import IndeedCollector
from collectors.jora_collector import JoraCollector
from collectors.reddit_collector import RedditCollector
from collectors.seek_collector import SeekCollector
from collectors.wellfound_collector import WellfoundCollector
from collectors.recruiter_collector import RecruiterCollector
from pipeline import Pipeline
from sheets.client import SheetsClient

logger = logging.getLogger(__name__)

ATS_INTERVAL = int(os.getenv("ATS_INTERVAL_SECONDS", "1800"))      # 30 min
BOARD_INTERVAL = int(os.getenv("BOARD_INTERVAL_SECONDS", "3600"))  # 60 min
REDDIT_INTERVAL = int(os.getenv("REDDIT_INTERVAL_SECONDS", "1800"))  # 30 min


def make_job(collector_cls, sheets: SheetsClient, pipeline: Pipeline):
    """Return a callable that runs the collector + pipeline."""
    def job():
        collector_name = collector_cls.__name__
        try:
            logger.info(f"▶ Starting {collector_name}...")
            collector = collector_cls(sheets)
            signals = collector.run()
            written = pipeline.process(signals)
            logger.info(f"✅ {collector_name}: {len(signals)} signals → {written} new written")
        except Exception as e:
            logger.error(f"❌ {collector_name} job error: {e}")
    return job


class Scheduler:
    def __init__(self, sheets: SheetsClient, alerter: Alerter):
        self._sheets = sheets
        self._pipeline = Pipeline(sheets, alerter)
        self._scheduler = BackgroundScheduler(timezone="UTC")

    def setup(self):
        s = self._scheduler
        sh = self._sheets
        p = self._pipeline

        # ATS collector — every 30 min
        s.add_job(
            make_job(ATSCollector, sh, p),
            trigger=IntervalTrigger(seconds=ATS_INTERVAL),
            id="ats_collector",
            name="ATS / Careers Page Collector",
            next_run_time=None,  # Don't run immediately on start; main.py runs first pass
        )

        # Reddit — every 30 min
        s.add_job(
            make_job(RedditCollector, sh, p),
            trigger=IntervalTrigger(seconds=REDDIT_INTERVAL),
            id="reddit_collector",
            name="Reddit Collector",
            next_run_time=None,
        )

        # Job boards — every 60 min
        for cls in [SeekCollector, IndeedCollector, JoraCollector, WellfoundCollector, RecruiterCollector]:
            s.add_job(
                make_job(cls, sh, p),
                trigger=IntervalTrigger(seconds=BOARD_INTERVAL),
                id=f"{cls.source_name}_collector",
                name=f"{cls.__name__}",
                next_run_time=None,
            )

        logger.info("Scheduler configured.")

    def run_all_once(self):
        """Run every collector once synchronously — useful for first pass or --dry-run checks."""
        sh = self._sheets
        p = self._pipeline
        all_collectors = [
            ATSCollector,
            RedditCollector,
            SeekCollector,
            IndeedCollector,
            JoraCollector,
            WellfoundCollector,
            RecruiterCollector,
        ]
        for cls in all_collectors:
            make_job(cls, sh, p)()

    def start(self):
        self._scheduler.start()
        logger.info("Scheduler started. Press Ctrl+C to stop.")

    def stop(self):
        self._scheduler.shutdown()
        logger.info("Scheduler stopped.")
