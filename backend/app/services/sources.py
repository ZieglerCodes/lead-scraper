"""Search source abstraction. Only synthetic/demo results are enabled.

Do not connect the old Google Places CSV-export script to this source; review
provider licensing for saved/redistributed lead records first.
"""
from typing import Protocol


class LeadSource(Protocol):
    def search(self, query: str, location: str, limit: int) -> list[dict]: ...


class DemoSource:
    def search(self, query: str, location: str, limit: int) -> list[dict]:
        return [
            {
                "Name": f"DEMO {query.title()} {i:03d}",
                "Address": f"DEMO ONLY — {location}",
                "Phone": "",
                "Email": f"sample{i:03d}@example.com",
                "Website": "https://example.com",
            }
            for i in range(1, limit + 1)
        ]


# Future providers must be reviewed for data storage, export and resale rights.
SOURCES: dict[str, LeadSource] = {"demo": DemoSource()}
