"""Bill structure ingestion from Parliament.ca XML to Neo4j.

This module imports structured bill content (parts, sections, subsections, paragraphs)
as well as version history and amendment events from LEGISinfo.

Data Sources:
- Parliament.ca Bill XML: /Content/Bills/{parliament}/{type}/{bill}/{bill}_{version}/{bill}_E.xml
- LEGISinfo JSON API: /LegisInfo/en/bill/{session}/{bill}/json

Neo4j Schema:
    Nodes:
        - BillVersion: Version snapshots through legislative process
        - BillAmendmentEvent: Amendment-related events (committee reports, etc.)
        - BillPart: Top-level divisions (Part I, Part II)
        - BillSection: Main numbered sections (1, 2, 3...)
        - BillSubsection: Subsections (1), (2), (3)...
        - BillParagraph: Paragraphs (a), (b), (c)...
        - BillSubparagraph: Subparagraphs (i), (ii), (iii)...
        - BillDefinition: Definitions within bills

    Relationships:
        - (Bill)-[:HAS_VERSION]->(BillVersion)
        - (Bill)-[:HAS_AMENDMENT_EVENT]->(BillAmendmentEvent)
        - (Bill)-[:HAS_PART]->(BillPart)
        - (Bill)-[:HAS_SECTION]->(BillSection) (for sections not in parts)
        - (BillPart)-[:HAS_SECTION]->(BillSection)
        - (BillSection)-[:HAS_SUBSECTION]->(BillSubsection)
        - (BillSubsection)-[:HAS_PARAGRAPH]->(BillParagraph)
        - (BillParagraph)-[:HAS_SUBPARAGRAPH]->(BillSubparagraph)
        - (Bill)-[:HAS_DEFINITION]->(BillDefinition)

Example:
    >>> from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
    >>> neo4j = Neo4jClient(uri="bolt://localhost:7687", user="neo4j", password="password")
    >>>
    >>> # Ingest a single bill
    >>> result = ingest_bill_structure(neo4j, parliament=44, session=1, bill_number="C-2")
    >>>
    >>> # Ingest multiple bills
    >>> results = ingest_bills_from_list(neo4j, bills=[("44-1", "C-2"), ("44-1", "C-3")])
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.bill_text_xml import (
    BillTextXMLClient,
    ParsedBill,
    BillVersion,
    BillAmendmentEvent,
    BillPart,
    BillSection,
    BillSubsection,
    BillParagraph,
    BillSubparagraph,
    BillDefinition,
    to_dict,
)

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger, ProgressTracker


def create_bill_structure_schema(neo4j_client: Neo4jClient) -> None:
    """Create Neo4j schema for bill structure nodes.

    Creates:
        - Unique constraints on all structure node IDs
        - Indexes on anchor_id for fast lookups
        - Indexes on bill_id for relationship creation
    """
    logger.info("Creating bill structure schema...")

    # BillVersion
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_version_id IF NOT EXISTS
        FOR (bv:BillVersion) REQUIRE bv.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_version_bill_id IF NOT EXISTS
        FOR (bv:BillVersion) ON (bv.bill_id)
    """)

    # BillAmendmentEvent
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_amendment_event_id IF NOT EXISTS
        FOR (bae:BillAmendmentEvent) REQUIRE bae.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_amendment_event_bill_id IF NOT EXISTS
        FOR (bae:BillAmendmentEvent) ON (bae.bill_id)
    """)

    # BillPart
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_part_id IF NOT EXISTS
        FOR (bp:BillPart) REQUIRE bp.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_part_anchor_id IF NOT EXISTS
        FOR (bp:BillPart) ON (bp.anchor_id)
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_part_bill_id IF NOT EXISTS
        FOR (bp:BillPart) ON (bp.bill_id)
    """)

    # BillSection
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_section_id IF NOT EXISTS
        FOR (bs:BillSection) REQUIRE bs.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_section_anchor_id IF NOT EXISTS
        FOR (bs:BillSection) ON (bs.anchor_id)
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_section_bill_id IF NOT EXISTS
        FOR (bs:BillSection) ON (bs.bill_id)
    """)

    # BillSubsection
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_subsection_id IF NOT EXISTS
        FOR (bss:BillSubsection) REQUIRE bss.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_subsection_anchor_id IF NOT EXISTS
        FOR (bss:BillSubsection) ON (bss.anchor_id)
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_subsection_section_id IF NOT EXISTS
        FOR (bss:BillSubsection) ON (bss.section_id)
    """)

    # BillParagraph
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_paragraph_id IF NOT EXISTS
        FOR (bpg:BillParagraph) REQUIRE bpg.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_paragraph_anchor_id IF NOT EXISTS
        FOR (bpg:BillParagraph) ON (bpg.anchor_id)
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_paragraph_subsection_id IF NOT EXISTS
        FOR (bpg:BillParagraph) ON (bpg.subsection_id)
    """)

    # BillSubparagraph
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_subparagraph_id IF NOT EXISTS
        FOR (bsp:BillSubparagraph) REQUIRE bsp.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_subparagraph_anchor_id IF NOT EXISTS
        FOR (bsp:BillSubparagraph) ON (bsp.anchor_id)
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_subparagraph_paragraph_id IF NOT EXISTS
        FOR (bsp:BillSubparagraph) ON (bsp.paragraph_id)
    """)

    # BillDefinition
    neo4j_client.run_query("""
        CREATE CONSTRAINT bill_definition_id IF NOT EXISTS
        FOR (bd:BillDefinition) REQUIRE bd.id IS UNIQUE
    """)
    neo4j_client.run_query("""
        CREATE INDEX bill_definition_bill_id IF NOT EXISTS
        FOR (bd:BillDefinition) ON (bd.bill_id)
    """)

    logger.info("✅ Bill structure schema created")


