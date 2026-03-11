"""
sheets/setup.py — Creates/verifies all 3 sheet tabs and seeds company_watchlist.
Run once before first use: python -m sheets.setup
"""
from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 30 Seed AU companies — replace with your own targets
SEED_COMPANIES = [
    ["Canva", "https://www.canva.com/careers/", "", "Sydney", "Design SaaS", "High"],
    ["Atlassian", "https://www.atlassian.com/company/careers/all-jobs", "Lever", "Sydney", "Dev Tools", "High"],
    ["Afterpay", "https://careers.afterpay.com/", "", "Melbourne", "Fintech", "High"],
    ["SafetyCulture", "https://safetyculturecareers.com/", "Greenhouse", "Sydney", "Safety SaaS", "High"],
    ["Xero", "https://www.xero.com/au/about/careers/", "Workday", "Melbourne", "Accounting SaaS", "High"],
    ["REA Group", "https://careers.rea-group.com/", "", "Melbourne", "Prop Tech", "High"],
    ["Seek", "https://www.seek.com.au/work-for-seek/", "", "Melbourne", "HR Tech", "High"],
    ["Airwallex", "https://www.airwallex.com/au/careers/", "Greenhouse", "Melbourne", "Fintech", "High"],
    ["Rokt", "https://rokt.com/careers/", "Greenhouse", "Sydney", "Ad Tech", "Med"],
    ["Culture Amp", "https://www.cultureamp.com/about/careers/", "Greenhouse", "Melbourne", "HR Tech", "High"],
    ["Buildkite", "https://buildkite.com/careers/", "", "Melbourne", "Dev Tools", "Med"],
    ["Employment Hero", "https://employmenthero.com/careers/", "Lever", "Sydney", "HR SaaS", "High"],
    ["Deputy", "https://www.deputy.com/au/careers/", "Greenhouse", "Sydney", "Workforce SaaS", "High"],
    ["Immutable", "https://www.immutable.com/careers/", "Greenhouse", "Sydney", "Web3", "Med"],
    ["Linktree", "https://linktr.ee/careers/", "Ashby", "Melbourne", "Creator Tech", "High"],
    ["Brighte", "https://brighte.com.au/careers/", "", "Sydney", "Fintech", "Med"],
    ["Cover Genius", "https://covergenius.com/careers/", "Greenhouse", "Sydney", "Insurtech", "Med"],
    ["Prospa", "https://www.prospa.com/careers/", "", "Sydney", "SME Finance", "Med"],
    ["Lendi Group", "https://careers.lendigroup.com.au/", "", "Sydney", "Mortgage Tech", "Med"],
    ["Siteminder", "https://www.siteminder.com/careers/", "Greenhouse", "Sydney", "Hospitality SaaS", "Med"],
    ["Compono", "https://compono.com/careers/", "", "Brisbane", "HR AI", "Low"],
    ["Rezdy", "https://www.rezdy.com/about/careers/", "", "Sydney", "Tourism SaaS", "Low"],
    ["HotDoc", "https://www.hotdoc.com.au/careers/", "Lever", "Melbourne", "HealthTech", "Med"],
    ["Eucalyptus", "https://eucalyptus.vc/careers/", "Greenhouse", "Sydney", "Digital Health", "High"],
    ["Hatch", "https://www.hatch.team/about/careers", "", "Melbourne", "Career Tech", "Med"],
    ["Octopus Deploy", "https://octopus.com/company/careers/", "Workable", "Brisbane", "Dev Tools", "Med"],
    ["Shippit", "https://www.shippit.com/careers/", "Lever", "Sydney", "Logistics SaaS", "Med"],
    ["Wiise", "https://wiise.com/careers/", "", "Sydney", "ERP SaaS", "Low"],
    ["Zeller", "https://myzeller.com/careers/", "Ashby", "Melbourne", "Fintech", "High"],
    ["Airtasker", "https://www.airtasker.com/careers/", "Greenhouse", "Sydney", "Marketplace", "Med"],
]


def setup(credentials_path: str, spreadsheet_id: str):
    from sheets.client import SheetsClient
    client = SheetsClient(credentials_path, spreadsheet_id)

    print("🔧 Verifying / creating tabs...")
    client.ensure_tabs()

    print("🌱 Seeding company_watchlist...")
    client.seed_watchlist(SEED_COMPANIES)

    print("✅ Setup complete! Sheet is ready.")
    print(f"   ↳ https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")


if __name__ == "__main__":
    creds = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    sheet_id = os.getenv("SPREADSHEET_ID", "")
    if not sheet_id:
        print("ERROR: SPREADSHEET_ID not set in .env")
        sys.exit(1)
    setup(creds, sheet_id)
