import urllib.request
import urllib.parse
import json
import time

COMPANIES = [
    "Canva", "Atlassian", "SafetyCulture", "Culture Amp", "Immutable", 
    "Dovetail", "Harrison.ai", "Linktree", "Airwallex", "Go1", 
    "Zeller", "Employment Hero", "Pet Circle", "Rokt", "Siteminder", 
    "Afterpay", "Zip Co", "Tyro", "Eucalyptus", "Mr Yum", 
    "Octopus Deploy", "Airtasker", "Finder", "Hipages", "Envato", 
    "Moula", "Judo Bank", "Prospa", "Openpay", "Xero", 
    "Vanguard", "Macquarie Group", "CBA", "NAB", "ANZ", 
    "Westpac", "Telstra", "Optus", "REA Group", "Domain", 
    "SEEK", "Carsales", "IRESS", "WiseTech Global", "Altium", 
    "Appen", "Megaport", "Data#3", "TechnologyOne"
]

results = []

def search_duckduckgo(query):
    # Just standard DDG html search
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        if 'class="result__url"' in html:
            start = html.find('class="result__url"')
            start = html.find('href="', start) + 6
            end = html.find('"', start)
            link = html[start:end]
            
            # Clean up DDG tracking redirect
            if link.startswith('//duckduckgo.com/l/?uddg='):
                encoded_url = link.split('uddg=')[1].split('&')[0]
                link = urllib.parse.unquote(encoded_url)
                
            return link
    except Exception as e:
        print(f"Error searching {query}: {e}")
    return ""

print("Fetching URLs...")
for company in COMPANIES:
    query = f"{company} careers OR jobs Australia"
    url = search_duckduckgo(query)
    
    hq = "Sydney" if company in ["Canva", "Atlassian", "SafetyCulture", "Rokt", "Zip Co", "Tyro", "Finder", "Hipages", "Airtasker"] else "Melbourne"
    priority = "High" if company in ["Canva", "Atlassian", "Airwallex", "Culture Amp"] else "Med"
    
    results.append([company, url, "", hq, "Tech", priority])
    print(f"[{company}] {url}")
    time.sleep(1.5)

with open("/Users/umama/.gemini/antigravity/scratch/au-pm-signal-engine/collectors/new_companies.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nDone! Wrote to new_companies.json")
