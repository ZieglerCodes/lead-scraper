from app.services.cleaning import clean_row, unique_leads
from app.services.contacts import extract_from_html
from app.services.pipeline import demo_search, import_csv


def test_clean_row_preserves_no_email_business():
    result = clean_row({"Name": "  sample company ", "Phone": "713-555-0100", "Email": "bad"}, "test")
    assert result["name"] == "sample company"
    assert result["phone"] == "+17135550100"
    assert result["email"] is None


def test_csv_import_and_deduplication():
    csv_bytes = b"Name,Phone,Email,Website\nAcme,713-555-0100,bad,\nAcme,713-555-0100,,\nOther,,hello@example.com,\n"
    rows = import_csv(csv_bytes)
    assert len(rows) == 2
    assert rows[0]["name"] == "Acme"
    assert rows[1]["email"] == "hello@example.com"


def test_csv_rejects_unrecognized_headers():
    try:
        import_csv(b"irrelevant,columns\nvalue,value\n")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "column" in str(exc)


def test_parse_html_without_any_network_calls():
    contacts = extract_from_html("<html><body>Email support@example.com or call (713) 555-1234</body></html>")
    assert "support@example.com" in contacts["emails"]
    assert contacts["phones"]


def test_demo_search_is_synthetic_and_requested_size():
    results = demo_search("roofers", "Houston", 4)
    assert len(results) == 4
    assert all(row["source"] == "synthetic-demo" for row in results)
