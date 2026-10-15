"""HTML contact parsing from contact_extractor.py; no outbound web requests.

A future URL-fetching service needs SSRF safeguards, robots/ToS review,
DNS/IP validation, redirect protection, timeouts, and content-size limits.
"""
import re
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s.\-]?)?\(?[2-9]\d{2}\)?[\s.\-]?[2-9]\d{2}[\s.\-]?\d{4}")


def extract_from_html(html: str) -> dict[str, list[str]]:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return {
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "phones": sorted(set(PHONE_RE.findall(text))),
    }
