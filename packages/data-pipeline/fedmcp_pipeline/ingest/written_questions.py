"""Written Questions ingestion from OurCommons to Neo4j."""

import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add fedmcp package to path
FEDMCP_PATH = Path(__file__).parent.parent.parent.parent / "fedmcp" / "src"
sys.path.insert(0, str(FEDMCP_PATH))

from fedmcp.clients.written_questions import WrittenQuestionsClient, WrittenQuestion
from ..utils.neo4j_client import Neo4jClient
from ..utils.progress import logger


# Nickname mapping for MP name matching
NICKNAME_MAPPING = {
    'bobby': 'robert',
    'rob': 'robert',
    'bob': 'robert',
    'bill': 'william',
    'dick': 'richard',
    'jim': 'james',
    'joe': 'joseph',
    'mike': 'michael',
    'tony': 'anthony',
    'shuv': 'shuvaloy',
    'ed': 'edward',
    'dan': 'daniel',
    'dave': 'david',
    'tom': 'thomas',
    'chris': 'christopher',
    'nick': 'nicholas',
    'matt': 'matthew',
    'pat': 'patrick',
    'tim': 'timothy',
    'steve': 'stephen',
    'rick': 'richard',
}


def normalize_name(name: str) -> str:
    """
    Normalize a name for fuzzy matching by:
    - Removing accents/diacritics
    - Converting to lowercase
    - Removing extra whitespace
    - Removing punctuation
    """
    if not name:
        return ""

    # Remove accents: é → e, è → e, ñ → n, etc.
    name = ''.join(
        char for char in unicodedata.normalize('NFD', name)
        if unicodedata.category(char) != 'Mn'
    )

    # Remove periods, commas
    name = name.replace('.', '').replace(',', '')

    # Convert to lowercase and strip whitespace
    name = name.lower().strip()

    # Normalize whitespace
    name = ' '.join(name.split())

    return name


def build_mp_mapping(neo4j_client: Neo4jClient) -> Dict[str, str]:
    """Build MP name -> ID mapping with variations for fuzzy matching."""
    mp_mapping = {}

    mp_query = """
        MATCH (m:MP)
        RETURN m.id AS id, m.name AS name,
               m.given_name AS given_name, m.family_name AS family_name,
               m.current_riding AS riding
    """
    mps = neo4j_client.run_query(mp_query)

    for mp in mps:
        mp_id = mp['id']
        name = mp.get('name', '')
        given = mp.get('given_name', '')
        family = mp.get('family_name', '')

        # Store by full name (normalized)
        if name:
            mp_mapping[normalize_name(name)] = mp_id

        # Store by "FirstName LastName" format (normalized)
        if given and family:
            normalized_full = normalize_name(f"{given} {family}")
            mp_mapping[normalized_full] = mp_id

            # Store core name without middle names/initials
            first_only = given.split()[0] if given else ""
            core_name = normalize_name(f"{first_only} {family}")
            if core_name:
                mp_mapping[core_name] = mp_id

            # Store with nickname variations
            first_normalized = normalize_name(first_only)
            if first_normalized in NICKNAME_MAPPING:
                formal_name = normalize_name(f"{NICKNAME_MAPPING[first_normalized]} {family}")
                mp_mapping[formal_name] = mp_id

        # For compound last names, also store with just the first part
        if given and family and " " in family:
            first_family = family.split()[0]
            mp_mapping[normalize_name(f"{given} {first_family}")] = mp_id

        # For hyphenated last names, also store first part only
        if given and family and "-" in family:
            first_part = family.split('-')[0]
            mp_mapping[normalize_name(f"{given} {first_part}")] = mp_id
            mp_mapping[normalize_name(f"{given.split()[0]} {first_part}")] = mp_id

    return mp_mapping


