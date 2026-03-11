import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from scoring import calculate_remote_likelihood

load_dotenv()

credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
spreadsheet_id = os.getenv("SPREADSHEET_ID", "")

if not spreadsheet_id or not os.path.isfile(credentials_path):
    print("Missing credentials or SPREADSHEET_ID.")
    exit(1)

creds = Credentials.from_service_account_file(credentials_path, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
])
gc = gspread.authorize(creds)
sh = gc.open_by_key(spreadsheet_id)
ws = sh.worksheet("hiring_signals")

all_values = ws.get_all_values()
headers = all_values[0]

if "remote_likelihood" not in headers:
    print("remote_likelihood column not found. Run migration script first.")
    exit(1)

remote_idx = headers.index("remote_likelihood")
title_idx = headers.index("role_title")
loc_idx = headers.index("location")
text_idx = headers.index("raw_text")

updated = False
for row in all_values[1:]:
    # Ensure row is long enough
    while len(row) <= max(remote_idx, title_idx, loc_idx, text_idx):
        row.append("")
        
    calc_val = calculate_remote_likelihood(
        location=row[loc_idx],
        title=row[title_idx],
        text=row[text_idx]
    )
    
    if row[remote_idx] != calc_val:
        row[remote_idx] = calc_val
        updated = True

if updated:
    ws.update("A1", all_values, value_input_option="RAW")
    print("Backfill complete! Updated historical records with correct remote likelihood.")
else:
    print("All records are already up to date.")
