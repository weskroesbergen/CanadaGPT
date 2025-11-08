"""
CanadaGPT Data Pipeline

Ingests Canadian government data into Neo4j for accountability tracking.
"""

__version__ = "1.0.0"

from .utils.neo4j_client import Neo4jClient
from .utils.config import Config

__all__ = ["Neo4jClient", "Config"]
