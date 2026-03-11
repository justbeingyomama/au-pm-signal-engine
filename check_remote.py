import os
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from scoring import calculate_remote_likelihood

load_dotenv()
credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
creds = Credentials.from_service_account_file(credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.readonly"])
gc = gspread.authorize(creds)
sh = gc.open_by_key(os.getenv("SPREADSHEET_ID", ""))
ws = sh.worksheet("hiring_signals")
rows = ws.get_all_values()
headers = rows[0]

# check raw calculation on all rows
high_count = 0
med_count = 0
low_count = 0

for row in rows[1:]:
    loc = row[6] if len(row) > 6 else ""
    title = row[5] if len(row) > 5 else ""
    text = row[13] if len(row) > 13 else ""
    
    calc = calculate_remote_likelihood(loc, title, text)
    if calc == "High":
        high_count += 1
        print(f"HIGH: {title} @ {row[4]} | Loc: {loc}")
    elif calc == "Med":
        med_count += 1
        print(f"MED: {title} @ {row[4]} | Loc: {loc}")
    else:
        low_count += 1

print(f"Summary -> High: {high_count}, Med: {med_count}, Low: {low_count}")
