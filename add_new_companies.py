import os
from dotenv import load_dotenv
from sheets.client import SheetsClient

load_dotenv()
creds = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
sheet_id = os.getenv("SPREADSHEET_ID")

client = SheetsClient(creds, sheet_id)

NEW_COMPANIES = [
    # Company, Careers URL, ATS Provider, HQ, Industry, Priority
    ["Domain", "https://careers.domain.com.au/", "Lever", "Sydney", "Prop Tech", "High"],
    ["Macquarie Group", "https://www.macquarie.com/au/en/careers.html", "", "Sydney", "Fintech", "High"],
    ["Zip Co", "https://zip.co/us/careers", "Lever", "Sydney", "Fintech", "High"],
    ["Tyro Payments", "https://www.tyro.com/careers/", "Greenhouse", "Sydney", "Fintech", "High"],
    ["Mr Yum", "https://careers.mryum.com/", "Lever", "Melbourne", "Hospitality Tech", "Med"],
    ["Go1", "https://www.go1.com/careers", "Greenhouse", "Brisbane", "EdTech", "High"],
    ["Miro", "https://miro.com/careers/", "Greenhouse", "Sydney", "Collaboration SaaS", "High"], # Hub in Sydney
    ["Kmart Group Tech", "https://www.kmart.com.au/careers/tech/", "", "Melbourne", "Retail Tech", "Med"],
    ["Woolworths Group", "https://wowcareers.com.au/tech", "", "Sydney", "Retail Tech", "Med"],
    ["Aussie Broadband", "https://www.aussiebroadband.com.au/careers/", "Greenhouse", "Melbourne", "Telco", "Med"],
    ["Finder", "https://www.finder.com.au/careers", "Greenhouse", "Sydney", "Fintech", "High"],
    ["Pet Circle", "https://www.petcircle.com.au/careers", "Lever", "Sydney", "E-commerce", "Med"],
    ["HiPages", "https://hipagesgroup.com.au/careers/", "Lever", "Sydney", "Marketplace", "Med"],
    ["Up Bank", "https://up.com.au/careers/", "Workable", "Melbourne", "Fintech", "High"],
    ["PEXA", "https://www.pexa.com.au/careers/", "Greenhouse", "Melbourne", "Prop Tech", "High"],
    ["Envato", "https://envato.com/careers/", "Greenhouse", "Melbourne", "Marketplace", "High"],
    ["Judo Bank", "https://www.judo.bank/careers", "Lever", "Melbourne", "Fintech", "High"],
    ["Xplor", "https://www.xplortechnologies.com/careers", "Greenhouse", "Melbourne", "SaaS", "Med"],
    ["Bigtincan", "https://www.bigtincan.com/careers/", "Greenhouse", "Sydney", "Sales Tech", "Med"],
    ["SiteMinder", "https://www.siteminder.com/careers/", "Greenhouse", "Sydney", "Hospitality SaaS", "High"],
    ["GitLab", "https://about.gitlab.com/jobs/", "Greenhouse", "Remote", "Software SaaS", "High"],
    ["Stripe", "https://stripe.com/jobs", "Greenhouse", "Remote", "Fintech", "High"],
    ["Automattic", "https://automattic.com/work-with-us/", "Greenhouse", "Remote", "CMS/SaaS", "High"],
    ["Tailor", "https://www.tailor.tech/careers", "", "Remote", "ERP Tech", "High"],
    ["ProcurePro", "https://procurepro.co/careers/", "", "Remote", "ConTech SaaS", "High"],
    ["upcover", "https://www.upcover.com/careers", "", "Remote", "InsurTech", "Med"],
    ["Who Gives A Crap", "https://au.whogivesacrap.org/pages/jobs", "Greenhouse", "Remote", "D2C/E-comm", "High"],
    ["Deputy", "https://www.deputy.com/company/careers", "", "Remote", "HR Tech SaaS", "High"]
]

print(f"Adding {len(NEW_COMPANIES)} new companies to the watchlist...")

# To append, we use the client's internal gspread worksheet object directly
ws = client._sh.worksheet("company_watchlist")
ws.append_rows(NEW_COMPANIES, value_input_option="USER_ENTERED")

print("Successfully added new companies to Google Sheets!")
