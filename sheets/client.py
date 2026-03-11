"""
sheets/client.py — Google Sheets API wrapper using gspread
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

TAB_COMPANY_WATCHLIST = "company_watchlist"
TAB_HIRING_SIGNALS = "hiring_signals"
TAB_COLLECTOR_STATE = "collector_state"

SIGNALS_HEADERS = [
    "signal_id", "dedupe_hash", "source", "signal_type", "company",
    "role_title", "location", "url", "posted_time", "discovered_time",
    "score", "is_high_priority", "remote_likelihood", "raw_text", "notes", "status",
]

WATCHLIST_HEADERS = [
    "company_name", "careers_url", "ats_provider",
    "hq_location", "industry", "priority_level",
]

STATE_HEADERS = [
    "source", "key", "last_run_time", "last_success_time",
    "last_cursor", "last_error",
]


class SheetsClient:
    def __init__(self, credentials_json: str, spreadsheet_id: str):
        creds_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet_id = spreadsheet_id
        self._sh = self._gc.open_by_key(spreadsheet_id)

    def _get_or_create_tab(self, title: str, headers: list[str]) -> gspread.Worksheet:
        """Return an existing worksheet or create it with headers."""
        try:
            ws = self._sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = self._sh.add_worksheet(title=title, rows=1000, cols=len(headers))
            ws.append_row(headers, value_input_option="RAW")
            logger.info(f"Created tab: {title}")
        return ws

    def get_tab(self, name: str) -> gspread.Worksheet:
        return self._sh.worksheet(name)

    def ensure_tabs(self):
        """Create all required tabs if missing."""
        self._get_or_create_tab(TAB_COMPANY_WATCHLIST, WATCHLIST_HEADERS)
        self._get_or_create_tab(TAB_HIRING_SIGNALS, SIGNALS_HEADERS)
        self._get_or_create_tab(TAB_COLLECTOR_STATE, STATE_HEADERS)
        logger.info("All tabs verified.")

    # ---- company_watchlist ------------------------------------------------

    def get_watchlist(self) -> list[dict]:
        ws = self.get_tab(TAB_COMPANY_WATCHLIST)
        return ws.get_all_records()

    def seed_watchlist(self, rows: list[list]):
        ws = self.get_tab(TAB_COMPANY_WATCHLIST)
        existing = ws.get_all_values()
        if len(existing) <= 1:  # Only header row or empty
            ws.append_rows(rows, value_input_option="RAW")
            logger.info(f"Seeded {len(rows)} companies into watchlist.")
        else:
            logger.info("Watchlist already has data, skipping seed.")

    # ---- hiring_signals ---------------------------------------------------

    def get_all_signal_rows(self) -> list[list]:
        ws = self.get_tab(TAB_HIRING_SIGNALS)
        rows = ws.get_all_values()
        return rows[1:] if rows else []  # skip header

    def append_signal(self, row: list):
        ws = self.get_tab(TAB_HIRING_SIGNALS)
        ws.append_row(row, value_input_option="RAW")

    def update_signal_status(self, signal_id: str, status: str):
        """Update the status column for a given signal_id."""
        ws = self.get_tab(TAB_HIRING_SIGNALS)
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):  # 1-indexed, skip header
            if row and row[0] == signal_id:
                status_col = SIGNALS_HEADERS.index("status") + 1
                ws.update_cell(i, status_col, status)
                return

    def get_signals_today(self) -> list[list]:
        """Return signal rows discovered today (UTC)."""
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = self.get_all_signal_rows()
        disc_idx = SIGNALS_HEADERS.index("discovered_time")
        return [r for r in rows if len(r) > disc_idx and r[disc_idx].startswith(today)]

    # ---- collector_state --------------------------------------------------

    def upsert_collector_state(self, source: str, key: str, **kwargs):
        """Update or insert a collector state row."""
        ws = self.get_tab(TAB_COLLECTOR_STATE)
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) >= 2 and row[0] == source and row[1] == key:
                # Update existing row
                for field, value in kwargs.items():
                    if field in STATE_HEADERS:
                        col = STATE_HEADERS.index(field) + 1
                        ws.update_cell(i, col, str(value))
                return
        # Insert new row
        new_row = [source, key, "", "", "", ""]
        for field, value in kwargs.items():
            if field in STATE_HEADERS:
                idx = STATE_HEADERS.index(field)
                new_row[idx] = str(value)
        ws.append_row(new_row, value_input_option="RAW")

    def get_all_collector_states(self) -> list[dict]:
        ws = self.get_tab(TAB_COLLECTOR_STATE)
        return ws.get_all_records()
