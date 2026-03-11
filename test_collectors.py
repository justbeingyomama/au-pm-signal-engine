import logging
from dotenv import load_dotenv
from sheets.client import SheetsClient
from collectors.reddit_collector import RedditCollector
from collectors.wellfound_collector import WellfoundCollector
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

sheets = SheetsClient(os.getenv("GOOGLE_CREDENTIALS_JSON"), os.getenv("SPREADSHEET_ID"))

print("Testing Reddit Collector...")
reddit = RedditCollector(sheets)
reddit_sigs = reddit.collect()
print(f"Reddit Found: {len(reddit_sigs)} signals")

print("Testing Wellfound Collector...")
wf = WellfoundCollector(sheets)
wf_sigs = wf.collect()
print(f"Wellfound Found: {len(wf_sigs)} signals")