def match_mp_name(name: str, mp_mapping: Dict[str, str]) -> Optional[str]:
    """Match speaker name to MP ID using fuzzy matching."""
    if not name:
        return None

    normalized = normalize_name(name)

    # Direct match
    mp_id = mp_mapping.get(normalized)
    if mp_id:
        return mp_id

    # Try variations
    if " " in normalized:
        parts = normalized.split()

        # Try: first name + last name (skip middle names)
        if len(parts) >= 2:
            first_last = f"{parts[0]} {parts[-1]}"
            mp_id = mp_mapping.get(first_last)
            if mp_id:
                return mp_id

        # Try: first + second word (for compound last names)
        if len(parts) >= 2:
            first_second = f"{parts[0]} {parts[1]}"
            mp_id = mp_mapping.get(first_second)
            if mp_id:
                return mp_id

        # Try nickname variations
        if len(parts) >= 2:
            first_name_norm = parts[0]
            # Check if first name is a formal name, try nickname
            for nickname, formal in NICKNAME_MAPPING.items():
                if first_name_norm == formal:
                    nickname_version = f"{nickname} {parts[-1]}"
                    mp_id = mp_mapping.get(nickname_version)
                    if mp_id:
                        return mp_id
            # Check if first name is a nickname, try formal
            if first_name_norm in NICKNAME_MAPPING:
                formal_version = f"{NICKNAME_MAPPING[first_name_norm]} {parts[-1]}"
                mp_id = mp_mapping.get(formal_version)
                if mp_id:
                    return mp_id

    return None


