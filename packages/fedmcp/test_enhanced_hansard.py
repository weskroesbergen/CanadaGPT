#!/usr/bin/env python3
"""
Test script to demonstrate enhanced Hansard XML metadata extraction.

This script fetches a recent Hansard sitting and displays the rich metadata
that is now being captured from the XML, including:
- Person database IDs (Affiliation@DbId)
- Role type codes (1=PM, 2=MP, 15=Speaker, etc.)
- Paragraph IDs for citations
- Structured timestamps
- Floor language
- Intervention types
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fedmcp.clients.ourcommons import OurCommonsHansardClient


def main():
    print("=" * 70)
    print("Enhanced Hansard XML Metadata Extraction Test")
    print("=" * 70)
    print()

    client = OurCommonsHansardClient()

    print("Fetching latest Hansard sitting...")
    try:
        sitting = client.get_sitting("latest/hansard", parse=True)
    except Exception as e:
        print(f"❌ Error fetching Hansard: {e}")
        return

    print(f"✅ Successfully parsed Hansard sitting")
    print()

    # Display document-level metadata
    print("📄 Document Metadata")
    print("-" * 70)
    print(f"Date: {sitting.date}")
    print(f"Number: {sitting.number}")
    print(f"Language: {sitting.language}")
    print(f"Source URL: {sitting.source_xml_url}")
    print()
    print("🆕 Enhanced Document Metadata:")
    print(f"  Creation Timestamp: {sitting.creation_timestamp}")
    print(f"  Speaker of the Day: {sitting.speaker_of_day}")
    print(f"  Hansard Document ID: {sitting.hansard_document_id}")
    print(f"  Parliament #: {sitting.parliament_number}")
    print(f"  Session #: {sitting.session_number}")
    print(f"  Volume: {sitting.volume}")
    print()

    # Display enhanced statement metadata
    print("💬 Sample Statements with Enhanced Metadata")
    print("-" * 70)

    total_statements = sum(len(section.speeches) for section in sitting.sections)
    print(f"Total sections: {len(sitting.sections)}")
    print(f"Total statements: {total_statements}")
    print()

    # Show first 3 statements from first section
    if sitting.sections and sitting.sections[0].speeches:
        section = sitting.sections[0]
        print(f"Section: {section.title}")
        print()

        for i, speech in enumerate(section.speeches[:3], 1):
            print(f"Statement {i}:")
            print(f"  Speaker: {speech.speaker_name}")
            print(f"  Party: {speech.party}")
            print(f"  Riding: {speech.riding}")
            print(f"  Time: {speech.timecode}")
            print()
            print("  🆕 Enhanced Metadata:")
            print(f"    Person DB ID: {speech.person_db_id} {'✅' if speech.person_db_id else '❌'}")
            print(f"    Role Type Code: {speech.role_type_code} {'✅' if speech.role_type_code else '❌'}")

            # Decode role type
            if speech.role_type_code:
                role_names = {
                    1: "Prime Minister",
                    2: "MP",
                    9: "Leader of Opposition",
                    15: "Speaker",
                    60107: "Presiding Officer",
                    96: "Clerk"
                }
                role_name = role_names.get(speech.role_type_code, f"Unknown ({speech.role_type_code})")
                print(f"      → Role: {role_name}")

            print(f"    Intervention ID: {speech.intervention_id} {'✅' if speech.intervention_id else '❌'}")
            print(f"    Paragraph IDs: {len(speech.paragraph_ids)} paragraphs {'✅' if speech.paragraph_ids else '❌'}")
            if speech.paragraph_ids:
                print(f"      → First 3: {speech.paragraph_ids[:3]}")
            if speech.timestamp_hour is not None and speech.timestamp_minute is not None:
                print(f"    Structured Time: {speech.timestamp_hour}:{speech.timestamp_minute:02d} ✅")
            else:
                print(f"    Structured Time: None ❌")
            print(f"    Floor Language: {speech.floor_language} {'✅' if speech.floor_language else '❌'}")
            print(f"    Intervention Type: {speech.intervention_type} {'✅' if speech.intervention_type else '❌'}")
            print()
            print(f"  Content Preview: {speech.text[:150]}...")
            print()
            print("-" * 70)

    # Statistics
    print()
    print("📊 Metadata Capture Statistics")
    print("-" * 70)

    all_speeches = [speech for section in sitting.sections for speech in section.speeches]

    stats = {
        "person_db_id": sum(1 for s in all_speeches if s.person_db_id),
        "role_type_code": sum(1 for s in all_speeches if s.role_type_code),
        "paragraph_ids": sum(1 for s in all_speeches if s.paragraph_ids),
        "structured_time": sum(1 for s in all_speeches if s.timestamp_hour is not None),
        "floor_language": sum(1 for s in all_speeches if s.floor_language),
        "intervention_type": sum(1 for s in all_speeches if s.intervention_type),
    }

    for field, count in stats.items():
        percentage = (count / len(all_speeches) * 100) if all_speeches else 0
        print(f"{field:20s}: {count:4d}/{len(all_speeches)} ({percentage:5.1f}%) {'✅' if percentage > 50 else '⚠️ '}")

    print()
    print("=" * 70)
    print("✅ Enhanced metadata extraction successful!")
    print("=" * 70)


if __name__ == "__main__":
    main()
