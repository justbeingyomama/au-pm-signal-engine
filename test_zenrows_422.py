import os
import requests
from dotenv import load_dotenv

load_dotenv()
zenrows_key = os.getenv("ZENROWS_API_KEY")
url = "https://au.indeed.com/jobs?q=product+manager&l=Australia"

proxy_url = "https://api.zenrows.com/v1/"
params = {
    "url": url, 
    "apikey": zenrows_key, 
    "premium_proxy": "true",
    "js_render": "true"
}

print("Sending request to ZenRows with js_render...")
resp = requests.get(proxy_url, params=params)
print(f"Status Code: {resp.status_code}")
print(f"Response Body length: {len(resp.text)}")
if resp.status_code == 200:
    print("Success! Got HTML back.")
else:
    print(f"Response Body: {resp.text}")