def ingest_written_questions(
    neo4j_client: Neo4jClient,
    parliament_session: str = "45-1",
    batch_size: int = 100,
    full_refresh: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, int]:
    """
    Ingest Written Questions metadata from OurCommons.

    Args:
        neo4j_client: Neo4j client
        parliament_session: Session to import (e.g., "45-1")
        batch_size: Batch size for Neo4j operations
        full_refresh: If True, re-import all; if False, only new questions
        limit: Maximum number of questions to import (for testing)

    Returns:
        Dict with counts of created/updated entities
    """
    logger.info("=" * 60)
    logger.info(f"WRITTEN QUESTIONS INGESTION - Session {parliament_session}")
    logger.info("=" * 60)

    stats = {
        'questions_scraped': 0,
        'questions_created': 0,
        'asked_by_links': 0,
        'unmatched_mps': 0,
    }

    client = WrittenQuestionsClient()

    # 1. Get existing question numbers if doing incremental
    existing_numbers = set()
    if not full_refresh:
        existing_query = """
            MATCH (wq:WrittenQuestion {session_id: $session_id})
            RETURN wq.question_number as number
        """
        existing = neo4j_client.run_query(existing_query, {"session_id": parliament_session})
        existing_numbers = {r['number'] for r in existing}
        logger.info(f"Found {len(existing_numbers)} existing questions in database")

    # 2. Fetch questions from OurCommons
    logger.info("Fetching written questions from OurCommons...")
    try:
        raw_questions = client.list_questions(
            parliament_session=parliament_session,
            limit=limit
        )
        stats['questions_scraped'] = len(raw_questions)
        logger.info(f"Scraped {len(raw_questions)} raw questions from OurCommons")
    except Exception as e:
        logger.error(f"Failed to fetch questions: {e}")
        return stats

    # 2b. Deduplicate questions by question_number
    # The scraper returns multiple links per question; prefer ones with asker_name
    question_map: Dict[str, Any] = {}
    for q in raw_questions:
        q_num = q.question_number
        if q_num not in question_map:
            question_map[q_num] = q
        elif q.asker_name and not question_map[q_num].asker_name:
            # Prefer question with asker_name populated
            question_map[q_num] = q
        elif q.status and not question_map[q_num].status:
            # Prefer question with status populated
            question_map[q_num] = q

    all_questions = list(question_map.values())
    logger.info(f"Deduplicated to {len(all_questions)} unique questions")

    # 3. Filter to new questions
    if not full_refresh:
        new_questions = [
            q for q in all_questions
            if q.question_number not in existing_numbers
        ]
        logger.info(f"  {len(new_questions)} are new, {len(existing_numbers)} already exist")
    else:
        new_questions = all_questions
        logger.info(f"Full refresh: importing all {len(new_questions)} questions")

    if not new_questions:
        logger.info("No new questions to import")
        return stats

    # 4. Fetch detailed data for new questions to get question_text
    logger.info(f"Fetching detailed data for {len(new_questions)} questions...")
    detailed_questions = []
    for i, q in enumerate(new_questions):
        try:
            # Extract question number for detail fetch
            q_num = q.question_number.upper().replace('Q-', '').replace('Q', '')
            detailed = client.get_question_details(parliament_session, q_num)
            if detailed:
                # Merge list data with detail data
                # List data is more reliable for asker_name, date_asked, status
                # Detail data has question_text, sessional_paper
                if q.asker_name:
                    detailed.asker_name = q.asker_name
                if q.date_asked:
                    detailed.date_asked = q.date_asked
                if q.status:
                    detailed.status = q.status
                detailed_questions.append(detailed)
            else:
                # Fallback to list data if detail fetch fails
                detailed_questions.append(q)
        except Exception as e:
            logger.warning(f"Failed to fetch details for {q.question_number}: {e}")
            detailed_questions.append(q)

        # Log progress every 50 questions
        if (i + 1) % 50 == 0:
            logger.info(f"  Fetched {i + 1}/{len(new_questions)} question details...")

    logger.info(f"  Fetched details for {len(detailed_questions)} questions")

    # 5. Build MP name mapping for linking
    logger.info("Building MP name mapping...")
    mp_mapping = build_mp_mapping(neo4j_client)
    logger.info(f"  Mapped {len(mp_mapping)} MP name variations")

    # 6. Prepare question data for Neo4j
    question_data = []
    asked_by_data = []
    unmatched_mps = []

    for q in detailed_questions:
        q_dict = q.to_dict()
        q_dict['updated_at'] = datetime.utcnow().isoformat()
        question_data.append(q_dict)

        # Match MP
        if q.asker_name:
            mp_id = match_mp_name(q.asker_name, mp_mapping)
            if mp_id:
                asked_by_data.append({
                    "question_id": q.id,
                    "mp_id": mp_id,
                })
            else:
                unmatched_mps.append(q.asker_name)

    stats['unmatched_mps'] = len(set(unmatched_mps))

    # 7. Create WrittenQuestion nodes
    logger.info(f"Creating {len(question_data)} WrittenQuestion nodes...")

    create_query = """
        UNWIND $questions AS q
        MERGE (wq:WrittenQuestion {id: q.id})
        SET wq.question_number = q.question_number,
            wq.parliament_number = q.parliament_number,
            wq.session_number = q.session_number,
            wq.session_id = q.session_id,
            wq.date_asked = CASE WHEN q.date_asked IS NOT NULL THEN date(q.date_asked) ELSE null END,
            wq.asker_name = q.asker_name,
            wq.asker_constituency = q.asker_constituency,
            wq.responding_department = q.responding_department,
            wq.status = q.status,
            wq.due_date = CASE WHEN q.due_date IS NOT NULL THEN date(q.due_date) ELSE null END,
            wq.answer_date = CASE WHEN q.answer_date IS NOT NULL THEN date(q.answer_date) ELSE null END,
            wq.sessional_paper = q.sessional_paper,
            wq.question_text = q.question_text,
            wq.topics = q.topics,
            wq.ourcommons_url = q.ourcommons_url,
            wq.updated_at = datetime()
        RETURN count(wq) as created
    """

    # Batch the creation
    for i in range(0, len(question_data), batch_size):
        batch = question_data[i:i + batch_size]
        result = neo4j_client.run_query(create_query, {"questions": batch})
        stats['questions_created'] += result[0]['created'] if result else 0

    logger.success(f"Created {stats['questions_created']} WrittenQuestion nodes")

    # 8. Create ASKED_BY relationships
    if asked_by_data:
        logger.info(f"Creating {len(asked_by_data)} ASKED_BY relationships...")

        ask_query = """
            UNWIND $data AS row
            MATCH (wq:WrittenQuestion {id: row.question_id})
            MATCH (mp:MP {id: row.mp_id})
            MERGE (wq)-[:ASKED_BY]->(mp)
            RETURN count(*) as linked
        """

        for i in range(0, len(asked_by_data), batch_size):
            batch = asked_by_data[i:i + batch_size]
            result = neo4j_client.run_query(ask_query, {"data": batch})
            stats['asked_by_links'] += result[0]['linked'] if result else 0

        logger.success(f"Created {stats['asked_by_links']} ASKED_BY relationships")

    if unmatched_mps:
        unique_unmatched = list(set(unmatched_mps))
        logger.warning(f"Could not match {len(unique_unmatched)} unique MP names:")
        for name in unique_unmatched[:10]:
            logger.warning(f"  - {name}")
        if len(unique_unmatched) > 10:
            logger.warning(f"  ... and {len(unique_unmatched) - 10} more")

    # 9. Summary
    logger.info("=" * 60)
    logger.success("WRITTEN QUESTIONS INGESTION COMPLETE")
    logger.info(f"Questions scraped: {stats['questions_scraped']}")
    logger.info(f"Questions created: {stats['questions_created']}")
    logger.info(f"ASKED_BY links: {stats['asked_by_links']}")
    logger.info(f"Unmatched MPs: {stats['unmatched_mps']}")
    match_rate = (stats['asked_by_links'] / stats['questions_created'] * 100) if stats['questions_created'] > 0 else 0
    logger.info(f"MP match rate: {match_rate:.1f}%")
    logger.info("=" * 60)

    return stats


