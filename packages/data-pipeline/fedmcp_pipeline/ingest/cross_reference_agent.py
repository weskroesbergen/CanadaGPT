"""Cross-reference agent for extracting entity mentions from parliamentary text.

This module extracts references to bills, MPs, committees, petitions, and other
parliamentary entities from Hansard statements and committee testimony.

Entity Patterns:
- Bills: "Bill C-234", "C-234", "S-12", "Senate Bill S-12"
- MPs: "the member for Carleton", "Mr. Poilievre", "the hon. member"
- Committees: "the finance committee", "FINA", "Standing Committee on Finance"
- Petitions: "e-petition 4823", "petition e-4823", "paper petition 451-00231"
- Votes: "Vote No. 234", "recorded division No. 234"

Relationship Types Created:
- (Statement)-[:MENTIONS]->(Bill) - with debate_stage property
- (Statement)-[:MENTIONS]->(MP) - when referencing another member
- (Statement)-[:MENTIONS]->(Committee)
- (Statement)-[:MENTIONS]->(Petition)

Usage:
    >>> from fedmcp_pipeline.ingest.cross_reference_agent import CrossReferenceAgent
    >>> agent = CrossReferenceAgent(neo4j_client)
    >>>
    >>> # Extract mentions from a statement
    >>> mentions = agent.extract_mentions(statement_text, statement_id)
    >>>
    >>> # Create relationships in Neo4j
    >>> agent.create_mention_relationships(statement_id, mentions)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger


class EntityType(Enum):
    """Types of entities that can be mentioned in parliamentary text."""
    BILL = "bill"
    MP = "mp"
    COMMITTEE = "committee"
    PETITION = "petition"
    VOTE = "vote"
    RIDING = "riding"


@dataclass
class EntityMention:
    """A mention of an entity in parliamentary text."""
    entity_type: EntityType
    raw_text: str  # Original text that matched
    normalized_id: Optional[str] = None  # Neo4j node ID if resolved
    confidence: float = 1.0  # Confidence score (0-1)
    position: int = 0  # Character position in text
    context: str = ""  # Surrounding context
    properties: Dict[str, Any] = field(default_factory=dict)  # Extra metadata


class CrossReferenceAgent:
    """Extract entity mentions from parliamentary text and create Neo4j relationships.

    The agent uses regex patterns to identify mentions of parliamentary entities
    in statement text, then attempts to resolve them to actual Neo4j nodes.
    """

    # Bill patterns
    BILL_PATTERNS = [
        # "Bill C-234", "Bill S-12", "Government Bill C-2"
        (r'\b(?:Government\s+|Private\s+(?:Member\'?s?\s+)?)?Bill\s+([CS])-?(\d+)\b', 1.0),
        # "C-234", "S-12" (standalone)
        (r'\b([CS])-(\d+)\b', 0.9),
        # "the bill" referring to context (lower confidence)
        (r'\bthe\s+bill\b', 0.5),
    ]

    # MP patterns
    MP_PATTERNS = [
        # "the member for Carleton", "the hon. member for Toronto Centre"
        # Riding names: capitalized words (possibly hyphenated), max 4 words, ending before common stopwords
        (r'\bthe\s+(?:hon(?:ourable|\.)\s+)?member\s+for\s+([A-Z][a-zéèêëîïôùûüç\-\']+(?:[\s\—\-][A-Z][a-zéèêëîïôùûüç\-\']+){0,3})(?=\s+(?:has|is|was|will|would|should|could|can|may|might|must|who|that|which|and|or|but|for|to|in|on|at|,|\.|\?|!|;|:|\n|$))', 0.95),
        # "Mr./Ms./Mrs. Poilievre", "Hon. Chrystia Freeland"
        (r'\b(?:Hon(?:ourable|\.)\s+|Right\s+Hon(?:ourable|\.)\s+)?(?:Mr|Ms|Mrs|Miss)\.?\s+([A-Z][a-zéèêëîïôùûüç\-\']+)', 0.85),
        # "the minister", "the Prime Minister" (need context)
        (r'\bthe\s+(?:(?:Deputy\s+)?Prime\s+)?Minister(?:\s+of\s+[A-Z][a-z\s]+)?', 0.7),
        # "my colleague", "the parliamentary secretary"
        (r'\b(?:my\s+colleague|the\s+parliamentary\s+secretary)', 0.5),
    ]

    # Committee patterns
    COMMITTEE_PATTERNS = [
        # Full name: "Standing Committee on Finance"
        (r'\b(?:Standing|Special|Legislative|Joint)\s+Committee\s+on\s+([A-Z][a-z]+(?:\s+[A-Za-z]+)*)', 0.95),
        # Acronym: "FINA", "ENVI", "ETHI"
        (r'\b(FINA|ENVI|ETHI|HUMA|TRAN|NDDN|JUST|CHPC|SECU|AGRI|INAN|INDU|RNNR|SRSR|PROC|OGGO|FAAE|CIMM|HEAL|FEWO|ACVA|LANG)\b', 0.95),
        # "the committee", "this committee" (context-dependent)
        (r'\bthe\s+committee\b', 0.4),
    ]

    # Petition patterns
    PETITION_PATTERNS = [
        # "e-petition 4823", "e-4823"
        (r'\be-?petition\s+(?:no\.?\s*)?(\d+)', 0.95),
        (r'\be-(\d+)\b', 0.85),
        # Paper petition: "petition 451-00231"
        (r'\bpetition\s+(\d{3}-\d{5})', 0.95),
    ]

    # Vote patterns
    VOTE_PATTERNS = [
        # "Vote No. 234", "recorded division No. 123"
        (r'\b(?:Vote|recorded\s+division)\s+(?:No\.?\s*)?(\d+)', 0.9),
    ]

    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        *,
        resolve_entities: bool = True,
        min_confidence: float = 0.5,
    ):
        """Initialize the cross-reference agent.

        Args:
            neo4j_client: Neo4j client for entity resolution and relationship creation
            resolve_entities: If True, attempt to resolve mentions to Neo4j nodes
            min_confidence: Minimum confidence threshold for mentions
        """
        self.neo4j = neo4j_client
        self.resolve_entities = resolve_entities
        self.min_confidence = min_confidence

        # Caches for entity resolution
        self._bill_cache: Dict[str, str] = {}  # "C-234" -> "45-1:C-234"
        self._mp_cache: Dict[str, str] = {}  # "Poilievre" -> MP node ID
        self._committee_cache: Dict[str, str] = {}  # "FINA" -> Committee node ID
        self._petition_cache: Dict[str, str] = {}  # "e-4823" -> Petition node ID

    def extract_mentions(
        self,
        text: str,
        statement_id: Optional[str] = None,
        *,
        context_window: int = 50,
    ) -> List[EntityMention]:
        """Extract all entity mentions from text.

        Args:
            text: The text to analyze (statement content, testimony, etc.)
            statement_id: Optional statement ID for logging/context
            context_window: Characters of context to capture around each mention

        Returns:
            List of EntityMention objects
        """
        mentions = []

        if not text:
            return mentions

        # Extract each entity type
        mentions.extend(self._extract_bills(text, context_window))
        mentions.extend(self._extract_mps(text, context_window))
        mentions.extend(self._extract_committees(text, context_window))
        mentions.extend(self._extract_petitions(text, context_window))
        mentions.extend(self._extract_votes(text, context_window))

        # Filter by confidence threshold
        mentions = [m for m in mentions if m.confidence >= self.min_confidence]

        # Sort by position in text
        mentions.sort(key=lambda m: m.position)

        # Resolve to Neo4j nodes if enabled
        if self.resolve_entities and self.neo4j:
            for mention in mentions:
                self._resolve_mention(mention)

        return mentions

    def _extract_bills(self, text: str, context_window: int) -> List[EntityMention]:
        """Extract bill mentions from text."""
        mentions = []

        for pattern, base_confidence in self.BILL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Extract bill number
                if match.lastindex and match.lastindex >= 2:
                    chamber = match.group(1).upper()
                    number = match.group(2)
                    bill_code = f"{chamber}-{number}"
                else:
                    bill_code = None

                # Get context
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]

                mentions.append(EntityMention(
                    entity_type=EntityType.BILL,
                    raw_text=match.group(0),
                    confidence=base_confidence,
                    position=match.start(),
                    context=context,
                    properties={"bill_code": bill_code} if bill_code else {},
                ))

        return mentions

    def _extract_mps(self, text: str, context_window: int) -> List[EntityMention]:
        """Extract MP mentions from text."""
        mentions = []

        for pattern, base_confidence in self.MP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get captured group (riding or name)
                captured = match.group(1) if match.lastindex else None

                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]

                mentions.append(EntityMention(
                    entity_type=EntityType.MP,
                    raw_text=match.group(0),
                    confidence=base_confidence,
                    position=match.start(),
                    context=context,
                    properties={
                        "riding": captured if "member for" in match.group(0).lower() else None,
                        "name": captured if captured and "member for" not in match.group(0).lower() else None,
                    },
                ))

        return mentions

    def _extract_committees(self, text: str, context_window: int) -> List[EntityMention]:
        """Extract committee mentions from text."""
        mentions = []

        for pattern, base_confidence in self.COMMITTEE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                captured = match.group(1) if match.lastindex else None

                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]

                mentions.append(EntityMention(
                    entity_type=EntityType.COMMITTEE,
                    raw_text=match.group(0),
                    confidence=base_confidence,
                    position=match.start(),
                    context=context,
                    properties={
                        "code": captured if captured and captured.isupper() else None,
                        "name": captured if captured and not captured.isupper() else None,
                    },
                ))

        return mentions

    def _extract_petitions(self, text: str, context_window: int) -> List[EntityMention]:
        """Extract petition mentions from text."""
        mentions = []

        for pattern, base_confidence in self.PETITION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                petition_number = match.group(1) if match.lastindex else None

                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]

                # Determine petition type
                is_epetition = "e-" in match.group(0).lower() or (
                    petition_number and not "-" in petition_number
                )

                mentions.append(EntityMention(
                    entity_type=EntityType.PETITION,
                    raw_text=match.group(0),
                    confidence=base_confidence,
                    position=match.start(),
                    context=context,
                    properties={
                        "petition_number": petition_number,
                        "type": "electronic" if is_epetition else "paper",
                    },
                ))

        return mentions

    def _extract_votes(self, text: str, context_window: int) -> List[EntityMention]:
        """Extract vote mentions from text."""
        mentions = []

        for pattern, base_confidence in self.VOTE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                vote_number = match.group(1) if match.lastindex else None

                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]

                mentions.append(EntityMention(
                    entity_type=EntityType.VOTE,
                    raw_text=match.group(0),
                    confidence=base_confidence,
                    position=match.start(),
                    context=context,
                    properties={"vote_number": vote_number},
                ))

        return mentions

    def _resolve_mention(self, mention: EntityMention) -> None:
        """Attempt to resolve a mention to a Neo4j node ID."""
        if not self.neo4j:
            return

        if mention.entity_type == EntityType.BILL:
            self._resolve_bill(mention)
        elif mention.entity_type == EntityType.MP:
            self._resolve_mp(mention)
        elif mention.entity_type == EntityType.COMMITTEE:
            self._resolve_committee(mention)
        elif mention.entity_type == EntityType.PETITION:
            self._resolve_petition(mention)

    def _resolve_bill(self, mention: EntityMention) -> None:
        """Resolve a bill mention to Neo4j node."""
        bill_code = mention.properties.get("bill_code")
        if not bill_code:
            return

        # Check cache
        if bill_code in self._bill_cache:
            mention.normalized_id = self._bill_cache[bill_code]
            return

        # Query Neo4j for current session bills matching this code
        result = self.neo4j.run_query("""
            MATCH (b:Bill)
            WHERE b.number = $code
            RETURN b.id AS id
            ORDER BY b.parliament_session DESC
            LIMIT 1
        """, {"code": bill_code})

        if result:
            mention.normalized_id = result[0]["id"]
            self._bill_cache[bill_code] = mention.normalized_id

    def _resolve_mp(self, mention: EntityMention) -> None:
        """Resolve an MP mention to Neo4j node."""
        riding = mention.properties.get("riding")
        name = mention.properties.get("name")

        if riding:
            # Check cache
            cache_key = f"riding:{riding}"
            if cache_key in self._mp_cache:
                mention.normalized_id = self._mp_cache[cache_key]
                return

            # Query by riding
            result = self.neo4j.run_query("""
                MATCH (m:MP)-[:REPRESENTS]->(r:Riding)
                WHERE toLower(r.name) CONTAINS toLower($riding)
                AND m.is_current = true
                RETURN m.id AS id
                LIMIT 1
            """, {"riding": riding})

            if result:
                mention.normalized_id = result[0]["id"]
                self._mp_cache[cache_key] = mention.normalized_id

        elif name:
            # Check cache
            cache_key = f"name:{name}"
            if cache_key in self._mp_cache:
                mention.normalized_id = self._mp_cache[cache_key]
                return

            # Query by last name (fuzzy)
            result = self.neo4j.run_query("""
                MATCH (m:MP)
                WHERE toLower(m.name) CONTAINS toLower($name)
                AND m.is_current = true
                RETURN m.id AS id
                LIMIT 1
            """, {"name": name})

            if result:
                mention.normalized_id = result[0]["id"]
                self._mp_cache[cache_key] = mention.normalized_id

    def _resolve_committee(self, mention: EntityMention) -> None:
        """Resolve a committee mention to Neo4j node."""
        code = mention.properties.get("code")
        name = mention.properties.get("name")

        if code:
            cache_key = f"code:{code}"
            if cache_key in self._committee_cache:
                mention.normalized_id = self._committee_cache[cache_key]
                return

            result = self.neo4j.run_query("""
                MATCH (c:Committee {code: $code})
                RETURN c.code AS id
                LIMIT 1
            """, {"code": code})

            if result:
                mention.normalized_id = result[0]["id"]
                self._committee_cache[cache_key] = mention.normalized_id

        elif name:
            cache_key = f"name:{name}"
            if cache_key in self._committee_cache:
                mention.normalized_id = self._committee_cache[cache_key]
                return

            result = self.neo4j.run_query("""
                MATCH (c:Committee)
                WHERE toLower(c.name) CONTAINS toLower($name)
                RETURN c.code AS id
                LIMIT 1
            """, {"name": name})

            if result:
                mention.normalized_id = result[0]["id"]
                self._committee_cache[cache_key] = mention.normalized_id

    def _resolve_petition(self, mention: EntityMention) -> None:
        """Resolve a petition mention to Neo4j node."""
        petition_number = mention.properties.get("petition_number")
        if not petition_number:
            return

        cache_key = petition_number
        if cache_key in self._petition_cache:
            mention.normalized_id = self._petition_cache[cache_key]
            return

        # Format petition number for query
        if "-" in petition_number:
            # Paper petition: "451-00231"
            query_number = petition_number
        else:
            # E-petition: "4823" -> "e-4823"
            query_number = f"e-{petition_number}"

        result = self.neo4j.run_query("""
            MATCH (p:Petition)
            WHERE p.number = $number OR p.number = $alt_number
            RETURN p.number AS id
            LIMIT 1
        """, {"number": query_number, "alt_number": petition_number})

        if result:
            mention.normalized_id = result[0]["id"]
            self._petition_cache[cache_key] = mention.normalized_id

    def create_mention_relationships(
        self,
        source_id: str,
        source_label: str,
        mentions: List[EntityMention],
        *,
        properties: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Create MENTIONS relationships in Neo4j for resolved mentions.

        Args:
            source_id: ID of the source node (Statement, CommitteeTestimony)
            source_label: Label of source node ("Statement", "CommitteeTestimony")
            mentions: List of EntityMention objects (only resolved ones will be used)
            properties: Additional properties for all relationships

        Returns:
            Number of relationships created
        """
        if not self.neo4j:
            return 0

        created = 0
        props = properties or {}

        for mention in mentions:
            if not mention.normalized_id:
                continue

            # Determine target label
            target_label = {
                EntityType.BILL: "Bill",
                EntityType.MP: "MP",
                EntityType.COMMITTEE: "Committee",
                EntityType.PETITION: "Petition",
                EntityType.VOTE: "Vote",
            }.get(mention.entity_type)

            if not target_label:
                continue

            # Build relationship properties
            rel_props = {
                "confidence": mention.confidence,
                "raw_text": mention.raw_text,
                "position": mention.position,
                **props,
            }

            # Add entity-specific properties
            if mention.entity_type == EntityType.BILL and mention.properties.get("bill_code"):
                rel_props["bill_code"] = mention.properties["bill_code"]

            try:
                result = self.neo4j.run_query(f"""
                    MATCH (src:{source_label} {{id: $source_id}})
                    MATCH (tgt:{target_label} {{id: $target_id}})
                    MERGE (src)-[r:MENTIONS]->(tgt)
                    SET r += $props
                    RETURN count(r) AS created
                """, {
                    "source_id": source_id,
                    "target_id": mention.normalized_id,
                    "props": rel_props,
                })

                if result and result[0]["created"]:
                    created += 1

            except Exception as e:
                logger.warning(f"Failed to create MENTIONS relationship: {e}")

        return created

    def process_statement(
        self,
        statement_id: str,
        content: str,
        *,
        debate_stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a statement to extract mentions and create relationships.

        This is the main entry point for processing individual statements.

        Args:
            statement_id: Neo4j Statement node ID
            content: Statement text content
            debate_stage: Optional debate stage for bill mentions ("1", "2", "3")

        Returns:
            Dictionary with processing results
        """
        # Extract mentions
        mentions = self.extract_mentions(content, statement_id)

        # Count by type
        type_counts = {}
        resolved_counts = {}
        for mention in mentions:
            type_name = mention.entity_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            if mention.normalized_id:
                resolved_counts[type_name] = resolved_counts.get(type_name, 0) + 1

        # Create relationships
        properties = {"debate_stage": debate_stage} if debate_stage else {}
        relationships_created = self.create_mention_relationships(
            statement_id,
            "Statement",
            mentions,
            properties=properties,
        )

        return {
            "statement_id": statement_id,
            "total_mentions": len(mentions),
            "type_counts": type_counts,
            "resolved_counts": resolved_counts,
            "relationships_created": relationships_created,
        }

    def clear_caches(self) -> None:
        """Clear all entity resolution caches."""
        self._bill_cache.clear()
        self._mp_cache.clear()
        self._committee_cache.clear()
        self._petition_cache.clear()


def extract_mentions_from_text(
    text: str,
    *,
    min_confidence: float = 0.5,
) -> List[EntityMention]:
    """Convenience function to extract mentions without Neo4j.

    Args:
        text: Text to analyze
        min_confidence: Minimum confidence threshold

    Returns:
        List of EntityMention objects (unresolved)
    """
    agent = CrossReferenceAgent(
        neo4j_client=None,
        resolve_entities=False,
        min_confidence=min_confidence,
    )
    return agent.extract_mentions(text)
