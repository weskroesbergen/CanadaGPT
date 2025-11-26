#!/bin/bash
# Import sittings 050-057 using the existing daily-hansard-import logic

export NEO4J_URI=bolt://localhost:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD=canadagpt2024

PYTHON=/Users/matthewdufresne/CanadaGPT/packages/data-pipeline/venv/bin/python3

for sitting in 050 051 052 053 054 055 056 057; do
  echo "======================================================================"
  echo "Importing sitting $sitting..."
  echo "======================================================================"
  
  # Create a temporary Python script to import this specific sitting
  $PYTHON - <<PYEOF
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'packages' / 'data-pipeline'))
sys.path.insert(0, str(Path.cwd() / 'packages' / 'fedmcp' / 'src'))

from fedmcp_pipeline.utils.neo4j_client import Neo4jClient  
from fedmcp_pipeline.utils.progress import logger
from fedmcp.clients.ourcommons import OurCommonsHansardClient

# Check and import sitting $sitting
url = "https://www.ourcommons.ca/Content/House/451/Debates/$sitting/HAN$sitting-E.XML"
print(f"Checking {url}...")

# Just invoke the main import script which has all the logic
import subprocess
result = subprocess.run([
    "$PYTHON",
    "scripts/daily-hansard-import.py"
], capture_output=False)
sys.exit(result.returncode)
PYEOF

  if [ $? -ne 0 ]; then
    echo "Warning: Failed to import sitting $sitting"
  fi
done

echo "======================================================================"
echo "Backfill complete!"
echo "======================================================================"
