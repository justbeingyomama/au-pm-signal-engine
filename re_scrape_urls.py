import os
import time
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
import httpx
from bs4 import BeautifulSoup
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

remote_idx = headers.index("remote_likelihood")
title_idx = headers.index("role_title")
loc_idx = headers.index("location")
url_idx = headers.index("url")

client = httpx.Client(timeout=10.0, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

updated = False
print(f"Checking {len(all_values) - 1} rows...")

for row in all_values[1:]:
    # Ensure row is long enough
    while len(row) <= max(remote_idx, title_idx, loc_idx, url_idx):
        row.append("")
        
    url = row[url_idx]
    current_likelihood = row[remote_idx]
    title = row[title_idx]
    loc = row[loc_idx]
    
    if url and url.startswith("http"):
        # We only really need to check if we haven't found a remote signal
        # but the user asked to check all.
        try:
            resp = client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                text = soup.get_text(" ", strip=True)
                
                new_calc = calculate_remote_likelihood(location=loc, title=title, text=text)
                if new_calc != current_likelihood:
                    print(f"Updated: {title} @ {row[4]} -> {new_calc}")
                    row[remote_idx] = new_calc
                    updated = True
            else:
                print(f"Skipping {url}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        
        # Small sleep to be nice to servers
        time.sleep(0.5)

if updated:
    ws.update("A1", all_values, value_input_option="RAW")
    print("Backfill complete! Updated sheet with new likelihoods.")
else:
    print("No new remote labels found after rescraping.")
