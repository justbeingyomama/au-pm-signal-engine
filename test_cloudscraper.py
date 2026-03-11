import cloudscraper

scraper = cloudscraper.create_scraper()
print("Fetching with cloudscraper...")
try:
    response = scraper.get("https://au.indeed.com/jobs?q=product+manager&l=Australia&sort=date")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Success! Title:", response.text[response.text.find('<title>'):response.text.find('</title>')+8])
    else:
        print("Blocked:", response.text[:200])
except Exception as e:
    print("Error:", e)
