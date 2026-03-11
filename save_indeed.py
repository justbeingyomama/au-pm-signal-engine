from curl_cffi import requests

r = requests.get('https://au.indeed.com/jobs?q=product+manager&l=Australia&sort=date', impersonate="chrome120", timeout=15)
with open("indeed_test.html", "w") as f:
    f.write(r.text)
print("Saved HTML")
