# AU Product Manager Hiring Signal Engine

An automated Python system that continuously monitors Australian job markets for Product Manager roles, writes deduplicated scored signals to Google Sheets, and sends Slack alerts.

## What it does

- **6 Collectors**: ATS/careers pages (Greenhouse, Lever, Workable, Ashby, custom HTML), SEEK, Indeed AU, Jora, Wellfound, Reddit
- **Processing Pipeline**: normalize → dedupe (MD5 hash) → score (0–10) → write to Google Sheets → alert
- **Scheduler**: ATS + Reddit every 30 min, job boards every 60 min
- **Dashboard**: `python dashboard.py` for live status in terminal

---

## Quick Start

### 1. Set up Google Cloud credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. IAM & Admin → Service Accounts → Create Service Account
4. Keys tab → Add Key → Create new key → JSON → download as `credentials.json`
5. Copy `credentials.json` into this project folder
6. Open [your Google Sheet](https://docs.google.com/spreadsheets/d/1hgNnMlTLtQF_3fiGkQilC5QntVbalpSEIOP5r5deiis/edit)
7. Click **Share** → paste your service account email (shown in credentials.json as `client_email`) → give **Editor** access

### 2. Install dependencies

```bash
cd /path/to/au-pm-signal-engine
pip install -r requirements.txt
```

> Python 3.10+ recommended.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set SPREADSHEET_ID (already pre-filled), SLACK_WEBHOOK_URL (optional)
```

### 4. Set up Google Sheets

```bash
python -m sheets.setup
```

This creates the 3 tabs (`company_watchlist`, `hiring_signals`, `collector_state`) and seeds 30 AU companies.

### 5. Run

```bash
# Run all collectors once and exit
python main.py --once

# Run continuously (first pass + every 30/60 min)
python main.py

# Show dashboard
python dashboard.py
```

---

## Project Structure

```
au-pm-signal-engine/
├── main.py                   # Entry point
├── scheduler.py              # APScheduler jobs
├── pipeline.py               # Normalize → dedupe → score → write → alert
├── scoring.py                # 0–10 score rules
├── deduper.py                # MD5 dedupe hash
├── alerter.py                # Slack webhook sender
├── dashboard.py              # Rich CLI dashboard
├── models.py                 # Signal, CollectorState dataclasses
├── sheets/
│   ├── client.py             # gspread wrapper
│   └── setup.py              # Tab creation + seed data
└── collectors/
    ├── base.py               # Abstract base + retry/backoff
    ├── ats_collector.py      # ATS / careers pages
    ├── seek_collector.py     # SEEK AU
    ├── indeed_collector.py   # Indeed AU (RSS + HTML)
    ├── jora_collector.py     # Jora AU
    ├── wellfound_collector.py# Wellfound
    └── reddit_collector.py   # Reddit RSS
```

---

## Scoring Rules

| Rule | Points |
|---|---|
| Direct job post (job board) | +5 |
| ATS career listing | +4 |
| Reddit forum post | +3 |
| Location matches AU city/region | +2 |
| Posted within last 24h | +2 |
| **Maximum** | **10** |

**High priority** = score ≥ 6

---

## Role Filters

**Include** (must match at least one):
- product manager, senior product manager, product lead, head of product, group product manager, principal product manager, technical product manager

**Exclude** (discard if any match):
- project manager, program manager, delivery manager, account manager, product marketing manager

---

## Google Sheets Schema

### `company_watchlist`
| company_name | careers_url | ats_provider | hq_location | industry | priority_level |

### `hiring_signals`
| signal_id | dedupe_hash | source | signal_type | company | role_title | location | url | posted_time | discovered_time | score | is_high_priority | raw_text | notes | status |

### `collector_state`
| source | key | last_run_time | last_success_time | last_cursor | last_error |

---

## Run Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `credentials.json not found` | Download service account JSON from Google Cloud |
| `SPREADSHEET_ID not set` | Copy `.env.example` to `.env` and set values |
| `403 Permission Denied` | Share the Google Sheet with the service account email |
| SEEK/Indeed returning no results | Possible IP block — try again later or reduce cadence |
| Reddit 429 errors | Normal; tenacity will retry with backoff |

---

## Extending

**Add a new company**: Add a row to `company_watchlist` in the Google Sheet.

**Add a new collector**: Create `collectors/my_collector.py` extending `CollectorBase`, implement `collect()`, add to `scheduler.py`.

**Change cadences**: Set `ATS_INTERVAL_SECONDS`, `BOARD_INTERVAL_SECONDS`, `REDDIT_INTERVAL_SECONDS` in `.env`.
