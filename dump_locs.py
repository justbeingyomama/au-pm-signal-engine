import csv
import gspread, os
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
creds = Credentials.from_service_account_file(credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"])
gc = gspread.authorize(creds)
sh = gc.open_by_key(os.getenv("SPREADSHEET_ID", ""))
ws = sh.worksheet("hiring_signals")
rows = ws.get_all_values()
with open("dump.csv", "w") as f:
    writer = csv.writer(f)
    for r in rows:
        writer.writerow([r[5] if len(r)>5 else "", r[6] if len(r)>6 else ""])
