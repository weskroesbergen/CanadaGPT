"""Pre-built Cypher query templates for common CanadaGPT operations."""

from typing import Dict, Any


def get_query_templates() -> Dict[str, Dict[str, Any]]:
    """Return dictionary of pre-built Cypher query templates."""
    return {
        "recent_debates": {
            "description": "Get Hansard debates from the last N days",
            "query": """
MATCH (d:Document)
WHERE d.date >= date() - duration({days: $days})
RETURN d.id, d.date, d.number, d.session_id
ORDER BY d.date DESC
LIMIT 100
            """.strip(),
            "parameters": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 7
                }
            }
        },

        "mp_speeches": {
            "description": "Get all speeches by a specific MP",
            "query": """
MATCH (mp:MP)-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document)
WHERE mp.name = $mp_name OR mp.parl_mp_id = $parl_mp_id
RETURN mp.name, d.date, d.id as document_id, s.content_en, s.h1_en, s.h2_en, s.time
ORDER BY d.date DESC, s.time
LIMIT $limit
            """.strip(),
            "parameters": {
                "mp_name": {
                    "type": "string",
                    "description": "MP name (e.g., 'Pierre Poilievre')",
                    "default": None
                },
                "parl_mp_id": {
                    "type": "string",
                    "description": "Parliamentary MP ID",
                    "default": None
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of speeches to return",
                    "default": 50
                }
            }
        },

        "spoke_at_stats": {
            "description": "Get SPOKE_AT relationship statistics for a date range",
            "query": """
MATCH (mp:MP)-[s:SPOKE_AT]->(d:Document)
WHERE d.date >= $date_from AND d.date <= $date_to
RETURN mp.name, mp.current_party, count(s) as speech_count, collect(DISTINCT d.date) as debate_dates
ORDER BY speech_count DESC
LIMIT $limit
            """.strip(),
            "parameters": {
                "date_from": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                    "default": None
                },
                "date_to": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                    "default": None
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of MPs to return",
                    "default": 20
                }
            }
        },

        "vote_analysis": {
            "description": "Analyze voting patterns by MP, party, or bill",
            "query": """
MATCH (mp:MP)-[:CAST_IN]->(ballot:Ballot)-[:CAST_IN]->(vote:Vote)
WHERE vote.vote_number = $vote_number OR vote.bill_number = $bill_number
RETURN mp.name, mp.current_party, ballot.vote_value, ballot.is_yea, ballot.is_nay,
       vote.vote_number, vote.date_time, vote.result, vote.subject
ORDER BY mp.current_party, mp.name
            """.strip(),
            "parameters": {
                "vote_number": {
                    "type": "integer",
                    "description": "Specific vote number",
                    "default": None
                },
                "bill_number": {
                    "type": "string",
                    "description": "Bill number (e.g., 'C-249')",
                    "default": None
                }
            }
        },

        "committee_evidence": {
            "description": "Get committee evidence and testimony by committee code",
            "query": """
MATCH (committee:Committee {code: $committee_code})-[:HELD_MEETING]->(meeting:Meeting)
OPTIONAL MATCH (meeting)-[:HAS_EVIDENCE]->(evidence:CommitteeEvidence)
OPTIONAL MATCH (evidence)<-[:GIVEN_IN]-(testimony:CommitteeTestimony)
RETURN committee.name, meeting.date, meeting.subject, meeting.status,
       evidence.id as evidence_id, evidence.date as evidence_date,
       testimony.speaker_name, testimony.organization, testimony.role, testimony.is_witness
ORDER BY meeting.date DESC
LIMIT $limit
            """.strip(),
            "parameters": {
                "committee_code": {
                    "type": "string",
                    "description": "Committee code (e.g., 'ETHI', 'ENVI')",
                    "default": None
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of meetings to return",
                    "default": 20
                }
            }
        },

        "lobbying_by_bill": {
            "description": "Get lobbying activity related to a specific bill",
            "query": """
MATCH (bill:Bill {bill_number: $bill_number})
OPTIONAL MATCH (comm:LobbyCommunication)-[:CONCERNS]->(bill)
OPTIONAL MATCH (comm)<-[:MADE]-(reg:LobbyRegistration)
RETURN bill.bill_number, bill.title,
       comm.id as communication_id, comm.date, comm.subject,
       reg.id as registration_id, reg.client_name, reg.organization_name
ORDER BY comm.date DESC
LIMIT $limit
            """.strip(),
            "parameters": {
                "bill_number": {
                    "type": "string",
                    "description": "Bill number (e.g., 'C-249')",
                    "default": None
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of communications to return",
                    "default": 50
                }
            }
        },

        "data_freshness": {
            "description": "Get latest data dates for all node types",
            "query": """
CALL {
    MATCH (d:Document) RETURN 'Hansard' as type, max(d.date) as latest_date
    UNION
    MATCH (v:Vote) RETURN 'Votes' as type, max(v.date) as latest_date
    UNION
    MATCH (e:CommitteeEvidence) RETURN 'Committee Evidence' as type, max(e.date) as latest_date
    UNION
    MATCH (m:Meeting) RETURN 'Committee Meetings' as type, max(m.date) as latest_date
    UNION
    MATCH (lc:LobbyCommunication) RETURN 'Lobbying Communications' as type, max(lc.date) as latest_date
}
RETURN type, latest_date
ORDER BY type
            """.strip(),
            "parameters": {}
        },

        "mp_linking_diagnostics": {
            "description": "Identify statements without MP linkage (unmatched speakers)",
            "query": """
MATCH (s:Statement)-[:PART_OF]->(d:Document)
WHERE d.date >= $date_from AND d.date <= $date_to
  AND NOT (s)-[:MADE_BY]->(:MP)
  AND s.who_en IS NOT NULL
WITH s.who_en as speaker, count(*) as occurrence_count
RETURN speaker, occurrence_count
ORDER BY occurrence_count DESC
LIMIT 50
            """.strip(),
            "parameters": {
                "date_from": {
                    "type": "string",
                    "description": "Start date (YYYY-MM-DD)",
                    "default": None
                },
                "date_to": {
                    "type": "string",
                    "description": "End date (YYYY-MM-DD)",
                    "default": None
                }
            }
        }
    }


def format_query_result(result: dict, template_name: str) -> str:
    """Format query result for display."""
    if "error" in result:
        return f"Error: {result['error']}"

    output = [f"Query: {template_name}"]
    output.append(f"Rows returned: {result.get('row_count', 0)}")
    output.append(f"Execution time: {result.get('execution_time_seconds', 0):.3f}s")
    output.append("\nResults:")

    for i, record in enumerate(result.get("records", [])[:10], 1):
        output.append(f"\n{i}. {record}")

    if result.get("row_count", 0) > 10:
        output.append(f"\n... and {result['row_count'] - 10} more rows")

    return "\n".join(output)
