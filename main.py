"""
main.py — Entry point for AU PM Hiring Signal Engine.

Usage:
    python main.py             # Run once then enter scheduled loop
    python main.py --once      # Run all collectors once and exit
    python main.py --setup     # Set up Google Sheets tabs and seed data, then exit
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("signal_engine.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="AU PM Hiring Signal Engine")
    parser.add_argument(
        "--once", action="store_true",
        help="Run all collectors once and exit (no scheduler)"
    )
    parser.add_argument(
        "--setup", action="store_true",
        help="Set up Google Sheets tabs and seed data, then exit"
    )
    args = parser.parse_args()

    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "")

    if not spreadsheet_id:
        logger.error("SPREADSHEET_ID is not set.")
        sys.exit(1)

    if not os.path.isfile(credentials_path):
        logger.error(
            f"Google credentials file not found: {credentials_path}\n"
            "Please provide the service account JSON file."
        )
        sys.exit(1)

    with open(credentials_path, "r", encoding="utf-8") as f:
        credentials_info = json.load(f)

    from sheets.client import SheetsClient
    from alerter import Alerter

    logger.info("Connecting to Google Sheets...")
    sheets = SheetsClient(credentials_info, spreadsheet_id)

    if args.setup:
        from sheets.setup import setup
        setup(credentials_info, spreadsheet_id)
        return

    sheets.ensure_tabs()

    alerter = Alerter()
    slack_status = "enabled" if alerter._enabled else "disabled (set SLACK_WEBHOOK_URL to enable)"
    logger.info(f"Slack alerts: {slack_status}")

    if args.once:
        logger.info("Running all collectors (single pass)...")
        from scheduler import Scheduler
        sched = Scheduler(sheets, alerter)
        sched.run_all_once()
        logger.info("Single pass complete. Check hiring_signals tab in Google Sheets.")
        return

    from scheduler import Scheduler
    sched = Scheduler(sheets, alerter)

    logger.info("Running initial pass of all collectors...")
    sched.run_all_once()

    sched.setup()
    sched.start()

    logger.info("=" * 60)
    logger.info("AU PM Signal Engine is running.")
    logger.info(f"Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    logger.info("Press Ctrl+C to stop.")
    logger.info("=" * 60)

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        sched.stop()
        logger.info("Signal engine stopped.")


if __name__ == "__main__":
    main()