def update_question_statuses(
    neo4j_client: Neo4jClient,
    parliament_session: str = "45-1",
) -> Dict[str, int]:
    """
    Update status of existing questions (check if answered).

    This is useful for periodic updates to track when questions get answered.
    When a question becomes answered, fetches detail page for sessional_paper.

    Args:
        neo4j_client: Neo4j client
        parliament_session: Session to update

    Returns:
        Dict with counts of updated questions
    """
    logger.info(f"Updating question statuses for session {parliament_session}...")

    stats = {
        'checked': 0,
        'updated': 0,
        'newly_answered': 0,
    }

    client = WrittenQuestionsClient()

    # Get all questions from OurCommons
    all_questions = client.list_questions(parliament_session=parliament_session)
    stats['checked'] = len(all_questions)

    # Update statuses in Neo4j
    update_query = """
        MATCH (wq:WrittenQuestion {id: $id})
        SET wq.status = $status,
            wq.answer_date = CASE WHEN $answer_date IS NOT NULL THEN date($answer_date) ELSE wq.answer_date END,
            wq.sessional_paper = CASE WHEN $sessional_paper IS NOT NULL THEN $sessional_paper ELSE wq.sessional_paper END,
            wq.updated_at = datetime()
        RETURN wq.status <> $old_status as changed
    """

    for q in all_questions:
        # Get current status
        current = neo4j_client.run_query(
            "MATCH (wq:WrittenQuestion {id: $id}) RETURN wq.status as status, wq.sessional_paper as sessional_paper",
            {"id": q.id}
        )

        if current:
            old_status = current[0].get('status', '')
            old_sessional_paper = current[0].get('sessional_paper')

            # Check if status changed or if we need sessional_paper
            is_now_answered = q.status and 'answered' in q.status.lower()
            needs_sessional_paper = is_now_answered and not old_sessional_paper
            status_changed = old_status != q.status

            if status_changed or needs_sessional_paper:
                sessional_paper = None

                # If newly answered, fetch detail page for sessional_paper
                if needs_sessional_paper:
                    try:
                        q_num = q.question_number.upper().replace('Q-', '').replace('Q', '')
                        detailed = client.get_question_details(parliament_session, q_num)
                        if detailed and detailed.sessional_paper:
                            sessional_paper = detailed.sessional_paper
                            stats['newly_answered'] += 1
                            logger.info(f"  {q.question_number} answered - sessional paper: {sessional_paper}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch details for {q.question_number}: {e}")

                neo4j_client.run_query(update_query, {
                    "id": q.id,
                    "status": q.status,
                    "answer_date": q.answer_date,
                    "sessional_paper": sessional_paper,
                    "old_status": old_status
                })
                stats['updated'] += 1

    logger.info(f"Updated {stats['updated']} question statuses ({stats['newly_answered']} newly answered)")
    return stats
