"""CSV record cleaning refactored from clean_data.py and combine_CSVs.py.

The original script discarded every row without a valid email. Here a business
with a name/address or phone is retained, while invalid contact details are blanked.
US phone normalization is intentionally basic in Phase 1; add phonenumbers later
for international support and stronger validation.
"""
import re
from collections.abc import Iterable

EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

ALIASES = {
    "name": ["Name", "Business Name", "Company", "Company Name"],
    "address": ["Address", "Formatted Address", "Street Address"],
    "phone": ["Phone", "Phone Number", "Telephone"],
    "email": ["Email", "Email Address", "E-mail"],
    "website": ["Website", "URL", "Web Site"],
}


def _field(row: dict, aliases: list[str]) -> str:
    lookup = {str(key).strip().casefold(): value for key, value in row.items()}
    for alias in aliases:
        value = lookup.get(alias.casefold())
        if value is not None:
            value = str(value).strip()
            if value and value.casefold() not in {"nan", "none", "null"}:
                return value
    return ""


def clean_email(value: str) -> str | None:
    for candidate in re.split(r"[,;\s]+", value or ""):
        candidate = candidate.strip()
        if EMAIL.fullmatch(candidate):
            return candidate.lower()
    return None


def clean_us_phone(value: str) -> str | None:
    # Limited to the North American Numbering Plan. No international assumptions.
    first = re.split(r"[,;]", value or "", maxsplit=1)[0]
    digits = re.sub(r"\D", "", first)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10 or digits[0] in "01" or digits[3] in "01":
        return None
    return "+1" + digits


def clean_row(row: dict, source: str) -> dict | None:
    name = _field(row, ALIASES["name"]).strip()
    address = _field(row, ALIASES["address"]).strip()
    phone = clean_us_phone(_field(row, ALIASES["phone"]))
    email = clean_email(_field(row, ALIASES["email"]))
    website = _field(row, ALIASES["website"]).strip()
    if website and not website.lower().startswith(("https://", "http://")):
        website = ""  # Preserve only explicit http(s) URLs; never fetch here.
    if not (name or address or phone or email or website):
        return None
    return {
        "name": name or None,
        "address": address or None,
        "phone": phone,
        "email": email,
        "website": website or None,
        "source": source,
    }


def unique_leads(rows: Iterable[dict]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        # Prefer stronger stable identifiers; fall back to name + address.
        if row.get("website"):
            key = ("website", row["website"].rstrip("/").casefold())
        elif row.get("email"):
            key = ("email", row["email"].casefold())
        elif row.get("phone"):
            key = ("phone", row["phone"])
        else:
            key = ("name-address", f"{row.get('name') or ''}|{row.get('address') or ''}".casefold())
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result
