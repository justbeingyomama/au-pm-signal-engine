from curl_cffi import requests
import time

impersonates = [
    "chrome", "chrome120", "chrome124", "chrome116", "safari", "safari17_0", "edge101"
]

for imp in impersonates:
    print(f"Testing impersonate: {imp}")
    try:
        r = requests.get('https://au.indeed.com/jobs?q=product+manager&l=Australia&sort=date', impersonate=imp, timeout=10)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            print("TITLE:", r.text[r.text.find('<title>'):r.text.find('</title>')+8])
        else:
            print("Failed")
    except Exception as e:
        print("Error:", e)
    time.sleep(2)
