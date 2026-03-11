import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
spreadsheet_id = os.getenv("SPREADSHEET_ID", "")

if not spreadsheet_id or not os.path.isfile(credentials_path):
    print("Missing credentials or SPREADSHEET_ID. Check your .env file.")
    exit(1)

creds = Credentials.from_service_account_file(credentials_path, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
])
gc = gspread.authorize(creds)
sh = gc.open_by_key(spreadsheet_id)

try:
    ws = sh.worksheet("hiring_signals")
except gspread.WorksheetNotFound:
    print("Tab hiring_signals not found!")
    exit(1)

all_values = ws.get_all_values()
if not all_values:
    print("Sheet is empty.")
    exit(0)

headers = all_values[0]

if "remote_likelihood" not in headers:
    is_hp_idx = headers.index("is_high_priority")
    insert_idx = is_hp_idx + 1
    
    # Update headers
    all_values[0].insert(insert_idx, "remote_likelihood")
    
    # Update all rows
    for row in all_values[1:]:
        while len(row) < insert_idx:
            row.append("")
        row.insert(insert_idx, "Low") # Defaulting older signals to Low or empty
        
    ws.update("A1", all_values, value_input_option="RAW")
    print(f"Migration complete! Added remote_likelihood at index {insert_idx}.")
else:
    print("Already migrated.")
