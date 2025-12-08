#!/usr/bin/env python3
"""Wrapper to run daily-hansard-import with environment variables"""
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

# Set args
sys.argv = ['daily-hansard-import.py', '--lookback-days', '30']

# Run the script
exec(open('scripts/daily-hansard-import.py', encoding='utf-8').read())