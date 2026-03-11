import time
from DrissionPage import ChromiumPage, ChromiumOptions

def test_indeed():
    print("Starting DrissionPage test...")
    co = ChromiumOptions()
    co.headless(True)
    
    page = ChromiumPage(co)
    print("Navigating to Indeed...")
    page.get('https://au.indeed.com/jobs?q=product+manager&l=Australia&sort=date')
    
    time.sleep(3)
    
    # Check if we got challenged
    print(f"Page Title: {page.title}")
    
    # Try finding job cards
    jobs = page.eles('.job_seen_beacon')
    if jobs:
        print(f"Found {len(jobs)} jobs!")
        print(f"First job text: {jobs[0].text[:100]}")
    else:
        print("No job cards found. Might be blocked.")
        
    page.quit()

if __name__ == "__main__":
    test_indeed()
