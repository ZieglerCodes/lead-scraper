from typing import Literal
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=120, examples=["roofing contractors"])
    location: str = Field(min_length=2, max_length=120, examples=["Houston, TX"])
    max_results: int = Field(default=10, ge=1, le=50)
    source: Literal["demo"] = "demo"
