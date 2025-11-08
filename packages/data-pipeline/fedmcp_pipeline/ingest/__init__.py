"""Data ingestion modules."""

from .parliament import ingest_parliament_data
from .lobbying import ingest_lobbying_data
from .finances import ingest_financial_data

__all__ = [
    "ingest_parliament_data",
    "ingest_lobbying_data",
    "ingest_financial_data",
]
