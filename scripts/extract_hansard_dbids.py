#!/usr/bin/env python3
"""
Extract Hansard DbIds and populate MP.hansard_db_id field

This script:
1. Fetches recent Hansard XMLs (covering all current MPs)
2. Extracts DbId + speaker name pairs from Affiliation elements
3. Uses name matching to link DbId → MP nodes
4. Populates MP.hansard_db_id field for future exact matching

This is a ONE-TIME operation to build the DbId→MP mapping.
Future Hansard imports will use exact hansard_db_id matching.
"""

import sys
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Set, List, Tuple
from collections import defaultdict

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'packages' / 'fedmcp' / 'src'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient
from fedmcp_pipeline.utils.progress import logger
from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.ingest.hansard import normalize_name, NICKNAME_MAPPING


def fetch_recent_hansard_xmls(limit: int = 50) -> List[Tuple[str, str]]:
    """
    Fetch recent Hansard XMLs to extract DbIds.

    Args:
        limit: Number of recent sittings to fetch

    Returns:
        List of (sitting_number, xml_text) tuples
    """
    logger.info(f"Fetching {limit} recent Hansard XMLs...")

    xmls = []
    sitting_num = 60  # Start from recent sitting

    for _ in range(limit):
        sitting_str = str(sitting_num).zfill(3)
        xml_url = f"https://www.ourcommons.ca/Content/House/451/Debates/{sitting_str}/HAN{sitting_str}-E.XML"

        try:
            response = requests.get(xml_url, headers={"Accept": "application/xml"}, timeout=30)
            if response.status_code == 200:
                xml_text = response.content.decode('utf-8-sig')
                xmls.append((sitting_str, xml_text))
                logger.info(f"  ✓ Fetched sitting {sitting_str}")
            else:
                logger.debug(f"  ✗ Sitting {sitting_str} not available (HTTP {response.status_code})")
        except Exception as e:
            logger.warning(f"  ✗ Error fetching sitting {sitting_str}: {e}")

        sitting_num -= 1
        if sitting_num < 1:
            break

    logger.info(f"Successfully fetched {len(xmls)} Hansard XMLs")
    return xmls


def extract_dbid_name_pairs(xmls: List[Tuple[str, str]]) -> Dict[int, Set[str]]:
    """
    Extract DbId → speaker names mapping from Hansard XMLs.

    Args:
        xmls: List of (sitting_number, xml_text) tuples

    Returns:
        Dict mapping DbId to set of speaker name variants
    """
    logger.info("Extracting DbId → name mappings from XMLs...")

    client = OurCommonsHansardClient()
    dbid_to_names: Dict[int, Set[str]] = defaultdict(set)

    for sitting_num, xml_text in xmls:
        try:
            sitting = client.parse_sitting(xml_text, source_url=f"sitting-{sitting_num}")

            for section in sitting.sections:
                for speech in section.speeches:
                    if speech.person_db_id and speech.speaker_name:
                        dbid_to_names[speech.person_db_id].add(speech.speaker_name)

        except Exception as e:
            logger.warning(f"Error parsing sitting {sitting_num}: {e}")
            continue

    logger.info(f"Extracted {len(dbid_to_names)} unique DbIds with name variants")
    return dbid_to_names


def strip_honorifics(name: str) -> str:
    """Remove honorifics from names."""
    honorifics = ['Hon.', 'Right Hon.', 'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Miss']
    for honorific in honorifics:
        if name.startswith(honorific + ' '):
            name = name[len(honorific):].strip()
    return name


def remove_middle_names(name: str) -> str:
    """
    Remove middle names/initials from a full name.
    Keeps only first name and last name.

    Examples:
        "Amanpreet S. Gill" -> "Amanpreet Gill"
        "Jasraj Singh Hallan" -> "Jasraj Hallan"
        "Rhéal Éloi Fortin" -> "Rhéal Fortin"
    """
    parts = name.split()
    if len(parts) <= 2:
        # Already first + last only
        return name

    # Keep first and last parts only
    return f"{parts[0]} {parts[-1]}"


