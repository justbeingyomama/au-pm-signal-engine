import logging
import os
from dotenv import load_dotenv

from collectors.indeed_collector import IndeedCollector
from models import CollectorState

logging.basicConfig(level=logging.INFO)
load_dotenv()

# We can mock the sheets dependency if we just want to run .collect() manually
class MockSheets:
    def upsert_collector_state(self, *args, **kwargs):
        pass

collector = IndeedCollector(MockSheets())
print("Starting indeed scrape...")
signals = collector.collect()
print(f"Got {len(signals)} signals!")
for i, sig in enumerate(signals[:3]):
    print(f"\n--- Signal {i+1} ---")
    print(f"Title: {sig.role_title}")
    print(f"Company: {sig.company}")
    print(f"URL: {sig.url}")
    print(f"Raw Text len: {len(sig.raw_text)}")
    print(f"Raw Snippet (first 150 chars): {sig.raw_text[:150]}")
