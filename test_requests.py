import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

print("Fetching with requests...")
response = requests.get('https://au.indeed.com/jobs?q=product+manager&l=Australia&sort=date', headers=headers)
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("Success! Title:", response.text[response.text.find('<title>'):response.text.find('</title>')+8])
else:
    print("Blocked:", response.text[:200])
