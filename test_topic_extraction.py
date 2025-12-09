#!/usr/bin/env python3
"""Test the new topic extraction from daily-hansard-import.py"""
import os
import sys
from pathlib import Path

# Set environment variables
os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
os.environ['NEO4J_USERNAME'] = 'neo4j'
os.environ['NEO4J_PASSWORD'] = 'canadagpt2024'

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path(__file__).parent / 'packages' / 'fedmcp' / 'src'))

from fedmcp.clients.ourcommons import OurCommonsHansardClient
from fedmcp_pipeline.utils.neo4j_client import Neo4jClient

# Import the parsing function
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from typing import Dict, Any
import requests

# Test with a recent debate
def test_topic_extraction():
    print("Testing topic extraction from December 3, 2025 debate (No. 066)...")

    # Fetch XML
    sitting_number = "066"
    xml_url = f"https://www.ourcommons.ca/Content/House/451/Debates/{sitting_number}/HAN{sitting_number}-E.XML"

    print(f"Fetching XML from: {xml_url}")
    response = requests.get(xml_url)
    response.raise_for_status()
    xml_text = response.content.decode('utf-8-sig')

    print(f"XML fetched successfully ({len(xml_text)} bytes)")

    # Parse with new topic extraction
    from xml.etree import ElementTree as ET
    tree = ET.fromstring(xml_text)

    # Extract topics
    intervention_topics = {}
    for order in tree.findall(".//OrderOfBusiness"):
        order_title_el = order.find("OrderOfBusinessTitle")
        h1_en = "".join(order_title_el.itertext()).strip() if order_title_el is not None else "Hansard"

        subjects = order.findall(".//SubjectOfBusiness")
        for subject in subjects:
            subject_title_el = subject.find("SubjectOfBusinessTitle")
            h2_en = "".join(subject_title_el.itertext()).strip() if subject_title_el is not None else None

            content = subject.find("SubjectOfBusinessContent")
            if content is not None:
                for intervention in content.findall(".//Intervention"):
                    intervention_id = intervention.get("id")
                    if intervention_id:
                        intervention_topics[intervention_id] = (h1_en, h2_en)

    print(f"\nExtracted {len(intervention_topics)} intervention topic mappings")
    print("\nSample topics (first 10):")
    for i, (interv_id, (h1, h2)) in enumerate(list(intervention_topics.items())[:10]):
        print(f"  {interv_id}: h1='{h1}' | h2='{h2}'")

    # Show unique h2_en topics
    unique_topics = set(h2 for _, h2 in intervention_topics.values() if h2)
    print(f"\nFound {len(unique_topics)} unique h2_en topics:")
    for topic in sorted(unique_topics)[:20]:
        print(f"  - {topic}")

if __name__ == "__main__":
    test_topic_extraction()