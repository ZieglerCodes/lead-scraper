"""Reusable pipeline from master_pipeline.py, with no input() or os.system()."""
import csv
import io

from app.services.cleaning import clean_row, unique_leads
from app.services.sources import SOURCES

MAX_CSV_ROWS = 2_000
csv.field_size_limit(100_000)


def demo_search(query: str, location: str, limit: int) -> list[dict]:
    raw = SOURCES["demo"].search(query, location, limit)
    cleaned = (clean_row(row, source="synthetic-demo") for row in raw)
    # Demo leads have distinct email identities; website is same illustrative URL.
    return unique_leads_for_demo(row for row in cleaned if row)


def unique_leads_for_demo(rows):
    # Avoid identical example.com website from obscuring synthetic fixtures.
    result = []
    seen = set()
    for row in rows:
        identity = row.get("email")
        if identity not in seen:
            seen.add(identity)
            result.append(row)
    return result


def import_csv(content: bytes) -> list[dict]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc
    try:
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV is missing a header row")
        recognized = {"name", "business name", "company", "company name", "address",
                      "formatted address", "street address", "phone", "phone number",
                      "telephone", "email", "email address", "e-mail", "website", "url", "web site"}
        if not any(field and field.strip().casefold() in recognized for field in reader.fieldnames):
            raise ValueError("CSV needs at least one column such as Name, Phone, Email, Website or Address")
        cleaned = []
        for n, row in enumerate(reader, start=1):
            if n > MAX_CSV_ROWS:
                raise ValueError(f"CSV exceeds the {MAX_CSV_ROWS} row limit for this development build")
            if None in row:
                raise ValueError(f"CSV row {n} has more columns than its header")
            candidate = clean_row(row, source="user-provided-csv")
            if candidate:
                cleaned.append(candidate)
        return unique_leads(cleaned)
    except csv.Error as exc:
        raise ValueError("CSV content is malformed") from exc
