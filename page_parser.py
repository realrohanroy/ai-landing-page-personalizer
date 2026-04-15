import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def get_base_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def find_cta(soup) -> tuple:
    """
    Find the most likely CTA element.
    Priority: button > a with cta-like class/text > first prominent a tag
    Returns (tag, text)
    """
    # Priority 1: actual button tags
    buttons = soup.find_all("button")
    for btn in buttons:
        text = btn.get_text(strip=True)
        if text and len(text) < 50:  # ignore empty or paragraph-length buttons
            return btn, text

    # Priority 2: <a> tags with CTA-like keywords in class or text
    cta_keywords = ["cta", "btn", "button", "shop", "buy", "start", "get", "try", "sign", "join", "claim"]
    anchors = soup.find_all("a")
    for a in anchors:
        classes = " ".join(a.get("class", [])).lower()
        text = a.get_text(strip=True).lower()
        if any(kw in classes or kw in text for kw in cta_keywords):
            if a.get_text(strip=True) and len(a.get_text(strip=True)) < 50:
                return a, a.get_text(strip=True)

    # Priority 3: fallback to first <a> with short text
    for a in anchors:
        text = a.get_text(strip=True)
        if text and len(text) < 40:
            return a, text

    return None, "Learn More"

def extract_logo(soup, base_url: str) -> str | None:
    """Find logo URL and make it absolute"""
    import re
    logo = soup.find("img", {"alt": re.compile(r"logo", re.I)})
    if not logo:
        # try finding in header
        header = soup.find("header")
        if header:
            logo = header.find("img")
    
    if logo and logo.get("src"):
        src = logo["src"]
        if src.startswith("http"):
            return src
        elif src.startswith("//"):
            return "https:" + src
        elif src.startswith("/"):
            return base_url + src
    return None

def parse_page(url: str) -> dict:
    """
    Fetch and parse landing page.
    Returns structured data + parse status for fallback handling.
    """
    base_url = get_base_url(url)

    # ── Attempt fetch ──────────────────────────────────────────
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # raises on 4xx/5xx
        html = response.text
        fetch_status = "success"

    except requests.exceptions.Timeout:
        return _failed_parse(url, "timeout")

    except requests.exceptions.HTTPError as e:
        return _failed_parse(url, f"http_error_{e.response.status_code}")

    except requests.exceptions.RequestException:
        return _failed_parse(url, "connection_error")

    # ── Parse HTML ─────────────────────────────────────────────
    soup = BeautifulSoup(html, "html.parser")

    h1_tag = soup.find("h1")
    h2_tag = soup.find("h2")
    cta_tag, cta_text = find_cta(soup)
    logo_url = extract_logo(soup, base_url)

    # extract subheadline - h2 or first meaningful <p>
    subheadline = ""
    if h2_tag:
        subheadline = h2_tag.get_text(strip=True)
    else:
        paragraphs = soup.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 30 and len(text) < 200:  # meaningful paragraph
                subheadline = text
                break

    return {
        # raw data for apply_changes
        "html": html,
        "soup": soup,
        "h1_tag": h1_tag,
        "cta_tag": cta_tag,

        # clean text for LLM
        "h1": h1_tag.get_text(strip=True) if h1_tag else "Welcome",
        "h2": subheadline,
        "cta": cta_text,

        # for hero card reconstruction
        "logo_url": logo_url,
        "base_url": base_url,

        # status flags
        "fetch_status": fetch_status,
        "parse_failed": False
    }


def _failed_parse(url: str, reason: str) -> dict:
    """
    Returns a safe fallback dict when page fetch fails.
    Downstream code checks parse_failed flag to switch to hero card mode.
    """
    return {
        "html": "",
        "soup": None,
        "h1_tag": None,
        "cta_tag": None,
        "h1": "Welcome",
        "h2": "",
        "cta": "Learn More",
        "logo_url": None,
        "base_url": get_base_url(url),
        "fetch_status": reason,
        "parse_failed": True  # ← this flag drives fallback in main.py
    }