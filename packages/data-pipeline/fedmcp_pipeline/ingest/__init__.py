"""Data ingestion modules."""

from .parliament import ingest_parliament_data
from .lobbying import ingest_lobbying_data
from .finances import ingest_financial_data
from .bill_structure import (
    ingest_bill_structure,
    ingest_bills_from_list,
    ingest_all_bills_in_session,
    run_bill_structure_ingestion,
    create_bill_structure_schema,
)
from .cross_reference_agent import (
    CrossReferenceAgent,
    EntityMention,
    EntityType,
    extract_mentions_from_text,
)

__all__ = [
    "ingest_parliament_data",
    "ingest_lobbying_data",
    "ingest_financial_data",
    # Bill structure
    "ingest_bill_structure",
    "ingest_bills_from_list",
    "ingest_all_bills_in_session",
    "run_bill_structure_ingestion",
    "create_bill_structure_schema",
    # Cross-reference
    "CrossReferenceAgent",
    "EntityMention",
    "EntityType",
    "extract_mentions_from_text",
]
