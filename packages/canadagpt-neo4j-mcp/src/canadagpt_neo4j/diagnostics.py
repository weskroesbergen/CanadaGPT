"""Diagnostic tools for MP linking, data freshness, and graph pattern analysis."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


def diagnose_mp_linking(driver, date_from: str, date_to: str, database: str) -> Dict[str, Any]:
    """
    Analyze MP name matching success rates for a date range.

    Returns:
        - Linking rate percentage
        - Total statements vs. linked statements
        - Top 20 unmatched speakers with occurrence counts
        - Suggestions for improvement
    """
    try:
        with driver.session(database=database) as session:
            # Total statements in date range
            total_query = """
            MATCH (s:Statement)-[:PART_OF]->(d:Document)
            WHERE d.date >= $date_from AND d.date <= $date_to
            RETURN count(s) as total_statements
            """
            total_result = session.run(total_query, {"date_from": date_from, "date_to": date_to})
            total_statements = total_result.single()["total_statements"]

            # Linked statements (with MADE_BY relationship)
            linked_query = """
            MATCH (mp:MP)<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document)
            WHERE d.date >= $date_from AND d.date <= $date_to
            RETURN count(s) as linked_statements
            """
            linked_result = session.run(linked_query, {"date_from": date_from, "date_to": date_to})
            linked_statements = linked_result.single()["linked_statements"]

            # Unmatched speakers
            unmatched_query = """
            MATCH (s:Statement)-[:PART_OF]->(d:Document)
            WHERE d.date >= $date_from AND d.date <= $date_to
              AND NOT (s)-[:MADE_BY]->(:MP)
              AND s.who_en IS NOT NULL
            WITH s.who_en as speaker, count(*) as occurrence_count
            RETURN speaker, occurrence_count
            ORDER BY occurrence_count DESC
            LIMIT 20
            """
            unmatched_result = session.run(unmatched_query, {"date_from": date_from, "date_to": date_to})
            unmatched_speakers = [dict(record) for record in unmatched_result]

            # Calculate linking rate
            linking_rate = (linked_statements / total_statements * 100) if total_statements > 0 else 0

            # Generate suggestions
            suggestions = []

            # Check for known non-MP speakers
            non_mp_keywords = ["Speaker", "Clerk", "Chair", "Acting Speaker", "Deputy Speaker"]
            for speaker in unmatched_speakers[:5]:
                speaker_name = speaker["speaker"]
                if any(keyword in speaker_name for keyword in non_mp_keywords):
                    suggestions.append(
                        f"'{speaker_name}' ({speaker['occurrence_count']} occurrences) is a parliamentary officer, not an MP. This is expected."
                    )
                elif speaker_name.startswith("Hon.") or speaker_name.startswith("Rt. Hon."):
                    suggestions.append(
                        f"'{speaker_name}' ({speaker['occurrence_count']} occurrences) may be a new MP or cabinet minister not yet in database. Run MP ingestion."
                    )
                else:
                    suggestions.append(
                        f"'{speaker_name}' ({speaker['occurrence_count']} occurrences) - check for name variations or typos."
                    )

            return {
                "date_range": {"from": date_from, "to": date_to},
                "total_statements": total_statements,
                "linked_statements": linked_statements,
                "unlinked_statements": total_statements - linked_statements,
                "linking_rate_percentage": round(linking_rate, 2),
                "unmatched_speakers": unmatched_speakers,
                "suggestions": suggestions,
                "status": "good" if linking_rate >= 85 else "needs_improvement"
            }
    except Exception as e:
        return {"error": str(e)}


def check_data_freshness(driver, database: str) -> Dict[str, Any]:
    """
    Verify ingestion pipelines are running on schedule.

    Compares latest data dates against expected publication schedules:
    - Hansard: Published 1-2 days after sitting (expect 2-3 day lag)
    - Votes: Same day as vote (expect 1 day lag)
    - Committee Evidence: Published 1-7 days after meeting (expect 7 day lag)
    - MP Data: Updated monthly (expect 30 day lag)
    - Lobbying: Updated weekly (expect 7 day lag)
    """
    try:
        with driver.session(database=database) as session:
            today = datetime.now().date()

            # Hansard freshness
            hansard_query = "MATCH (d:Document) RETURN max(d.date) as latest_date"
            hansard_result = session.run(hansard_query).single()
            hansard_latest = hansard_result["latest_date"] if hansard_result and hansard_result["latest_date"] else None

            # Votes freshness
            votes_query = "MATCH (v:Vote) RETURN max(v.date) as latest_date"
            votes_result = session.run(votes_query).single()
            votes_latest = votes_result["latest_date"] if votes_result and votes_result["latest_date"] else None

            # Committee evidence freshness
            evidence_query = "MATCH (e:CommitteeEvidence) RETURN max(e.date) as latest_date"
            evidence_result = session.run(evidence_query).single()
            evidence_latest = evidence_result["latest_date"] if evidence_result and evidence_result["latest_date"] else None

            # Lobbying freshness
            lobbying_query = "MATCH (lc:LobbyCommunication) RETURN max(lc.date) as latest_date"
            lobbying_result = session.run(lobbying_query).single()
            lobbying_latest = lobbying_result["latest_date"] if lobbying_result and lobbying_result["latest_date"] else None

            # Calculate staleness
            def days_old(date_str):
                if not date_str:
                    return None
                date_obj = datetime.fromisoformat(date_str).date()
                return (today - date_obj).days

            hansard_days = days_old(hansard_latest)
            votes_days = days_old(votes_latest)
            evidence_days = days_old(evidence_latest)
            lobbying_days = days_old(lobbying_latest)

            # Determine status
            warnings = []

            if hansard_days is not None and hansard_days > 5:
                warnings.append(f"Hansard data is {hansard_days} days old (expected: 2-3 days). Check hansard-daily-import job.")

            if votes_days is not None and votes_days > 3:
                warnings.append(f"Votes data is {votes_days} days old (expected: 1 day). Check votes-ingestion job.")

            if evidence_days is not None and evidence_days > 14:
                warnings.append(f"Committee evidence is {evidence_days} days old (expected: 7 days). Check committee-evidence-ingestion job.")

            if lobbying_days is not None and lobbying_days > 14:
                warnings.append(f"Lobbying data is {lobbying_days} days old (expected: 7 days). Check lobbying-ingestion job.")

            return {
                "today": str(today),
                "data_sources": {
                    "hansard": {
                        "latest_date": hansard_latest,
                        "days_old": hansard_days,
                        "expected_lag_days": "2-3",
                        "status": "fresh" if hansard_days is not None and hansard_days <= 5 else "stale"
                    },
                    "votes": {
                        "latest_date": votes_latest,
                        "days_old": votes_days,
                        "expected_lag_days": "1",
                        "status": "fresh" if votes_days is not None and votes_days <= 3 else "stale"
                    },
                    "committee_evidence": {
                        "latest_date": evidence_latest,
                        "days_old": evidence_days,
                        "expected_lag_days": "7",
                        "status": "fresh" if evidence_days is not None and evidence_days <= 14 else "stale"
                    },
                    "lobbying": {
                        "latest_date": lobbying_latest,
                        "days_old": lobbying_days,
                        "expected_lag_days": "7",
                        "status": "fresh" if lobbying_days is not None and lobbying_days <= 14 else "stale"
                    }
                },
                "warnings": warnings,
                "overall_status": "healthy" if not warnings else "needs_attention"
            }
    except Exception as e:
        return {"error": str(e)}


def analyze_graph_patterns(
    driver,
    date_from: Optional[str],
    date_to: Optional[str],
    database: str
) -> Dict[str, Any]:
    """
    Detect anomalies and interesting patterns in the graph.

    Patterns analyzed:
    - Debate volume gaps (missing sittings)
    - MP activity dropoffs (previously active MPs with no recent speeches)
    - Committee meeting spikes
    - Vote attendance patterns
    """
    try:
        with driver.session(database=database) as session:
            anomalies = []

            # 1. Debate volume gaps (missing debate dates)
            if date_from and date_to:
                gap_query = """
                MATCH (d:Document)
                WHERE d.date >= $date_from AND d.date <= $date_to
                WITH collect(DISTINCT d.date) as debate_dates
                RETURN debate_dates
                """
                gap_result = session.run(gap_query, {"date_from": date_from, "date_to": date_to})
                debate_dates = gap_result.single()["debate_dates"]

                # Check for multi-day gaps (potential missing data)
                debate_dates_sorted = sorted(debate_dates)
                for i in range(len(debate_dates_sorted) - 1):
                    date1 = datetime.fromisoformat(debate_dates_sorted[i]).date()
                    date2 = datetime.fromisoformat(debate_dates_sorted[i + 1]).date()
                    gap_days = (date2 - date1).days

                    # Flag gaps > 7 days (excluding expected recesses)
                    if gap_days > 7:
                        anomalies.append({
                            "type": "debate_volume_gap",
                            "description": f"{gap_days}-day gap between {debate_dates_sorted[i]} and {debate_dates_sorted[i + 1]}",
                            "severity": "high" if gap_days > 14 else "medium"
                        })

            # 2. MP activity dropoffs
            dropoff_query = """
            MATCH (mp:MP)-[:SPOKE_AT]->(d:Document)
            WITH mp, max(d.date) as last_speech_date, count(*) as total_speeches
            WHERE total_speeches > 10 AND last_speech_date < date() - duration({days: 30})
            RETURN mp.name, last_speech_date, total_speeches
            ORDER BY last_speech_date ASC
            LIMIT 10
            """
            dropoff_result = session.run(dropoff_query)
            for record in dropoff_result:
                anomalies.append({
                    "type": "mp_activity_dropoff",
                    "description": f"{record['mp.name']} has not spoken since {record['last_speech_date']} ({record['total_speeches']} total speeches)",
                    "severity": "low"
                })

            # 3. Committee meeting spikes
            spike_query = """
            MATCH (c:Committee)-[:HELD_MEETING]->(m:Meeting)
            WHERE m.date >= date() - duration({days: 30})
            WITH c, count(m) as recent_meetings
            WHERE recent_meetings > 10
            RETURN c.name, c.code, recent_meetings
            ORDER BY recent_meetings DESC
            """
            spike_result = session.run(spike_query)
            for record in spike_result:
                anomalies.append({
                    "type": "committee_meeting_spike",
                    "description": f"{record['c.name']} ({record['c.code']}) held {record['recent_meetings']} meetings in last 30 days",
                    "severity": "info"
                })

            # 4. Vote attendance patterns (low participation)
            attendance_query = """
            MATCH (v:Vote)
            WHERE v.date >= date() - duration({days: 90})
            WITH v, v.num_yeas + v.num_nays as total_votes
            WHERE total_votes < 200
            RETURN v.vote_number, v.date_time, v.subject, total_votes
            ORDER BY total_votes ASC
            LIMIT 5
            """
            attendance_result = session.run(attendance_query)
            for record in attendance_result:
                anomalies.append({
                    "type": "low_vote_attendance",
                    "description": f"Vote {record['v.vote_number']} on {record['v.date_time']} had only {record['total_votes']} participants: {record['v.subject']}",
                    "severity": "medium"
                })

            return {
                "analysis_period": {
                    "from": date_from or "Not specified",
                    "to": date_to or "Not specified"
                },
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "summary": {
                    "debate_gaps": len([a for a in anomalies if a["type"] == "debate_volume_gap"]),
                    "mp_dropoffs": len([a for a in anomalies if a["type"] == "mp_activity_dropoff"]),
                    "committee_spikes": len([a for a in anomalies if a["type"] == "committee_meeting_spike"]),
                    "low_attendance_votes": len([a for a in anomalies if a["type"] == "low_vote_attendance"])
                }
            }
    except Exception as e:
        return {"error": str(e)}
