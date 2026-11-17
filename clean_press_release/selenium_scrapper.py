import os, time
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
try:
    # optional: auto-manage chromedriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    _USE_WDM = True
except Exception:
    _USE_WDM = False

NAV_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/139.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,image/apng,*/*;q=0.8,"
               "application/signed-exchange;v=b3;q=0.7"),
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

def download_pdf_with_selenium_cookies(url: str, out_dir: Path, referer: str = "https://www.saudiexchange.sa/") -> Path:
    """Open saudiexchange in headless Chrome, grab cookies, then use requests to download the PDF."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=" + NAV_HEADERS["User-Agent"])

    if _USE_WDM:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.saudiexchange.sa/")
        time.sleep(2.0)  # let WAF/cookies set

        # get cookies and transfer to requests
        jar = requests.Session()
        jar.headers.update({**NAV_HEADERS, "Referer": referer})
        for c in driver.get_cookies():
            # include domain/path to avoid cookie being ignored
            jar.cookies.set(c.get("name"), c.get("value"), domain=c.get("domain"), path=c.get("path", "/"))

        # now fetch the PDF
        r = jar.get(url, timeout=60, allow_redirects=True, stream=True)
        if r.status_code in (401, 403):
            # try with root referer as fallback
            jar.headers["Referer"] = "https://www.saudiexchange.sa/"
            r = jar.get(url, timeout=60, allow_redirects=True, stream=True)
        r.raise_for_status()

        fp = out_dir / Path(url).name
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return fp
    finally:
        driver.quit()