def ingest_bill_versions(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill version nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with available_versions

    Returns:
        Number of versions created
    """
    if not bill.available_versions:
        return 0

    bill_id = f"{bill.session_str}:{bill.bill_number}"
    now = datetime.utcnow().isoformat()

    versions_data = []
    for ver in bill.available_versions:
        version_id = f"{bill_id}:v{ver.version_number}"
        versions_data.append({
            "id": version_id,
            "bill_id": bill_id,
            "version_number": ver.version_number,
            "stage": ver.stage.value if ver.stage else "first-reading",
            "publication_type_name": ver.publication_type_name,
            "publication_date": ver.publication_date.isoformat() if ver.publication_date else None,
            "has_amendments": ver.has_amendments,
            "xml_url": ver.xml_url,
            "pdf_url": ver.pdf_url,
            "updated_at": now,
        })

    # Create BillVersion nodes
    cypher = """
    UNWIND $versions AS v
    MERGE (bv:BillVersion {id: v.id})
    SET bv.bill_id = v.bill_id,
        bv.version_number = v.version_number,
        bv.stage = v.stage,
        bv.publication_type_name = v.publication_type_name,
        bv.publication_date = CASE WHEN v.publication_date IS NOT NULL
            THEN datetime(v.publication_date) ELSE NULL END,
        bv.has_amendments = v.has_amendments,
        bv.xml_url = v.xml_url,
        bv.pdf_url = v.pdf_url,
        bv.updated_at = datetime(v.updated_at)
    WITH bv, v
    MATCH (b:Bill {id: v.bill_id})
    MERGE (b)-[:HAS_VERSION]->(bv)
    RETURN count(bv) as created
    """

    result = neo4j_client.run_query(cypher, {"versions": versions_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillVersion nodes")
    return created


def ingest_amendment_events(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill amendment event nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with amendment_events

    Returns:
        Number of amendment events created
    """
    if not bill.amendment_events:
        return 0

    bill_id = f"{bill.session_str}:{bill.bill_number}"
    now = datetime.utcnow().isoformat()

    events_data = []
    for i, event in enumerate(bill.amendment_events, start=1):
        event_id = f"{bill_id}:amend:{i}"
        events_data.append({
            "id": event_id,
            "bill_id": bill_id,
            "event_type": event.event_type,
            "description_en": event.description_en,
            "description_fr": event.description_fr,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "chamber": event.chamber,
            "stage": event.stage,
            "committee_code": event.committee_code,
            "committee_name": event.committee_name,
            "report_id": event.report_id,
            "report_number": event.report_number,
            "number_of_amendments": event.number_of_amendments,
            "updated_at": now,
        })

    # Create BillAmendmentEvent nodes
    cypher = """
    UNWIND $events AS e
    MERGE (bae:BillAmendmentEvent {id: e.id})
    SET bae.bill_id = e.bill_id,
        bae.event_type = e.event_type,
        bae.description_en = e.description_en,
        bae.description_fr = e.description_fr,
        bae.event_date = CASE WHEN e.event_date IS NOT NULL
            THEN datetime(e.event_date) ELSE NULL END,
        bae.chamber = e.chamber,
        bae.stage = e.stage,
        bae.committee_code = e.committee_code,
        bae.committee_name = e.committee_name,
        bae.report_id = e.report_id,
        bae.report_number = e.report_number,
        bae.number_of_amendments = e.number_of_amendments,
        bae.updated_at = datetime(e.updated_at)
    WITH bae, e
    MATCH (b:Bill {id: e.bill_id})
    MERGE (b)-[:HAS_AMENDMENT_EVENT]->(bae)
    RETURN count(bae) as created
    """

    result = neo4j_client.run_query(cypher, {"events": events_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillAmendmentEvent nodes")
    return created


def ingest_bill_parts(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill part nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with parts

    Returns:
        Number of parts created
    """
    if not bill.parts:
        return 0

    bill_id = f"{bill.session_str}:{bill.bill_number}"
    now = datetime.utcnow().isoformat()

    parts_data = []
    for part in bill.parts:
        parts_data.append({
            "id": part.id,
            "bill_id": bill_id,
            "number": part.number,
            "title_en": part.title_en,
            "title_fr": part.title_fr,
            "anchor_id": part.anchor_id,
            "sequence": part.sequence,
            "updated_at": now,
        })

    # Create BillPart nodes
    cypher = """
    UNWIND $parts AS p
    MERGE (bp:BillPart {id: p.id})
    SET bp.bill_id = p.bill_id,
        bp.number = p.number,
        bp.title_en = p.title_en,
        bp.title_fr = p.title_fr,
        bp.anchor_id = p.anchor_id,
        bp.sequence = p.sequence,
        bp.updated_at = datetime(p.updated_at)
    WITH bp, p
    MATCH (b:Bill {id: p.bill_id})
    MERGE (b)-[:HAS_PART]->(bp)
    RETURN count(bp) as created
    """

    result = neo4j_client.run_query(cypher, {"parts": parts_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillPart nodes")
    return created


def ingest_bill_sections(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill section nodes and relationships.

    Handles both:
    - Sections within parts: (BillPart)-[:HAS_SECTION]->(BillSection)
    - Loose sections (no part): (Bill)-[:HAS_SECTION]->(BillSection)

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with parts and sections

    Returns:
        Number of sections created
    """
    bill_id = f"{bill.session_str}:{bill.bill_number}"
    now = datetime.utcnow().isoformat()

    sections_data = []

    # Sections within parts
    for part in bill.parts:
        for section in part.sections:
            sections_data.append({
                "id": section.id,
                "bill_id": bill_id,
                "part_id": part.id,
                "number": section.number,
                "marginal_note_en": section.marginal_note_en,
                "marginal_note_fr": section.marginal_note_fr,
                "text_en": section.text_en,
                "text_fr": section.text_fr,
                "anchor_id": section.anchor_id,
                "sequence": section.sequence,
                "updated_at": now,
            })

    # Loose sections (not in any part)
    for section in bill.sections:
        sections_data.append({
            "id": section.id,
            "bill_id": bill_id,
            "part_id": None,
            "number": section.number,
            "marginal_note_en": section.marginal_note_en,
            "marginal_note_fr": section.marginal_note_fr,
            "text_en": section.text_en,
            "text_fr": section.text_fr,
            "anchor_id": section.anchor_id,
            "sequence": section.sequence,
            "updated_at": now,
        })

    if not sections_data:
        return 0

    # Create BillSection nodes
    cypher = """
    UNWIND $sections AS s
    MERGE (bs:BillSection {id: s.id})
    SET bs.bill_id = s.bill_id,
        bs.part_id = s.part_id,
        bs.number = s.number,
        bs.marginal_note_en = s.marginal_note_en,
        bs.marginal_note_fr = s.marginal_note_fr,
        bs.text_en = s.text_en,
        bs.text_fr = s.text_fr,
        bs.anchor_id = s.anchor_id,
        bs.sequence = s.sequence,
        bs.updated_at = datetime(s.updated_at)
    RETURN count(bs) as created
    """

    result = neo4j_client.run_query(cypher, {"sections": sections_data})
    created = result[0]["created"] if result else 0

    # Create relationships for sections in parts
    cypher_part_rel = """
    UNWIND $sections AS s
    MATCH (bs:BillSection {id: s.id})
    MATCH (bp:BillPart {id: s.part_id})
    WHERE s.part_id IS NOT NULL
    MERGE (bp)-[:HAS_SECTION]->(bs)
    """
    neo4j_client.run_query(cypher_part_rel, {"sections": sections_data})

    # Create relationships for loose sections (Bill -> Section)
    cypher_bill_rel = """
    UNWIND $sections AS s
    MATCH (bs:BillSection {id: s.id})
    MATCH (b:Bill {id: s.bill_id})
    WHERE s.part_id IS NULL
    MERGE (b)-[:HAS_SECTION]->(bs)
    """
    neo4j_client.run_query(cypher_bill_rel, {"sections": sections_data})

    logger.info(f"  ✅ Created {created} BillSection nodes")
    return created


def ingest_bill_subsections(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill subsection nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with parts and sections

    Returns:
        Number of subsections created
    """
    now = datetime.utcnow().isoformat()
    subsections_data = []

    # Collect all subsections from all sections
    all_sections = list(bill.sections)  # Loose sections
    for part in bill.parts:
        all_sections.extend(part.sections)

    for section in all_sections:
        for subsection in section.subsections:
            subsections_data.append({
                "id": subsection.id,
                "section_id": section.id,
                "number": subsection.number,
                "text_en": subsection.text_en,
                "text_fr": subsection.text_fr,
                "anchor_id": subsection.anchor_id,
                "sequence": subsection.sequence,
                "updated_at": now,
            })

    if not subsections_data:
        return 0

    # Create BillSubsection nodes
    cypher = """
    UNWIND $subsections AS ss
    MERGE (bss:BillSubsection {id: ss.id})
    SET bss.section_id = ss.section_id,
        bss.number = ss.number,
        bss.text_en = ss.text_en,
        bss.text_fr = ss.text_fr,
        bss.anchor_id = ss.anchor_id,
        bss.sequence = ss.sequence,
        bss.updated_at = datetime(ss.updated_at)
    WITH bss, ss
    MATCH (bs:BillSection {id: ss.section_id})
    MERGE (bs)-[:HAS_SUBSECTION]->(bss)
    RETURN count(bss) as created
    """

    result = neo4j_client.run_query(cypher, {"subsections": subsections_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillSubsection nodes")
    return created


def ingest_bill_paragraphs(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill paragraph nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with parts and sections

    Returns:
        Number of paragraphs created
    """
    now = datetime.utcnow().isoformat()
    paragraphs_data = []

    # Collect all paragraphs from all subsections
    all_sections = list(bill.sections)
    for part in bill.parts:
        all_sections.extend(part.sections)

    for section in all_sections:
        for subsection in section.subsections:
            for paragraph in subsection.paragraphs:
                paragraphs_data.append({
                    "id": paragraph.id,
                    "subsection_id": subsection.id,
                    "letter": paragraph.letter,
                    "text_en": paragraph.text_en,
                    "text_fr": paragraph.text_fr,
                    "anchor_id": paragraph.anchor_id,
                    "sequence": paragraph.sequence,
                    "updated_at": now,
                })

    if not paragraphs_data:
        return 0

    # Create BillParagraph nodes
    cypher = """
    UNWIND $paragraphs AS p
    MERGE (bpg:BillParagraph {id: p.id})
    SET bpg.subsection_id = p.subsection_id,
        bpg.letter = p.letter,
        bpg.text_en = p.text_en,
        bpg.text_fr = p.text_fr,
        bpg.anchor_id = p.anchor_id,
        bpg.sequence = p.sequence,
        bpg.updated_at = datetime(p.updated_at)
    WITH bpg, p
    MATCH (bss:BillSubsection {id: p.subsection_id})
    MERGE (bss)-[:HAS_PARAGRAPH]->(bpg)
    RETURN count(bpg) as created
    """

    result = neo4j_client.run_query(cypher, {"paragraphs": paragraphs_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillParagraph nodes")
    return created


def ingest_bill_subparagraphs(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill subparagraph nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with parts and sections

    Returns:
        Number of subparagraphs created
    """
    now = datetime.utcnow().isoformat()
    subparagraphs_data = []

    # Collect all subparagraphs from all paragraphs
    all_sections = list(bill.sections)
    for part in bill.parts:
        all_sections.extend(part.sections)

    for section in all_sections:
        for subsection in section.subsections:
            for paragraph in subsection.paragraphs:
                for subparagraph in paragraph.subparagraphs:
                    subparagraphs_data.append({
                        "id": subparagraph.id,
                        "paragraph_id": paragraph.id,
                        "numeral": subparagraph.numeral,
                        "text_en": subparagraph.text_en,
                        "text_fr": subparagraph.text_fr,
                        "anchor_id": subparagraph.anchor_id,
                        "sequence": subparagraph.sequence,
                        "updated_at": now,
                    })

    if not subparagraphs_data:
        return 0

    # Create BillSubparagraph nodes
    cypher = """
    UNWIND $subparagraphs AS sp
    MERGE (bsp:BillSubparagraph {id: sp.id})
    SET bsp.paragraph_id = sp.paragraph_id,
        bsp.numeral = sp.numeral,
        bsp.text_en = sp.text_en,
        bsp.text_fr = sp.text_fr,
        bsp.anchor_id = sp.anchor_id,
        bsp.sequence = sp.sequence,
        bsp.updated_at = datetime(sp.updated_at)
    WITH bsp, sp
    MATCH (bpg:BillParagraph {id: sp.paragraph_id})
    MERGE (bpg)-[:HAS_SUBPARAGRAPH]->(bsp)
    RETURN count(bsp) as created
    """

    result = neo4j_client.run_query(cypher, {"subparagraphs": subparagraphs_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillSubparagraph nodes")
    return created


def ingest_bill_definitions(
    neo4j_client: Neo4jClient,
    bill: ParsedBill,
) -> int:
    """Ingest bill definition nodes and relationships.

    Args:
        neo4j_client: Neo4j client instance
        bill: Parsed bill with definitions

    Returns:
        Number of definitions created
    """
    if not bill.definitions:
        return 0

    bill_id = f"{bill.session_str}:{bill.bill_number}"
    now = datetime.utcnow().isoformat()

    definitions_data = []
    for i, defn in enumerate(bill.definitions, start=1):
        def_id = f"{bill_id}:def:{i}"
        definitions_data.append({
            "id": def_id,
            "bill_id": bill_id,
            "term_en": defn.term_en,
            "term_fr": defn.term_fr,
            "definition_en": defn.definition_en,
            "definition_fr": defn.definition_fr,
            "sequence": i,
            "updated_at": now,
        })

    # Create BillDefinition nodes
    cypher = """
    UNWIND $definitions AS d
    MERGE (bd:BillDefinition {id: d.id})
    SET bd.bill_id = d.bill_id,
        bd.term_en = d.term_en,
        bd.term_fr = d.term_fr,
        bd.definition_en = d.definition_en,
        bd.definition_fr = d.definition_fr,
        bd.sequence = d.sequence,
        bd.updated_at = datetime(d.updated_at)
    WITH bd, d
    MATCH (b:Bill {id: d.bill_id})
    MERGE (b)-[:HAS_DEFINITION]->(bd)
    RETURN count(bd) as created
    """

    result = neo4j_client.run_query(cypher, {"definitions": definitions_data})
    created = result[0]["created"] if result else 0
    logger.info(f"  ✅ Created {created} BillDefinition nodes")
    return created


def ingest_bill_structure(
    neo4j_client: Neo4jClient,
    parliament: int,
    session: int,
    bill_number: str,
    *,
    version: int = 1,
    is_government: bool = False,
    include_all_versions: bool = True,
) -> Dict[str, int]:
    """Ingest complete bill structure from Parliament.ca XML.

    This is the main entry point for ingesting a single bill's structure.

    Args:
        neo4j_client: Neo4j client instance
        parliament: Parliament number (e.g., 44)
        session: Session number (e.g., 1)
        bill_number: Bill code (e.g., "C-2")
        version: Version number to parse (1=first reading, etc.)
        is_government: True for government bills
        include_all_versions: If True, fetch and store all available versions

    Returns:
        Dictionary with counts for each node type created
    """
    bill_id = f"{parliament}-{session}:{bill_number.upper()}"
    logger.info(f"Ingesting bill structure for {bill_id}...")

    # First check if bill exists in Neo4j
    check_result = neo4j_client.run_query(
        "MATCH (b:Bill {id: $id}) RETURN b.id",
        {"id": f"{parliament}-{session}:{bill_number.upper()}"}
    )

    if not check_result:
        logger.warning(f"  Bill {bill_id} not found in Neo4j, skipping structure ingestion")
        return {"error": f"Bill {bill_id} not found"}

    # Fetch and parse bill with history
    client = BillTextXMLClient()

    try:
        bill = client.parse_bill_with_history(
            parliament=parliament,
            session=session,
            bill_number=bill_number,
            version=version,
            is_government=is_government,
            include_all_versions=include_all_versions,
        )
    except Exception as e:
        logger.error(f"  Failed to fetch/parse bill {bill_id}: {e}")
        return {"error": str(e)}

    results = {
        "bill": bill_id,
        "versions": 0,
        "amendment_events": 0,
        "parts": 0,
        "sections": 0,
        "subsections": 0,
        "paragraphs": 0,
        "subparagraphs": 0,
        "definitions": 0,
    }

    # Ingest all structure components
    results["versions"] = ingest_bill_versions(neo4j_client, bill)
    results["amendment_events"] = ingest_amendment_events(neo4j_client, bill)
    results["parts"] = ingest_bill_parts(neo4j_client, bill)
    results["sections"] = ingest_bill_sections(neo4j_client, bill)
    results["subsections"] = ingest_bill_subsections(neo4j_client, bill)
    results["paragraphs"] = ingest_bill_paragraphs(neo4j_client, bill)
    results["subparagraphs"] = ingest_bill_subparagraphs(neo4j_client, bill)
    results["definitions"] = ingest_bill_definitions(neo4j_client, bill)

    total = sum(v for k, v in results.items() if k != "bill" and k != "error")
    logger.info(f"✅ Ingested {total} total nodes for {bill_id}")

    return results


def ingest_bills_from_list(
    neo4j_client: Neo4jClient,
    bills: List[Tuple[str, str]],
    *,
    default_version: int = 1,
) -> Dict[str, Any]:
    """Ingest multiple bills from a list of (session, bill_number) tuples.

    Args:
        neo4j_client: Neo4j client instance
        bills: List of (session, bill_number) tuples, e.g., [("44-1", "C-2"), ("45-1", "C-234")]
        default_version: Default version to parse if not specified

    Returns:
        Dictionary with overall statistics and per-bill results
    """
    logger.info(f"Ingesting structure for {len(bills)} bills...")

    progress = ProgressTracker(
        total=len(bills),
        desc="Ingesting bill structures",
        unit="bills"
    )

    results = {
        "total_bills": len(bills),
        "successful": 0,
        "failed": 0,
        "totals": {
            "versions": 0,
            "amendment_events": 0,
            "parts": 0,
            "sections": 0,
            "subsections": 0,
            "paragraphs": 0,
            "subparagraphs": 0,
            "definitions": 0,
        },
        "per_bill": [],
    }

    for session_str, bill_number in bills:
        # Parse session string (e.g., "44-1" -> parliament=44, session=1)
        parts = session_str.split("-")
        if len(parts) != 2:
            logger.warning(f"Invalid session format: {session_str}, skipping {bill_number}")
            results["failed"] += 1
            progress.update(1)
            continue

        parliament = int(parts[0])
        session = int(parts[1])

        # Determine if government bill (starts with C- for private member, G- or no prefix for government)
        is_government = bill_number.upper().startswith("G-") or not bill_number.upper().startswith("C-")

        bill_result = ingest_bill_structure(
            neo4j_client,
            parliament=parliament,
            session=session,
            bill_number=bill_number,
            version=default_version,
            is_government=is_government,
        )

        if "error" in bill_result:
            results["failed"] += 1
        else:
            results["successful"] += 1
            for key in results["totals"]:
                results["totals"][key] += bill_result.get(key, 0)

        results["per_bill"].append(bill_result)
        progress.update(1)

    progress.close()

    logger.info("=" * 60)
    logger.info(f"✅ Bill structure ingestion complete:")
    logger.info(f"   Successful: {results['successful']}/{results['total_bills']}")
    logger.info(f"   Failed: {results['failed']}/{results['total_bills']}")
    logger.info(f"   Total nodes created: {sum(results['totals'].values())}")
    logger.info("=" * 60)

    return results


def ingest_all_bills_in_session(
    neo4j_client: Neo4jClient,
    parliament: int,
    session: int,
    *,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Ingest structure for all bills in a parliamentary session.

    Fetches all bills from the session in Neo4j and ingests their structure.

    Args:
        neo4j_client: Neo4j client instance
        parliament: Parliament number (e.g., 44)
        session: Session number (e.g., 1)
        limit: Optional limit on number of bills to process

    Returns:
        Dictionary with overall statistics
    """
    session_str = f"{parliament}-{session}"
    logger.info(f"Fetching all bills from session {session_str}...")

    # Get all bills in this session from Neo4j
    query = """
    MATCH (b:Bill)
    WHERE b.parliament_session = $session_str
    RETURN b.id AS id, b.number AS number
    ORDER BY b.number
    """
    if limit:
        query += f" LIMIT {limit}"

    results = neo4j_client.run_query(query, {"session_str": session_str})

    if not results:
        logger.warning(f"No bills found in session {session_str}")
        return {"error": f"No bills found in session {session_str}"}

    bills = [(session_str, r["number"]) for r in results if r.get("number")]
    logger.info(f"Found {len(bills)} bills in session {session_str}")

    return ingest_bills_from_list(neo4j_client, bills)


def run_bill_structure_ingestion(
    neo4j_client: Neo4jClient,
    *,
    session_str: Optional[str] = None,
    bill_numbers: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Main entry point for bill structure ingestion.

    Can be called with:
    - session_str only: Ingest all bills in that session
    - session_str + bill_numbers: Ingest specific bills in that session
    - bill_numbers only with session in format "44-1:C-2": Ingest specific bills

    Args:
        neo4j_client: Neo4j client instance
        session_str: Parliamentary session (e.g., "44-1")
        bill_numbers: List of bill numbers (e.g., ["C-2", "C-3"])
        limit: Optional limit on number of bills

    Returns:
        Dictionary with results
    """
    logger.info("=" * 60)
    logger.info("BILL STRUCTURE INGESTION")
    logger.info("=" * 60)

    # Create schema
    create_bill_structure_schema(neo4j_client)

    if session_str and bill_numbers:
        # Specific bills in a session
        bills = [(session_str, bn) for bn in bill_numbers]
        return ingest_bills_from_list(neo4j_client, bills)

    elif session_str:
        # All bills in a session
        parts = session_str.split("-")
        if len(parts) != 2:
            return {"error": f"Invalid session format: {session_str}"}
        return ingest_all_bills_in_session(
            neo4j_client,
            parliament=int(parts[0]),
            session=int(parts[1]),
            limit=limit,
        )

    elif bill_numbers:
        # Bill numbers with embedded session (e.g., "44-1:C-2")
        bills = []
        for bn in bill_numbers:
            if ":" in bn:
                sess, num = bn.split(":", 1)
                bills.append((sess, num))
            else:
                logger.warning(f"Bill {bn} missing session, skipping")
        return ingest_bills_from_list(neo4j_client, bills)

    else:
        return {"error": "Must specify session_str and/or bill_numbers"}