def match_dbids_to_mps(neo4j: Neo4jClient, dbid_to_names: Dict[int, Set[str]]) -> Dict[int, str]:
    """
    Match DbIds to MP nodes using name matching.

    Args:
        neo4j: Neo4j client
        dbid_to_names: Mapping of DbId to speaker name variants

    Returns:
        Dict mapping DbId to MP.id
    """
    logger.info("Matching DbIds to MP nodes using name matching...")

    # Fetch all MP names from database
    result = neo4j.run_query("""
        MATCH (mp:MP)
        RETURN mp.id as mp_id, mp.name as name, mp.given_name as given_name, mp.family_name as family_name
    """)

    mps = {}
    for row in result:
        mp_id = row['mp_id']
        name = row['name']
        normalized = normalize_name(name)
        mps[mp_id] = {
            'name': name,
            'normalized': normalized,
            'normalized_no_middle': remove_middle_names(normalized),
            'given_name': row.get('given_name', ''),
            'family_name': row.get('family_name', '')
        }

    logger.info(f"Loaded {len(mps)} MPs from database")

    # Match DbIds to MPs
    dbid_to_mp: Dict[int, str] = {}
    unmatched_dbids: List[Tuple[int, str]] = []

    for db_id, name_variants in dbid_to_names.items():
        matched = False

        for speaker_name in name_variants:
            # Strip honorifics BEFORE normalizing
            speaker_name_clean = strip_honorifics(speaker_name)
            normalized_speaker = normalize_name(speaker_name_clean)

            # Try exact normalized name match
            for mp_id, mp_data in mps.items():
                if mp_data['normalized'] == normalized_speaker:
                    dbid_to_mp[db_id] = mp_id
                    matched = True
                    break

            if matched:
                break

            # Try family name match + nickname matching
            speaker_parts = normalized_speaker.split()
            if len(speaker_parts) >= 2:
                speaker_family = speaker_parts[-1]
                speaker_given = ' '.join(speaker_parts[:-1])

                for mp_id, mp_data in mps.items():
                    mp_family = normalize_name(mp_data.get('family_name', ''))
                    mp_given = normalize_name(mp_data.get('given_name', ''))

                    if mp_family == speaker_family:
                        # Check if given names match via nicknames
                        if mp_given == speaker_given:
                            dbid_to_mp[db_id] = mp_id
                            matched = True
                            break

                        # Check nickname mapping
                        for nickname, full_name in NICKNAME_MAPPING.items():
                            if (normalize_name(nickname) == speaker_given and
                                normalize_name(full_name) == mp_given):
                                dbid_to_mp[db_id] = mp_id
                                matched = True
                                break
                            if (normalize_name(full_name) == speaker_given and
                                normalize_name(nickname) == mp_given):
                                dbid_to_mp[db_id] = mp_id
                                matched = True
                                break

                    if matched:
                        break

            if matched:
                break

            # Try removing middle names as a fallback
            # This handles cases like "Jasraj Singh Hallan" vs "Jasraj Hallan"
            # or "Amanpreet S. Gill" vs "Amanpreet Gill"
            speaker_no_middle = remove_middle_names(normalized_speaker)

            for mp_id, mp_data in mps.items():
                if mp_data['normalized_no_middle'] == speaker_no_middle:
                    dbid_to_mp[db_id] = mp_id
                    matched = True
                    logger.debug(f"  Matched via middle name removal: {speaker_name} -> {mp_data['name']}")
                    break

            if matched:
                break

            # Try prefix matching as a fallback
            # This handles cases like "Michelle Rempel" vs "Michelle Rempel Garner" (married name)
            # where one name is a prefix of the other
            for mp_id, mp_data in mps.items():
                mp_normalized = mp_data['normalized']
                # Check if one is a prefix of the other
                if (normalized_speaker.startswith(mp_normalized + ' ') or
                    mp_normalized.startswith(normalized_speaker + ' ')):
                    dbid_to_mp[db_id] = mp_id
                    matched = True
                    logger.debug(f"  Matched via name prefix: {speaker_name} -> {mp_data['name']}")
                    break

            if matched:
                break

        if not matched:
            # Use the first (most common) name variant for logging
            unmatched_dbids.append((db_id, list(name_variants)[0]))

    logger.success(f"✓ Matched {len(dbid_to_mp)} DbIds to MPs ({len(dbid_to_mp)/len(dbid_to_names)*100:.1f}%)")

    if unmatched_dbids:
        logger.warning(f"✗ Could not match {len(unmatched_dbids)} DbIds:")
        for db_id, name in sorted(unmatched_dbids, key=lambda x: x[1])[:20]:
            logger.warning(f"  DbId={db_id}: {name}")
        if len(unmatched_dbids) > 20:
            logger.warning(f"  ... and {len(unmatched_dbids) - 20} more")

    return dbid_to_mp


def populate_hansard_db_ids(neo4j: Neo4jClient, dbid_to_mp: Dict[int, str]) -> int:
    """
    Populate MP.hansard_db_id field in Neo4j.

    Args:
        neo4j: Neo4j client
        dbid_to_mp: Mapping of DbId to MP.id

    Returns:
        Number of MPs updated
    """
    logger.info("Populating MP.hansard_db_id field in Neo4j...")

    # Build update query
    updates = [{"mp_id": mp_id, "hansard_db_id": db_id} for db_id, mp_id in dbid_to_mp.items()]

    query = """
    UNWIND $updates AS update
    MATCH (mp:MP {id: update.mp_id})
    SET mp.hansard_db_id = update.hansard_db_id
    RETURN count(*) as updated_count
    """

    result = neo4j.run_query(query, {"updates": updates})
    updated_count = result[0]['updated_count'] if result else 0

    logger.success(f"✓ Updated {updated_count} MP nodes with hansard_db_id")
    return updated_count


def main():
    """Main entry point."""
    logger.info("=" * 80)
    logger.info("HANSARD DB_ID EXTRACTION AND MAPPING")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    print()

    # Get Neo4j connection from environment
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://10.128.0.3:7687')
    neo4j_user = os.getenv('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD')

    if not neo4j_password:
        logger.error("NEO4J_PASSWORD environment variable not set")
        sys.exit(1)

    neo4j = Neo4jClient(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)

    try:
        # Step 1: Fetch recent Hansard XMLs
        xmls = fetch_recent_hansard_xmls(limit=50)
        if not xmls:
            logger.error("No Hansard XMLs could be fetched")
            sys.exit(1)

        # Step 2: Extract DbId → name mappings
        dbid_to_names = extract_dbid_name_pairs(xmls)
        if not dbid_to_names:
            logger.error("No DbIds extracted from XMLs")
            sys.exit(1)

        # Step 3: Match DbIds to MPs
        dbid_to_mp = match_dbids_to_mps(neo4j, dbid_to_names)
        if not dbid_to_mp:
            logger.error("No DbIds could be matched to MPs")
            sys.exit(1)

        # Step 4: Populate hansard_db_id field
        updated_count = populate_hansard_db_ids(neo4j, dbid_to_mp)

        logger.info("=" * 80)
        logger.success(f"✅ Successfully populated hansard_db_id for {updated_count} MPs")
        logger.info(f"Match rate: {updated_count/len(dbid_to_names)*100:.1f}% of DbIds in XMLs")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        neo4j.close()


if __name__ == "__main__":
    main()
