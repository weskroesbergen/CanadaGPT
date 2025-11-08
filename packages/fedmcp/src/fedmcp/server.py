"""FedMCP Server - MCP server for Canadian federal parliamentary and legal information."""

import os
import asyncio
import logging
from typing import Any, Optional
from dataclasses import asdict
from itertools import islice

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Icon,
)
import mcp.server.stdio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from .clients import (
    OpenParliamentClient,
    OurCommonsHansardClient,
    LegisInfoClient,
    CanLIIClient,
    RepresentClient,
)
from .clients.expenditure import MPExpenditureClient
from .clients.petitions import PetitionsClient
from .clients.lobbying import LobbyingRegistryClient
from .clients.federal_contracts import FederalContractsClient
from .clients.political_contributions import PoliticalContributionsClient
from .clients.grants_contributions import GrantsContributionsClient
from .clients.departmental_expenses import DepartmentalExpensesClient

# Initialize clients
op_client = OpenParliamentClient()
hansard_client = OurCommonsHansardClient()
legis_client = LegisInfoClient()
represent_client = RepresentClient()
expenditure_client = MPExpenditureClient()
petitions_client = PetitionsClient()
lobbying_client = LobbyingRegistryClient()
contracts_client = FederalContractsClient()
political_contrib_client = PoliticalContributionsClient()
grants_client = GrantsContributionsClient()
dept_expenses_client = DepartmentalExpensesClient()

# Initialize CanLII client if API key is available
canlii_api_key = os.getenv("CANLII_API_KEY")
canlii_client = CanLIIClient(api_key=canlii_api_key) if canlii_api_key else None

# Create server instance with Canadian flag icon (SVG data URI)
# Using SVG to ensure compatibility with Claude Desktop UI
CANADIAN_FLAG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="#FF0000"/>
  <rect x="16" y="0" width="32" height="64" fill="#FFFFFF"/>
  <path d="M32 20 L28 28 L20 26 L26 32 L22 40 L32 36 L42 40 L38 32 L44 26 L36 28 Z" fill="#FF0000"/>
</svg>"""

import base64
flag_b64 = base64.b64encode(CANADIAN_FLAG_SVG.encode()).decode()
flag_data_uri = f"data:image/svg+xml;base64,{flag_b64}"

app = Server(
    name="Canada GPT",
    version="1.0.0",
    instructions="Canadian federal parliamentary and legal information server",
    icons=[Icon(src=flag_data_uri, mimeType="image/svg+xml")]
)


# Helper functions
async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread pool to avoid blocking the event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)


def validate_limit(limit: Optional[int], min_val: int = 1, max_val: int = 50, default: int = 10) -> int:
    """Validate and normalize limit parameter.

    Args:
        limit: The limit value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        default: Default value if limit is None

    Returns:
        Validated limit value

    Raises:
        ValueError: If limit is out of range
    """
    if limit is None:
        return default
    if not isinstance(limit, int):
        raise ValueError(f"limit must be an integer, got {type(limit).__name__}")
    if limit < min_val or limit > max_val:
        raise ValueError(f"limit must be between {min_val} and {max_val}, got {limit}")
    return limit


def sanitize_error_message(error: Exception) -> str:
    """Sanitize error messages to avoid leaking sensitive information.

    Args:
        error: The exception to sanitize

    Returns:
        Sanitized error message
    """
    import re
    error_str = str(error)
    # Remove API keys from error messages
    error_str = re.sub(r'api[_-]?key[=:]\s*[^\s&]+', 'api_key=***', error_str, flags=re.IGNORECASE)
    # Remove Bearer tokens (do this before generic token regex)
    error_str = re.sub(r'Bearer\s+[^\s&]+', 'Bearer ***', error_str, flags=re.IGNORECASE)
    # Remove tokens (matches: token=xxx, token: xxx)
    error_str = re.sub(r'token[=:]\s*[^\s&]+', 'token=***', error_str, flags=re.IGNORECASE)
    return error_str


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    tools = [
        Tool(
            name="search_debates",
            description="Search Canadian House of Commons debate summaries by keyword. NOTE: Limited functionality - this searches sitting summaries, not full speeches. For bill-specific debates, use 'search_bill_debates'. For keyword searches in full transcripts, use 'search_hansard'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords to search in debates",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_bills",
            description="Search for Canadian bills by number (e.g., C-249) or keywords. Searches both LEGISinfo and OpenParliament.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Bill number (e.g., C-249) or keywords",
                    },
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., 45-1), required for specific bill lookup",
                    },
                    "sponsor": {
                        "type": "string",
                        "description": "Filter by bill sponsor - politician URL (e.g., '/politicians/pierre-poilievre/')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_hansard",
            description="Search House of Commons Hansard transcripts for quotes or keywords. Returns matching speeches with full context. Can search latest or specific sitting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Quote or keywords to search in Hansard",
                    },
                    "sitting": {
                        "type": "string",
                        "description": "Optional: Specific sitting to search (e.g., '45-1/sitting-48/hansard' or 'latest/hansard'). Defaults to 'latest/hansard'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of speeches to return (1-20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_bill_debates",
            description="Search Hansard transcripts for debates about a specific bill. Retrieves debate dates from LEGISinfo, then searches those Hansards for the bill. Returns MP speeches with context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bill_number": {
                        "type": "string",
                        "description": "Bill number (e.g., C-3, C-4, S-12)",
                    },
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., 45-1). If omitted, searches recent sessions.",
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Optional: Additional keywords to search within bill debates (e.g., 'citizenship', 'affordability')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of speeches to return per sitting (1-20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["bill_number"],
            },
        ),
        Tool(
            name="get_committee_evidence",
            description="Get transcript evidence from a specific committee meeting. Returns speeches and testimony from witnesses and MPs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "parliament": {
                        "type": "string",
                        "description": "Parliament number (e.g., '44')",
                    },
                    "session": {
                        "type": "string",
                        "description": "Session number (e.g., '1')",
                    },
                    "committee": {
                        "type": "string",
                        "description": "Committee code (e.g., 'ETHI' for Ethics, 'ENVI' for Environment)",
                    },
                    "meeting": {
                        "type": "integer",
                        "description": "Meeting number",
                    },
                    "search": {
                        "type": "string",
                        "description": "Optional: Search for specific keywords in the transcript",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of speeches to return (if searching)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["parliament", "session", "committee", "meeting"],
            },
        ),
        Tool(
            name="list_debates",
            description="List recent House of Commons debates with pagination and optional date filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0,
                        "minimum": 0,
                    },
                    "date_after": {
                        "type": "string",
                        "description": "Filter debates after this date (YYYY-MM-DD format)",
                    },
                    "date_before": {
                        "type": "string",
                        "description": "Filter debates before this date (YYYY-MM-DD format)",
                    },
                },
            },
        ),
        Tool(
            name="get_bill",
            description="Get detailed information for a specific bill from LEGISinfo.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., 45-1)",
                    },
                    "code": {
                        "type": "string",
                        "description": "Bill code (e.g., c-249, lowercase)",
                    },
                },
                "required": ["session", "code"],
            },
        ),
        Tool(
            name="list_mps",
            description="List current Members of Parliament from OpenParliament.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        ),
        Tool(
            name="get_mp_expenses",
            description="Get quarterly expenditure data for a specific MP from House of Commons Proactive Disclosure. Search by MP name, party, or constituency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "MP name, party, or constituency to search for (e.g., 'Poilievre', 'Liberal', 'Simcoe North')",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search: 'name', 'party', or 'constituency'",
                        "enum": ["name", "party", "constituency"],
                        "default": "name",
                    },
                    "fiscal_year": {
                        "type": "integer",
                        "description": "Fiscal year (e.g., 2026 for 2025-2026). Defaults to current fiscal year 2026.",
                        "default": 2026,
                    },
                    "quarter": {
                        "type": "integer",
                        "description": "Quarter (1-4). Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar. Defaults to 1.",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 4,
                    },
                },
                "required": ["search_term"],
            },
        ),
        Tool(
            name="search_mp_expenses",
            description="Search and compare MP expenses. Get top spenders, party averages, or filter by expense category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Search mode: 'top_spenders' to get highest spenders, 'party_averages' to compare parties",
                        "enum": ["top_spenders", "party_averages"],
                    },
                    "category": {
                        "type": "string",
                        "description": "Expense category for top_spenders mode: 'salaries', 'travel', 'hospitality', 'contracts', or 'total'",
                        "enum": ["salaries", "travel", "hospitality", "contracts", "total"],
                        "default": "total",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results for top_spenders mode (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "fiscal_year": {
                        "type": "integer",
                        "description": "Fiscal year (e.g., 2026 for 2025-2026)",
                        "default": 2026,
                    },
                    "quarter": {
                        "type": "integer",
                        "description": "Quarter (1-4)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 4,
                    },
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="list_votes",
            description="List recent parliamentary votes from OpenParliament with optional date and result filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "date_after": {
                        "type": "string",
                        "description": "Filter votes after this date (YYYY-MM-DD format)",
                    },
                    "date_before": {
                        "type": "string",
                        "description": "Filter votes before this date (YYYY-MM-DD format)",
                    },
                    "result": {
                        "type": "string",
                        "description": "Filter by vote result",
                        "enum": ["Passed", "Negatived"],
                    },
                },
            },
        ),
        Tool(
            name="list_committees",
            description="List parliamentary committees (both House and Senate committees).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        ),
        Tool(
            name="get_committee_details",
            description="Get detailed information about a specific parliamentary committee including membership, mandate, and meeting information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "committee_url": {
                        "type": "string",
                        "description": "Committee URL path from OpenParliament (e.g., '/committees/finance/' or full URL)",
                    },
                },
                "required": ["committee_url"],
            },
        ),
        Tool(
            name="get_politician_profile",
            description="Get complete profile for a specific politician/MP including biographical information, current roles, and parliamentary history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "politician_url": {
                        "type": "string",
                        "description": "Politician URL path from OpenParliament (e.g., '/politicians/pierre-poilievre/' or full URL)",
                    },
                },
                "required": ["politician_url"],
            },
        ),
        Tool(
            name="search_petitions",
            description="Search House of Commons petitions by keyword, sponsor MP, topic, or category. Returns petition details including signatures, status, and government responses.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keywords to search in petition titles, text, and topics (e.g., 'climate change', 'health care')",
                    },
                    "sponsor_name": {
                        "type": "string",
                        "description": "MP sponsor name (full or partial, e.g., 'Elizabeth May', 'Poilievre')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Petition status category",
                        "enum": ["All", "Open", "Closed", "Responses"],
                        "default": "All",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_petition_details",
            description="Get detailed information about a specific petition by its number. Returns full petition text, grievances, signatures by province, government response if available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "petition_number": {
                        "type": "string",
                        "description": "Petition number (e.g., 'e-6629' for electronic or '451-00231' for paper)",
                    },
                },
                "required": ["petition_number"],
            },
        ),
        Tool(
            name="get_mp_petitions",
            description="Get all petitions sponsored by a specific MP. Shows MP engagement with citizen petitions and their areas of focus.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_name": {
                        "type": "string",
                        "description": "MP name (full or partial, e.g., 'Elizabeth May', 'Trudeau')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by petition status",
                        "enum": ["All", "Open", "Closed", "Responses"],
                        "default": "All",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of petitions (1-50)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["mp_name"],
            },
        ),
        Tool(
            name="search_lobbying_registrations",
            description="Search federal lobbying registrations to see who is lobbying, for which organizations, on what topics. Essential for tracking corporate influence and accountability.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "Client/organization name (e.g., 'Bell', 'Pfizer', 'Google')",
                    },
                    "lobbyist_name": {
                        "type": "string",
                        "description": "Lobbyist name",
                    },
                    "subject_keyword": {
                        "type": "string",
                        "description": "Keywords in subject matter (e.g., 'climate', 'telecommunications', 'pharmaceutical')",
                    },
                    "institution": {
                        "type": "string",
                        "description": "Government institution being lobbied (e.g., 'Health Canada', 'Industry Canada')",
                    },
                    "active_only": {
                        "type": "boolean",
                        "description": "Only show currently active registrations",
                        "default": True,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="search_lobbying_communications",
            description="Search actual lobbying communications/meetings between lobbyists and government officials. Shows who met with whom, when, and about what topics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "Client/organization name",
                    },
                    "lobbyist_name": {
                        "type": "string",
                        "description": "Lobbyist name",
                    },
                    "official_name": {
                        "type": "string",
                        "description": "Government official name (e.g., 'Minister', 'Deputy Minister')",
                    },
                    "institution": {
                        "type": "string",
                        "description": "Government institution",
                    },
                    "subject_keyword": {
                        "type": "string",
                        "description": "Keywords in communication subject matter",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD, e.g., '2024-01-01')",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (1-50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_top_lobbying_clients",
            description="Get the most active lobbying organizations by number of active registrations. Useful for identifying major corporate lobbying activity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of top clients to return (1-50)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "active_only": {
                        "type": "boolean",
                        "description": "Only count active registrations",
                        "default": True,
                    },
                },
            },
        ),
        Tool(
            name="analyze_bill_lobbying",
            description="Cross-reference a bill with lobbying activity to identify potential corporate influence. Searches lobbying registrations and communications for mentions of the bill.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bill_number": {
                        "type": "string",
                        "description": "Bill number (e.g., 'C-3', 'S-12')",
                    },
                    "bill_keyword": {
                        "type": "string",
                        "description": "Keywords related to the bill's subject matter (e.g., 'citizenship', 'online harms', 'affordability')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results per category (1-30)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 30,
                    },
                },
                "required": ["bill_keyword"],
            },
        ),
        Tool(
            name="analyze_mp_bills",
            description="Analyze an MP's legislative record by examining bills they've sponsored. Shows bill success rates, topics, and current status. Useful for evaluating MP effectiveness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_name": {
                        "type": "string",
                        "description": "MP name (full or partial, case-insensitive)",
                    },
                    "politician_url": {
                        "type": "string",
                        "description": "OpenParliament politician URL (e.g., '/politicians/pierre-poilievre/'). If provided, mp_name is ignored.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of bills to analyze (1-50)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="compare_party_bills",
            description="Compare bill introduction and success rates across political parties. Analyzes which parties are most active legislatively and which bills get passed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., '45-1'). If omitted, analyzes recent sessions.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of bills to analyze per party (1-100)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        ),
        Tool(
            name="analyze_bill_progress",
            description="Analyze the legislative progress timeline for a specific bill. Shows how long each stage took, current status, and historical context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bill_number": {
                        "type": "string",
                        "description": "Bill number (e.g., 'C-3', 'S-12')",
                    },
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., '45-1'). If omitted, searches recent sessions.",
                    },
                },
                "required": ["bill_number"],
            },
        ),
        Tool(
            name="get_mp_activity_scorecard",
            description="Generate comprehensive activity scorecard for an MP across all data sources: bills sponsored, votes, speeches, expenses, petitions, and lobbying connections. Essential for evaluating MP performance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_name": {
                        "type": "string",
                        "description": "MP name (full or partial)",
                    },
                    "politician_url": {
                        "type": "string",
                        "description": "OpenParliament politician URL. If provided, mp_name is ignored.",
                    },
                },
            },
        ),
        Tool(
            name="track_committee_activity",
            description="Track committee meeting activity and productivity. Shows meeting frequency, witnesses heard, reports tabled.",
            inputSchema={
                "type": "object",
                "properties": {
                    "committee": {
                        "type": "string",
                        "description": "Committee name or acronym (e.g., 'ETHI', 'Finance')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of committees to analyze if searching (1-20)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
            },
        ),
        Tool(
            name="detect_conflicts_of_interest",
            description="Cross-reference MP expenses, lobbying meetings, and voting records to identify potential conflicts of interest. Highlights unusual patterns for accountability.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_name": {
                        "type": "string",
                        "description": "MP name to investigate",
                    },
                    "topic_keyword": {
                        "type": "string",
                        "description": "Topic keyword to focus on (e.g., 'pharmaceutical', 'telecommunications')",
                    },
                },
            },
        ),
        Tool(
            name="analyze_industry_influence",
            description="Comprehensive analysis of corporate/industry influence on Parliament. Shows top lobbying industries, most-lobbied MPs, and connections to legislation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "industry_keyword": {
                        "type": "string",
                        "description": "Industry keyword (e.g., 'oil', 'tech', 'pharmaceutical', 'telecom')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results per category (1-20)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["industry_keyword"],
            },
        ),
        Tool(
            name="compare_mp_performance",
            description="Side-by-side comparison of multiple MPs across all metrics: bills, petitions, expenses, lobbying exposure. Useful for evaluating candidates or party effectiveness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_names": {
                        "type": "array",
                        "description": "List of MP names to compare (2-5 MPs)",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 5,
                    },
                },
                "required": ["mp_names"],
            },
        ),
        Tool(
            name="search_mp",
            description="Search for a Member of Parliament by name, party, or riding. Returns matching MPs with their details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to search for (case-insensitive, partial matches OK)",
                    },
                    "party": {
                        "type": "string",
                        "description": "Filter by party (e.g., 'Conservative', 'Liberal', 'NDP', 'Bloc')",
                    },
                    "riding": {
                        "type": "string",
                        "description": "Filter by riding/constituency name (partial match)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
            },
        ),
        Tool(
            name="get_mp_voting_history",
            description="Get recent voting history for a specific MP. Shows how they voted on recent bills and motions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mp_url": {
                        "type": "string",
                        "description": "The politician URL from search_mp results (e.g., '/politicians/pierre-poilievre/')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent votes to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["mp_url"],
            },
        ),
        Tool(
            name="get_vote_details",
            description="Get detailed information about a specific vote, including how individual MPs voted.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vote_url": {
                        "type": "string",
                        "description": "The vote URL (e.g., '/votes/45-1/43/')",
                    },
                    "include_ballots": {
                        "type": "boolean",
                        "description": "Include individual MP ballots (how each MP voted)",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of ballots to return if include_ballots is true",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 350,
                    },
                },
                "required": ["vote_url"],
            },
        ),
        Tool(
            name="find_mp_by_postal_code",
            description="Find your federal Member of Parliament by postal code. Returns MP name, party, riding, and contact information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "postal_code": {
                        "type": "string",
                        "description": "Canadian postal code (e.g., 'K1A 0A9' or 'k1a0a9')",
                    },
                },
                "required": ["postal_code"],
            },
        ),
        Tool(
            name="analyze_party_discipline",
            description="Analyze party discipline for a specific vote. Shows which MPs voted against their party's majority position.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vote_url": {
                        "type": "string",
                        "description": "The vote URL (e.g., '/votes/45-1/43/')",
                    },
                },
                "required": ["vote_url"],
            },
        ),
        Tool(
            name="get_bill_legislative_progress",
            description="Get detailed legislative progress and status for a Canadian bill. Shows current stage, completed stages, timeline, and next steps.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bill_number": {
                        "type": "string",
                        "description": "Bill number (e.g., 'C-2', 'S-222')",
                    },
                    "session": {
                        "type": "string",
                        "description": "Parliamentary session (e.g., '45-1'). If not provided, will search recent sessions.",
                    },
                },
                "required": ["bill_number"],
            },
        ),
        Tool(
            name="analyze_mp_voting_participation",
            description="Analyze an MP's voting participation and attendance. Shows participation rate, recent votes, and patterns of abstention or absence.",
            inputSchema={
                "type": "object",
                "properties": {
                    "politician_url": {
                        "type": "string",
                        "description": "Politician URL (e.g., '/politicians/pierre-poilievre/'). Use search_politician first if needed.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent votes to analyze (1-100)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["politician_url"],
            },
        ),
        Tool(
            name="search_topic_across_sources",
            description="Search for a topic or keyword across all data sources (debates, bills, Hansard, votes). Provides comprehensive coverage of parliamentary discussion on a topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or keywords to search across all sources",
                    },
                    "limit_per_source": {
                        "type": "integer",
                        "description": "Maximum results per source (1-20)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["topic"],
            },
        ),
    ]

    # Add CanLII tools if client is available
    if canlii_client:
        tools.extend([
            Tool(
                name="search_cases",
                description="Search Canadian case law via CanLII. Requires specifying a court/tribunal database ID (e.g., 'csc-scc' for Supreme Court).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID (e.g., 'csc-scc' for Supreme Court, 'fca-caf' for Federal Court of Appeal)",
                        },
                        "query": {
                            "type": "string",
                            "description": "Keywords to search in case law",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code ('en' or 'fr')",
                            "default": "en",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                        "published_after": {
                            "type": "string",
                            "description": "Filter cases published after this date (YYYY-MM-DD)",
                        },
                        "published_before": {
                            "type": "string",
                            "description": "Filter cases published before this date (YYYY-MM-DD)",
                        },
                        "decision_date_after": {
                            "type": "string",
                            "description": "Filter cases decided after this date (YYYY-MM-DD)",
                        },
                        "decision_date_before": {
                            "type": "string",
                            "description": "Filter cases decided before this date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["database_id", "query"],
                },
            ),
            Tool(
                name="get_case",
                description="Get detailed metadata for a specific case from CanLII.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID (e.g., 'csc-scc')",
                        },
                        "case_id": {
                            "type": "string",
                            "description": "Case ID",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code ('en' or 'fr')",
                            "default": "en",
                        },
                    },
                    "required": ["database_id", "case_id"],
                },
            ),
            Tool(
                name="get_case_citations",
                description="Get citation information for a case (cited cases, citing cases, or cited legislation).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID (e.g., 'csc-scc')",
                        },
                        "case_id": {
                            "type": "string",
                            "description": "Case ID",
                        },
                        "citation_type": {
                            "type": "string",
                            "description": "Type of citations to retrieve",
                            "enum": ["citedCases", "citingCases", "citedLegislations"],
                            "default": "citingCases",
                        },
                    },
                    "required": ["database_id", "case_id"],
                },
            ),
            Tool(
                name="search_legislation",
                description="Browse Canadian federal and provincial legislation via CanLII.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID (e.g., 'ca' for federal acts, 'car' for regulations)",
                            "default": "ca",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code ('en' or 'fr')",
                            "default": "en",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                },
            ),
            Tool(
                name="list_canlii_databases",
                description="List all available CanLII databases for case law or legislation. Use this to discover court/tribunal databases or legislation databases.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Type of databases to list",
                            "enum": ["cases", "legislation"],
                            "default": "cases",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code ('en' or 'fr')",
                            "default": "en",
                        },
                    },
                },
            ),
            Tool(
                name="search_federal_contracts",
                description="Search Canadian federal government contracts over $10,000. Find contracts by vendor, department, value, or year.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "vendor_name": {
                            "type": "string",
                            "description": "Vendor/contractor name to search for",
                        },
                        "department": {
                            "type": "string",
                            "description": "Department/buyer name to filter by",
                        },
                        "min_value": {
                            "type": "number",
                            "description": "Minimum contract value in CAD",
                        },
                        "max_value": {
                            "type": "number",
                            "description": "Maximum contract value in CAD",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Contract year to filter by",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_top_contractors",
                description="Get top government contractors by total contract value. Analyze which companies receive the most federal contracts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Filter by contract year",
                        },
                        "department": {
                            "type": "string",
                            "description": "Filter by department/buyer",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top contractors to return (1-50)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="search_political_contributions",
                description="Search federal political contributions to parties and candidates from Elections Canada data (2004-present).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contributor_name": {
                            "type": "string",
                            "description": "Donor name to search for",
                        },
                        "recipient_name": {
                            "type": "string",
                            "description": "Candidate or party name",
                        },
                        "political_party": {
                            "type": "string",
                            "description": "Party name (Liberal, Conservative, NDP, Green, Bloc Québécois, etc.)",
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Minimum contribution amount in CAD",
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Maximum contribution amount in CAD",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Contribution year",
                        },
                        "province": {
                            "type": "string",
                            "description": "Contributor province (e.g., 'ON', 'QC', 'BC')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_top_political_donors",
                description="Get top political donors by total contribution amount. Analyze major campaign contributors.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Filter by contribution year",
                        },
                        "political_party": {
                            "type": "string",
                            "description": "Filter by recipient party",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top donors to return (1-50)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_party_fundraising",
                description="Get total fundraising by political party. Compare party fundraising and contributor counts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Filter by contribution year",
                        },
                    },
                },
            ),
            Tool(
                name="search_federal_grants",
                description="Search federal grants and contributions over $25,000. Find grants by recipient, program, department, or amount.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "recipient_name": {
                            "type": "string",
                            "description": "Recipient organization or person name",
                        },
                        "program_name": {
                            "type": "string",
                            "description": "Program name to search for",
                        },
                        "department": {
                            "type": "string",
                            "description": "Department/owner organization name",
                        },
                        "min_value": {
                            "type": "number",
                            "description": "Minimum grant value in CAD",
                        },
                        "max_value": {
                            "type": "number",
                            "description": "Maximum grant value in CAD",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Agreement year",
                        },
                        "province": {
                            "type": "string",
                            "description": "Recipient province",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_top_grant_recipients",
                description="Get top grant recipients by total funding. Analyze which organizations receive the most federal grants.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Filter by agreement year",
                        },
                        "department": {
                            "type": "string",
                            "description": "Filter by department",
                        },
                        "program_name": {
                            "type": "string",
                            "description": "Filter by program",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top recipients to return (1-50)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="get_grant_program_spending",
                description="Get total spending by federal grant program. Compare program spending and recipient counts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Filter by agreement year",
                        },
                        "department": {
                            "type": "string",
                            "description": "Filter by department",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of programs to return (1-50)",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="search_departmental_travel",
                description="Search federal departmental travel expenses. Find travel by department, traveler name, destination, or amount.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "department": {
                            "type": "string",
                            "description": "Department name to filter by",
                        },
                        "name": {
                            "type": "string",
                            "description": "Traveler name to search for",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Travel destination",
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Minimum expense amount in CAD",
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Maximum expense amount in CAD",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Travel year",
                        },
                        "disclosure_group": {
                            "type": "string",
                            "description": "Disclosure group (e.g., 'Minister', 'Deputy Minister')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="search_departmental_hospitality",
                description="Search federal departmental hospitality expenses. Find hospitality events by department, host, location, or amount.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "department": {
                            "type": "string",
                            "description": "Department name to filter by",
                        },
                        "name": {
                            "type": "string",
                            "description": "Host name to search for",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location",
                        },
                        "min_amount": {
                            "type": "number",
                            "description": "Minimum expense amount in CAD",
                        },
                        "max_amount": {
                            "type": "number",
                            "description": "Maximum expense amount in CAD",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Hospitality year",
                        },
                        "disclosure_group": {
                            "type": "string",
                            "description": "Disclosure group (e.g., 'Minister', 'Deputy Minister')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (1-50)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="trace_money_flow",
                description="Follow the money through the political system. Trace connections between political contributions, lobbying activities, government contracts, and grants for an individual, organization, or company.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity_name": {
                            "type": "string",
                            "description": "Name of person or organization to trace (e.g., company name, individual donor)",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Focus on a specific year (optional)",
                        },
                        "include_lobbying": {
                            "type": "boolean",
                            "description": "Include lobbying activity in trace",
                            "default": True,
                        },
                        "include_contracts": {
                            "type": "boolean",
                            "description": "Include government contracts in trace",
                            "default": True,
                        },
                        "include_grants": {
                            "type": "boolean",
                            "description": "Include federal grants in trace",
                            "default": True,
                        },
                        "include_contributions": {
                            "type": "boolean",
                            "description": "Include political contributions in trace",
                            "default": True,
                        },
                    },
                    "required": ["entity_name"],
                },
            ),
            Tool(
                name="analyze_mp_finances",
                description="Comprehensive financial analysis of an MP including office expenses, political contributions received, lobbying interactions, and related entities.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mp_name": {
                            "type": "string",
                            "description": "MP name to analyze (e.g., 'Pierre Poilievre', 'Chrystia Freeland')",
                        },
                        "fiscal_year": {
                            "type": "integer",
                            "description": "Fiscal year for expense analysis",
                            "default": 2026,
                        },
                        "include_lobbying": {
                            "type": "boolean",
                            "description": "Include lobbying communications with this MP",
                            "default": True,
                        },
                    },
                    "required": ["mp_name"],
                },
            ),
            Tool(
                name="compare_party_funding",
                description="Compare political party fundraising sources, top donors, and funding patterns across parties.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "integer",
                            "description": "Year to analyze (optional, defaults to all available data)",
                        },
                        "include_donor_analysis": {
                            "type": "boolean",
                            "description": "Include top donor analysis for each party",
                            "default": True,
                        },
                        "min_donation": {
                            "type": "number",
                            "description": "Minimum donation amount to consider (filters out small donations)",
                        },
                    },
                },
            ),
            Tool(
                name="government_spending_analysis",
                description="Analyze government spending patterns across contracts, grants, and departmental expenses. Identify top recipients and spending trends.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "focus": {
                            "type": "string",
                            "description": "Analysis focus",
                            "enum": ["department", "recipient", "program", "overview"],
                            "default": "overview",
                        },
                        "department_name": {
                            "type": "string",
                            "description": "Specific department to analyze (if focus=department)",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Year to analyze",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top results to return",
                            "default": 20,
                            "minimum": 5,
                            "maximum": 50,
                        },
                    },
                },
            ),
            Tool(
                name="conflict_of_interest_check",
                description="Cross-reference political contributions, lobbying activities, and government contracts/grants to identify potential conflicts of interest or concerning patterns.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entity_name": {
                            "type": "string",
                            "description": "Name of person or organization to check",
                        },
                        "year": {
                            "type": "integer",
                            "description": "Focus on specific year (optional)",
                        },
                        "threshold_amount": {
                            "type": "number",
                            "description": "Minimum contract/grant amount to flag (default: $100,000)",
                            "default": 100000,
                        },
                    },
                    "required": ["entity_name"],
                },
            ),
        ])

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls.

    Note: All client operations are synchronous (using requests library),
    so we run them in a thread pool to avoid blocking the async event loop.
    """

    try:
        if name == "search_debates":
            try:
                query = arguments["query"]
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_debates called with query='{query}', limit={limit}")

                def _search_debates():
                    debates = []
                    query_lower = query.lower()

                    # Use islice to cap max examined debates (3x limit for filtering)
                    # This prevents fetching unlimited pages when searching
                    max_to_examine = limit * 3
                    for debate in islice(op_client.list_debates(), max_to_examine):
                        debate_text = " ".join([
                            str(debate.get("content", {}).get("en", "")),
                            str(debate.get("heading", {}).get("en", "")),
                            str(debate.get("speaker", {}).get("name", "")),
                        ]).lower()

                        if query_lower in debate_text:
                            debates.append({
                                "date": debate.get("date"),
                                "url": debate.get("url"),
                                "speaker": debate.get("speaker", {}).get("name"),
                                "content_preview": str(debate.get("content", {}).get("en", ""))[:300],
                            })
                            if len(debates) >= limit:
                                break
                    return debates

                debates = await run_sync(_search_debates)

                return [TextContent(
                    type="text",
                    text=f"Found {len(debates)} debate(s) matching '{query}':\n\n" +
                         "\n\n".join([
                             f"Date: {d['date']}\nSpeaker: {d['speaker']}\nPreview: {d['content_preview']}...\nURL: {d['url']}"
                             for d in debates
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for search_debates: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_debates")
                return [TextContent(type="text", text=f"Error searching debates: {sanitize_error_message(e)}")]

        elif name == "search_bills":
            try:
                query = arguments["query"]
                session = arguments.get("session")
                sponsor = arguments.get("sponsor")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_bills called with query='{query}', session={session}, sponsor={sponsor}, limit={limit}")

                query_upper = query.upper()
                is_bill_number = query_upper.startswith(('C-', 'S-')) and len(query) < 10

                bills = []

                # Try specific bill lookup via LEGISinfo if bill number detected
                if is_bill_number:
                    bill_code = query_upper.lower()

                    # If session provided, only try that session
                    # Otherwise, try recent sessions in order
                    sessions_to_try = [session] if session else ['45-1', '44-1', '43-2', '43-1', '42-1']

                    for sess in sessions_to_try:
                        try:
                            bill_data = await run_sync(legis_client.get_bill, sess, bill_code)

                            if isinstance(bill_data, list) and bill_data:
                                bill_info = bill_data[0]
                                # Format sponsor with title if available
                                sponsor_name = bill_info.get('SponsorPersonName', 'N/A')
                                sponsor_title = bill_info.get('SponsorAffiliationTitle', '')
                                sponsor_str = f"{sponsor_name} ({sponsor_title})" if sponsor_title else sponsor_name

                                # Extract debate sittings and committee info from bill stages
                                debate_sittings = []
                                committee_info_dict = None
                                committee_meetings = []

                                bill_stages = bill_info.get('BillStages', {})
                                house_stages = bill_stages.get('HouseBillStages', [])
                                for stage in house_stages:
                                    # Extract debate sittings
                                    for sitting in stage.get('Sittings', []):
                                        sitting_name = sitting.get('Name', '')
                                        if 'debate' in sitting_name.lower():
                                            debate_sittings.append({
                                                'date': sitting.get('Date', ''),
                                                'number': sitting.get('Number', ''),
                                                'name': sitting_name
                                            })

                                    # Extract committee information
                                    committee = stage.get('Committee')
                                    if committee and not committee_info_dict:
                                        committee_info_dict = committee

                                    # Extract committee meetings
                                    for meeting in stage.get('CommitteeMeetings', []):
                                        committee_meetings.append(meeting)

                                debate_info = ""
                                if debate_sittings:
                                    debate_info = "\n\nRecent Debates:\n" + "\n".join([
                                        f"  • {s['date'][:10]} (Sitting #{s['number']}): {s['name']}"
                                        for s in debate_sittings[-5:]  # Show last 5 debates
                                    ])

                                committee_display = ""
                                if committee_info_dict:
                                    committee_name = committee_info_dict.get('CommitteeName', 'N/A')
                                    committee_acronym = committee_info_dict.get('CommitteeAcronym', '')
                                    committee_display = f"\n\nCommittee: {committee_name} ({committee_acronym})"

                                    if committee_meetings:
                                        committee_display += "\nCommittee Meetings:\n" + "\n".join([
                                            f"  • Meeting #{m.get('Number')} on {m.get('Date', '')[:10]}"
                                            for m in committee_meetings
                                        ])

                                return [TextContent(
                                    type="text",
                                    text=f"Bill {bill_info.get('NumberCode', bill_info.get('Number'))}\n" +
                                         f"Title: {bill_info.get('LongTitle') or bill_info.get('ShortTitle')}\n" +
                                         f"Session: {sess}\n" +
                                         f"Status: {bill_info.get('StatusName', 'N/A')}\n" +
                                         f"Sponsor: {sponsor_str}\n" +
                                         f"Type: {bill_info.get('BillDocumentTypeName', 'N/A')}" +
                                         committee_display +
                                         debate_info +
                                         f"\n\nSource: LEGISinfo"
                                )]
                        except Exception as e:
                            logger.debug(f"Bill {bill_code} not found in session {sess}: {e}")
                            continue  # Try next session

                    # If we get here, LEGISinfo didn't find the bill in any session
                    # Fall through to OpenParliament search

                # Search in OpenParliament bills
                def _search_bills():
                    query_lower = query.lower()
                    found_bills = []

                    # Build query parameters for filtering
                    params = {}
                    if session:
                        params['session'] = session
                    if sponsor:
                        params['sponsor_politician'] = sponsor

                    # Use islice to cap max examined bills (10x limit, minimum 100)
                    # This provides better coverage since OpenParliament returns bills in unpredictable order
                    max_to_examine = max(100, limit * 10)
                    for bill in islice(op_client.list_bills(**params), max_to_examine):
                        bill_text = " ".join([
                            str(bill.get("number", "")),
                            str(bill.get("name", {}).get("en", "")),
                            str(bill.get("short_title", {}).get("en", "")),
                        ]).lower()

                        if query_lower in bill_text:
                            found_bills.append({
                                "number": bill.get("number"),
                                "name": bill.get("name", {}).get("en"),
                                "short_title": bill.get("short_title", {}).get("en"),
                                "url": bill.get("url"),
                            })
                            if len(found_bills) >= limit:
                                break
                    return found_bills

                bills = await run_sync(_search_bills)

                # Add helpful guidance if no bills found
                if len(bills) == 0:
                    help_text = f"Found 0 bill(s) matching '{query}'."
                    if is_bill_number:
                        help_text += "\n\nTroubleshooting tips for bill number searches:"
                        help_text += "\n• Bill may not exist in the searched sessions"
                        if session:
                            help_text += f"\n• Try searching without specifying session (currently: {session})"
                        help_text += "\n• Verify bill number format (e.g., 'C-3', 'S-12')"
                        help_text += "\n• Check recent sessions: 45-1 (current), 44-1, 43-2, 43-1, 42-1"
                    else:
                        help_text += "\n\nTips:"
                        help_text += "\n• Try different search terms or keywords"
                        help_text += "\n• For specific bills, use the bill number (e.g., 'C-3')"
                    return [TextContent(type="text", text=help_text)]

                return [TextContent(
                    type="text",
                    text=f"Found {len(bills)} bill(s) matching '{query}':\n\n" +
                         "\n\n".join([
                             f"Number: {b['number']}\n" +
                             f"Name: {(b['name'] or 'N/A')[:200]}{'...' if b['name'] and len(b['name']) > 200 else ''}\n" +
                             f"Short Title: {(b['short_title'] or 'N/A')[:150]}{'...' if b['short_title'] and len(b['short_title']) > 150 else ''}\n" +
                             f"URL: {b['url']}"
                             for b in bills
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for search_bills: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_bills")
                return [TextContent(type="text", text=f"Error searching bills: {sanitize_error_message(e)}")]

        elif name == "search_hansard":
            try:
                query = arguments["query"]
                sitting_url = arguments.get("sitting", "latest/hansard")
                limit = validate_limit(arguments.get("limit"), default=5, max_val=20)
                logger.info(f"search_hansard called with query='{query}', sitting='{sitting_url}', limit={limit}")

                sitting = await run_sync(hansard_client.get_sitting, sitting_url, parse=True)

                if not sitting or not sitting.sections:
                    return [TextContent(
                        type="text",
                        text=f"No Hansard data available or no matches found for '{query}'"
                    )]

                matches = []
                query_lower = query.lower()

                for section in sitting.sections:
                    for speech in section.speeches:
                        if len(matches) >= limit:
                            break

                        if speech.text and query_lower in speech.text.lower():
                            text_lower = speech.text.lower()
                            match_idx = text_lower.find(query_lower)

                            start = max(0, match_idx - 200)
                            end = min(len(speech.text), match_idx + len(query) + 200)
                            context = speech.text[start:end]

                            matches.append({
                                "speaker": speech.speaker_name,
                                "party": speech.party,
                                "riding": speech.riding,
                                "context": context,
                            })

                return [TextContent(
                    type="text",
                    text=f"Hansard Date: {sitting.date}\n" +
                         f"Found {len(matches)} speech(es) matching '{query}':\n\n" +
                         "\n\n---\n\n".join([
                             f"Speaker: {m['speaker']} ({m['party']}, {m['riding']})\nContext: ...{m['context']}..."
                             for m in matches
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for search_hansard: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_hansard")
                return [TextContent(type="text", text=f"Error searching Hansard: {sanitize_error_message(e)}")]

        elif name == "search_bill_debates":
            try:
                bill_number = arguments["bill_number"].strip()
                session = arguments.get("session")
                search_query = arguments.get("search_query", "").strip()
                limit = validate_limit(arguments.get("limit"), default=5, max_val=20)
                logger.info(f"search_bill_debates called with bill_number='{bill_number}', session={session}, search_query='{search_query}', limit={limit}")

                # Normalize bill number
                bill_code = bill_number.upper().replace('BILL ', '').strip().lower()

                # Try to get bill data from LEGISinfo
                sessions_to_try = [session] if session else ['45-1', '44-1', '43-2', '43-1']
                bill_data = None
                found_session = None

                for sess in sessions_to_try:
                    try:
                        result = await run_sync(legis_client.get_bill, sess, bill_code)
                        if isinstance(result, list) and result:
                            bill_data = result[0]
                            found_session = sess
                            break
                    except Exception:
                        continue

                if not bill_data:
                    return [TextContent(
                        type="text",
                        text=f"Bill {bill_number} not found in LEGISinfo. Try specifying the session (e.g., '45-1')."
                    )]

                # Extract debate sittings
                debate_sittings = []
                bill_stages = bill_data.get('BillStages', {})
                house_stages = bill_stages.get('HouseBillStages', [])
                for stage in house_stages:
                    for sitting in stage.get('Sittings', []):
                        sitting_name = sitting.get('Name', '')
                        if 'debate' in sitting_name.lower():
                            debate_sittings.append({
                                'date': sitting.get('Date', ''),
                                'number': sitting.get('Number', ''),
                                'name': sitting_name
                            })

                if not debate_sittings:
                    return [TextContent(
                        type="text",
                        text=f"No debate sittings found for Bill {bill_number} in session {found_session}."
                    )]

                # Search each debate sitting for the bill
                all_matches = []
                for sitting_info in debate_sittings:
                    sitting_date = sitting_info['date'][:10]  # YYYY-MM-DD
                    sitting_number = sitting_info['number']

                    # Build direct XML URL for this sitting
                    # Format: https://www.ourcommons.ca/Content/House/{parl}{sess}/Debates/{sitting_padded}/HAN{sitting_padded}-E.XML
                    parl_num = found_session.split('-')[0]
                    sess_num = found_session.split('-')[1]
                    sitting_padded = sitting_number.zfill(3)
                    xml_url = f"https://www.ourcommons.ca/Content/House/{parl_num}{sess_num}/Debates/{sitting_padded}/HAN{sitting_padded}-E.XML"

                    try:
                        # Fetch and parse XML directly
                        def _fetch_and_parse():
                            response = hansard_client.session.get(xml_url, headers={'Accept': 'application/xml'})
                            response.raise_for_status()
                            xml_text = response.content.decode('utf-8-sig')
                            return hansard_client.parse_sitting(xml_text, source_url=xml_url)

                        sitting = await run_sync(_fetch_and_parse)

                        if not sitting or not sitting.sections:
                            continue

                        # Build search terms: bill number + optional search query
                        search_terms = [bill_number.lower(), f"bill {bill_code}"]
                        if search_query:
                            search_terms.append(search_query.lower())

                        sitting_matches = []
                        for section in sitting.sections:
                            for speech in section.speeches:
                                if len(sitting_matches) >= limit:
                                    break

                                if not speech.text:
                                    continue

                                text_lower = speech.text.lower()

                                # Check if any search term is in the speech
                                match_found = any(term in text_lower for term in search_terms)

                                if match_found:
                                    # Find context around bill mention
                                    match_idx = text_lower.find(bill_code)
                                    if match_idx == -1:
                                        match_idx = text_lower.find(bill_number.lower())

                                    if match_idx >= 0:
                                        start = max(0, match_idx - 200)
                                        end = min(len(speech.text), match_idx + len(bill_number) + 200)
                                        context = speech.text[start:end]
                                    else:
                                        # If searching by keyword, show beginning of speech
                                        context = speech.text[:400]

                                    sitting_matches.append({
                                        "date": sitting_date,
                                        "sitting_number": sitting_number,
                                        "speaker": speech.speaker_name,
                                        "party": speech.party,
                                        "riding": speech.riding,
                                        "context": context,
                                    })

                        all_matches.extend(sitting_matches)

                    except Exception as e:
                        logger.warning(f"Could not fetch Hansard for sitting {sitting_number}: {e}")
                        continue

                if not all_matches:
                    return [TextContent(
                        type="text",
                        text=f"Found {len(debate_sittings)} debate sitting(s) for Bill {bill_number}, but no speeches matched the search criteria.\n\n" +
                             "Debate sittings:\n" + "\n".join([
                                 f"  • {s['date'][:10]} (Sitting #{s['number']})"
                                 for s in debate_sittings
                             ])
                    )]

                return [TextContent(
                    type="text",
                    text=f"Bill {bill_number} ({found_session})\n" +
                         f"Found {len(all_matches)} speech(es) across {len(debate_sittings)} debate sitting(s):\n\n" +
                         "\n\n---\n\n".join([
                             f"Date: {m['date']} (Sitting #{m['sitting_number']})\n" +
                             f"Speaker: {m['speaker']} ({m['party']}, {m['riding']})\n" +
                             f"Context: ...{m['context']}..."
                             for m in all_matches
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for search_bill_debates: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_bill_debates")
                return [TextContent(type="text", text=f"Error searching bill debates: {sanitize_error_message(e)}")]

        elif name == "get_committee_evidence":
            try:
                parliament = arguments["parliament"]
                session = arguments["session"]
                committee = arguments["committee"].upper()
                meeting = arguments["meeting"]
                search_query = arguments.get("search")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)

                logger.info(f"get_committee_evidence called with {parliament}-{session}/{committee}/meeting-{meeting}")

                # Build the committee evidence URL
                # Format: /DocumentViewer/en/{parliament}-{session}/{COMMITTEE}/meeting-{number}/evidence
                slug = f"{parliament}-{session}/{committee}/meeting-{meeting}/evidence"

                # Fetch and parse committee evidence (same format as Hansard)
                sitting = await run_sync(hansard_client.get_sitting, slug, parse=True)

                if not sitting or not sitting.sections:
                    return [TextContent(
                        type="text",
                        text=f"No evidence available for {committee} meeting {meeting}"
                    )]

                # If searching, filter speeches
                if search_query:
                    matches = []
                    query_lower = search_query.lower()

                    for section in sitting.sections:
                        for speech in section.speeches:
                            if len(matches) >= limit:
                                break

                            if speech.text and query_lower in speech.text.lower():
                                text_lower = speech.text.lower()
                                match_idx = text_lower.find(query_lower)

                                start = max(0, match_idx - 200)
                                end = min(len(speech.text), match_idx + len(search_query) + 200)
                                context = speech.text[start:end]

                                matches.append({
                                    "speaker": speech.speaker_name,
                                    "party": speech.party,
                                    "riding": speech.riding,
                                    "context": context,
                                })

                    return [TextContent(
                        type="text",
                        text=f"Committee: {committee}\nMeeting: {meeting}\nDate: {sitting.date}\n" +
                             f"Found {len(matches)} speech(es) matching '{search_query}':\n\n" +
                             "\n\n---\n\n".join([
                                 f"Speaker: {m['speaker']} ({m['party']}, {m['riding']})\nContext: ...{m['context']}..."
                                 for m in matches
                             ])
                    )]

                # No search - return all speeches (limited)
                all_speeches = []
                for section in sitting.sections:
                    for speech in section.speeches[:limit]:
                        all_speeches.append({
                            "speaker": speech.speaker_name or "Unknown",
                            "party": speech.party or "N/A",
                            "riding": speech.riding or "N/A",
                            "text_preview": speech.text[:300] if speech.text else "No text"
                        })
                        if len(all_speeches) >= limit:
                            break
                    if len(all_speeches) >= limit:
                        break

                return [TextContent(
                    type="text",
                    text=f"Committee: {committee}\nMeeting: {meeting}\nDate: {sitting.date}\n" +
                         f"Evidence (showing {len(all_speeches)} speeches):\n\n" +
                         "\n\n---\n\n".join([
                             f"Speaker: {s['speaker']} ({s['party']}, {s['riding']})\n{s['text_preview']}..."
                             for s in all_speeches
                         ])
                )]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_committee_evidence: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for get_committee_evidence: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_committee_evidence")
                return [TextContent(type="text", text=f"Error fetching committee evidence: {sanitize_error_message(e)}")]

        elif name == "list_debates":
            try:
                limit = validate_limit(arguments.get("limit"), default=5, max_val=100)
                offset = arguments.get("offset", 0)
                date_after = arguments.get("date_after")
                date_before = arguments.get("date_before")

                if not isinstance(offset, int) or offset < 0:
                    raise ValueError("offset must be a non-negative integer")
                logger.info(f"list_debates called with limit={limit}, offset={offset}, date_after={date_after}, date_before={date_before}")

                # Build query parameters for date filtering
                params = {'offset': offset}
                if date_after:
                    params['date__gte'] = date_after
                if date_before:
                    params['date__lte'] = date_before

                # Use islice to properly limit results (limit param only controls page size, not total)
                debates = await run_sync(lambda: list(islice(op_client.list_debates(**params), limit)))

                return [TextContent(
                    type="text",
                    text=f"Recent debates (limit={limit}, offset={offset}):\n\n" +
                         "\n\n".join([
                             f"Date: {d.get('date')}\nSpeaker: {d.get('speaker', {}).get('name')}\n" +
                             f"Heading: {d.get('heading', {}).get('en', 'N/A')}\nURL: {d.get('url')}"
                             for d in debates
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for list_debates: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in list_debates")
                return [TextContent(type="text", text=f"Error listing debates: {sanitize_error_message(e)}")]

        elif name == "get_bill":
            try:
                session = arguments["session"]
                code = arguments["code"]
                logger.info(f"get_bill called with session={session}, code={code}")

                result = await run_sync(legis_client.get_bill, session, code)
                if isinstance(result, list) and result:
                    bill = result[0]

                    # Format sponsor with title if available
                    sponsor_name = bill.get('SponsorPersonName', 'N/A')
                    sponsor_title = bill.get('SponsorAffiliationTitle', '')
                    sponsor_str = f"{sponsor_name} ({sponsor_title})" if sponsor_title else sponsor_name

                    # Extract debate sittings and committee info from bill stages
                    debate_sittings = []
                    committee_info_dict = None
                    committee_meetings = []

                    bill_stages = bill.get('BillStages', {})
                    house_stages = bill_stages.get('HouseBillStages', [])
                    for stage in house_stages:
                        # Extract debate sittings
                        for sitting in stage.get('Sittings', []):
                            sitting_name = sitting.get('Name', '')
                            if 'debate' in sitting_name.lower():
                                debate_sittings.append({
                                    'date': sitting.get('Date', ''),
                                    'number': sitting.get('Number', ''),
                                    'name': sitting_name
                                })

                        # Extract committee information
                        committee = stage.get('Committee')
                        if committee and not committee_info_dict:
                            committee_info_dict = committee

                        # Extract committee meetings
                        for meeting in stage.get('CommitteeMeetings', []):
                            committee_meetings.append(meeting)

                    debate_info = ""
                    if debate_sittings:
                        debate_info = "\n\nDebate Sittings:\n" + "\n".join([
                            f"  • {s['date'][:10]} (Sitting #{s['number']}): {s['name']}"
                            for s in debate_sittings
                        ])

                    committee_display = ""
                    if committee_info_dict:
                        committee_name = committee_info_dict.get('CommitteeName', 'N/A')
                        committee_acronym = committee_info_dict.get('CommitteeAcronym', '')
                        committee_display = f"\n\nCommittee: {committee_name} ({committee_acronym})"

                        if committee_meetings:
                            committee_display += "\nCommittee Meetings:\n" + "\n".join([
                                f"  • Meeting #{m.get('Number')} on {m.get('Date', '')[:10]}"
                                for m in committee_meetings
                            ])

                    return [TextContent(
                        type="text",
                        text=f"Bill {bill.get('NumberCode', bill.get('Number'))}\n" +
                             f"Long Title: {bill.get('LongTitle')}\n" +
                             f"Short Title: {bill.get('ShortTitle') or 'N/A'}\n" +
                             f"Session: {session}\n" +
                             f"Status: {bill.get('StatusName', 'N/A')}\n" +
                             f"Sponsor: {sponsor_str}\n" +
                             f"Type: {bill.get('BillDocumentTypeName', 'N/A')}" +
                             committee_display +
                             debate_info
                    )]

                return [TextContent(type="text", text=f"Bill data: {result}")]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_bill: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_bill")
                return [TextContent(type="text", text=f"Error getting bill: {sanitize_error_message(e)}")]

        elif name == "list_mps":
            try:
                limit = validate_limit(arguments.get("limit"), default=10, max_val=100)
                logger.info(f"list_mps called with limit={limit}")

                # Use islice to properly limit results (limit param only controls page size, not total)
                mps = await run_sync(lambda: list(islice(op_client.list_mps(), limit)))

                return [TextContent(
                    type="text",
                    text=f"Current Members of Parliament (limit={limit}):\n\n" +
                         "\n".join([
                             f"- {mp.get('name')} ({mp.get('party', {}).get('short_name', {}).get('en', 'N/A')}) - {mp.get('riding', {}).get('name', {}).get('en', 'N/A')}"
                             for mp in mps
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for list_mps: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in list_mps")
                return [TextContent(type="text", text=f"Error listing MPs: {sanitize_error_message(e)}")]

        elif name == "get_mp_expenses":
            try:
                search_term = arguments["search_term"]
                search_type = arguments.get("search_type", "name")
                fiscal_year = arguments.get("fiscal_year", 2026)
                quarter = arguments.get("quarter", 1)
                logger.info(f"get_mp_expenses called with search_term='{search_term}', search_type={search_type}, fiscal_year={fiscal_year}, quarter={quarter}")

                # Search based on type
                if search_type == "name":
                    results = await run_sync(expenditure_client.search_by_name, search_term, fiscal_year, quarter)
                elif search_type == "party":
                    results = await run_sync(expenditure_client.search_by_party, search_term, fiscal_year, quarter)
                elif search_type == "constituency":
                    results = await run_sync(expenditure_client.search_by_constituency, search_term, fiscal_year, quarter)
                else:
                    return [TextContent(type="text", text=f"Invalid search_type: {search_type}")]

                if not results:
                    return [TextContent(
                        type="text",
                        text=f"No MPs found matching '{search_term}' ({search_type}) for FY {fiscal_year} Q{quarter}."
                    )]

                # Format results
                quarter_names = {1: "Q1 (Apr-Jun)", 2: "Q2 (Jul-Sep)", 3: "Q3 (Oct-Dec)", 4: "Q4 (Jan-Mar)"}
                quarter_display = quarter_names.get(quarter, f"Q{quarter}")

                output = f"MP Expenses for FY {fiscal_year-1}-{fiscal_year} {quarter_display}\n"
                output += f"Search: '{search_term}' ({search_type})\n"
                output += f"Found {len(results)} MP(s)\n\n"

                for exp in results:
                    output += f"MP: {exp.name}\n"
                    output += f"Constituency: {exp.constituency}\n"
                    output += f"Party: {exp.caucus}\n"
                    output += f"Expenses:\n"
                    output += f"  Salaries: ${exp.salaries:,.2f}\n"
                    output += f"  Travel: ${exp.travel:,.2f}\n"
                    output += f"  Hospitality: ${exp.hospitality:,.2f}\n"
                    output += f"  Contracts: ${exp.contracts:,.2f}\n"
                    output += f"  TOTAL: ${exp.total:,.2f}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for get_mp_expenses: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_mp_expenses")
                return [TextContent(type="text", text=f"Error getting MP expenses: {sanitize_error_message(e)}")]

        elif name == "search_mp_expenses":
            try:
                mode = arguments["mode"]
                fiscal_year = arguments.get("fiscal_year", 2026)
                quarter = arguments.get("quarter", 1)
                logger.info(f"search_mp_expenses called with mode={mode}, fiscal_year={fiscal_year}, quarter={quarter}")

                quarter_names = {1: "Q1 (Apr-Jun)", 2: "Q2 (Jul-Sep)", 3: "Q3 (Oct-Dec)", 4: "Q4 (Jan-Mar)"}
                quarter_display = quarter_names.get(quarter, f"Q{quarter}")

                if mode == "top_spenders":
                    category = arguments.get("category", "total")
                    limit = validate_limit(arguments.get("limit"), default=10, max_val=50)

                    results = await run_sync(expenditure_client.get_top_spenders, category, fiscal_year, quarter, limit)

                    output = f"Top {limit} MP Spenders - {category.title()}\n"
                    output += f"FY {fiscal_year-1}-{fiscal_year} {quarter_display}\n\n"

                    for i, exp in enumerate(results, 1):
                        amount = getattr(exp, category) if category != 'total' else exp.total
                        output += f"{i}. {exp.name} ({exp.caucus})\n"
                        output += f"   Constituency: {exp.constituency}\n"
                        output += f"   {category.title()}: ${amount:,.2f}\n"
                        if category == 'total':
                            output += f"   Breakdown: Salaries ${exp.salaries:,.2f}, Travel ${exp.travel:,.2f}, Hospitality ${exp.hospitality:,.2f}, Contracts ${exp.contracts:,.2f}\n"
                        output += "\n"

                    return [TextContent(type="text", text=output)]

                elif mode == "party_averages":
                    averages = await run_sync(expenditure_client.get_party_averages, fiscal_year, quarter)

                    output = f"Party Average Expenses\n"
                    output += f"FY {fiscal_year-1}-{fiscal_year} {quarter_display}\n\n"

                    for party, data in sorted(averages.items()):
                        output += f"{party} ({data['count']} MPs)\n"
                        output += f"  Avg Salaries: ${data['avg_salaries']:,.2f}\n"
                        output += f"  Avg Travel: ${data['avg_travel']:,.2f}\n"
                        output += f"  Avg Hospitality: ${data['avg_hospitality']:,.2f}\n"
                        output += f"  Avg Contracts: ${data['avg_contracts']:,.2f}\n"
                        output += f"  Avg Total: ${data['avg_total']:,.2f}\n"
                        output += "\n"

                    return [TextContent(type="text", text=output)]

                else:
                    return [TextContent(type="text", text=f"Invalid mode: {mode}")]

            except ValueError as e:
                logger.warning(f"Invalid input for search_mp_expenses: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_mp_expenses")
                return [TextContent(type="text", text=f"Error searching MP expenses: {sanitize_error_message(e)}")]

        elif name == "list_votes":
            try:
                limit = validate_limit(arguments.get("limit"), default=10, max_val=100)
                date_after = arguments.get("date_after")
                date_before = arguments.get("date_before")
                result = arguments.get("result")

                logger.info(f"list_votes called with limit={limit}, date_after={date_after}, date_before={date_before}, result={result}")

                # Build query parameters for filtering
                params = {}
                if date_after:
                    params['date__gte'] = date_after
                if date_before:
                    params['date__lte'] = date_before
                if result:
                    params['result'] = result

                # Run synchronous API call in thread pool to avoid blocking
                # Use islice to properly limit results (limit param only controls page size, not total)
                votes = await asyncio.to_thread(lambda: list(islice(op_client.list_votes(**params), limit)))

                return [TextContent(
                    type="text",
                    text=f"Recent parliamentary votes (limit={limit}):\n\n" +
                         "\n\n".join([
                             f"Date: {v.get('date')}\nNumber: {v.get('number')}\n" +
                             f"Description: {v.get('description', {}).get('en', 'N/A')[:200]}{'...' if len(v.get('description', {}).get('en', '')) > 200 else ''}\n" +
                             f"Result: {v.get('result')}\nURL: {v.get('url')}"
                             for v in votes
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for list_votes: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in list_votes")
                return [TextContent(type="text", text=f"Error listing votes: {sanitize_error_message(e)}")]

        elif name == "list_committees":
            try:
                limit = validate_limit(arguments.get("limit"), default=10, max_val=100)
                logger.info(f"list_committees called with limit={limit}")

                # Run synchronous API call in thread pool to avoid blocking
                # Use islice to properly limit results
                committees = await asyncio.to_thread(lambda: list(islice(op_client.list_committees(), limit)))

                return [TextContent(
                    type="text",
                    text=f"Parliamentary committees (limit={limit}):\n\n" +
                         "\n\n".join([
                             f"Name: {c.get('name', {}).get('en', 'N/A')}\n" +
                             f"Short Name: {c.get('short_name', {}).get('en', 'N/A')}\n" +
                             f"URL: {c.get('url')}"
                             for c in committees
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for list_committees: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in list_committees")
                return [TextContent(type="text", text=f"Error listing committees: {sanitize_error_message(e)}")]

        elif name == "get_committee_details":
            try:
                committee_url = arguments["committee_url"]
                logger.info(f"get_committee_details called with committee_url='{committee_url}'")

                # Fetch committee details
                committee = await run_sync(op_client.get_committee, committee_url)

                if not committee:
                    return [TextContent(type="text", text=f"Committee not found: {committee_url}")]

                # Format output
                output = f"Committee: {committee.get('name', {}).get('en', 'N/A')}\n"
                output += f"Short Name: {committee.get('short_name', {}).get('en', 'N/A')}\n"
                output += f"Parent: {committee.get('parent', {}).get('name', {}).get('en', 'N/A') if committee.get('parent') else 'None'}\n"
                output += f"URL: {committee.get('url', 'N/A')}\n\n"

                # Members
                members = committee.get('memberships', [])
                if members:
                    output += f"Members ({len(members)}):\n"
                    for member in members[:50]:  # Limit to 50 members
                        politician = member.get('politician', {})
                        role = member.get('role', 'Member')
                        output += f"  • {politician.get('name', 'N/A')} ({role})\n"
                else:
                    output += "Members: No membership data available\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for get_committee_details: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_committee_details")
                return [TextContent(type="text", text=f"Error getting committee details: {sanitize_error_message(e)}")]

        elif name == "get_politician_profile":
            try:
                politician_url = arguments["politician_url"]
                logger.info(f"get_politician_profile called with politician_url='{politician_url}'")

                # Fetch politician profile
                politician = await run_sync(op_client.get_politician, politician_url)

                if not politician:
                    return [TextContent(type="text", text=f"Politician not found: {politician_url}")]

                # Format output
                output = f"Name: {politician.get('name', 'N/A')}\n"

                # Current member info
                if politician.get('current_member'):
                    current_riding = politician.get('current_riding', {})
                    current_party = politician.get('current_party', {})
                    output += f"Status: Current MP\n"
                    output += f"Riding: {current_riding.get('name', {}).get('en', 'N/A')}\n"
                    output += f"Party: {current_party.get('name', {}).get('en', 'N/A')}\n"
                else:
                    output += f"Status: Former MP\n"

                # Biographical info
                if politician.get('gender'):
                    output += f"Gender: {politician.get('gender')}\n"

                # Roles
                roles = politician.get('current_roles', [])
                if roles:
                    output += f"\nCurrent Roles:\n"
                    for role in roles[:10]:
                        output += f"  • {role.get('role', 'N/A')}\n"

                # Membership history
                memberships = politician.get('memberships', [])
                if memberships:
                    output += f"\nRiding History ({len(memberships)} total):\n"
                    for membership in memberships[:5]:  # Show most recent 5
                        riding = membership.get('riding', {})
                        party = membership.get('party', {})
                        start = membership.get('start_date', 'Unknown')
                        end = membership.get('end_date', 'Present')
                        output += f"  • {riding.get('name', {}).get('en', 'N/A')} ({party.get('short_name', {}).get('en', 'N/A')}) - {start} to {end}\n"

                output += f"\nURL: {politician.get('url', 'N/A')}\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for get_politician_profile: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_politician_profile")
                return [TextContent(type="text", text=f"Error getting politician profile: {sanitize_error_message(e)}")]

        elif name == "search_petitions":
            try:
                keyword = arguments.get("keyword")
                sponsor_name = arguments.get("sponsor_name")
                category = arguments.get("category", "All")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_petitions called with keyword='{keyword}', sponsor='{sponsor_name}', category={category}, limit={limit}")

                # Search petitions
                results = await run_sync(
                    petitions_client.search_petitions,
                    keyword=keyword,
                    sponsor_name=sponsor_name,
                    category=category,
                    limit=limit
                )

                if not results:
                    search_desc = []
                    if keyword:
                        search_desc.append(f"keyword '{keyword}'")
                    if sponsor_name:
                        search_desc.append(f"sponsor '{sponsor_name}'")
                    search_desc = " and ".join(search_desc) if search_desc else "your criteria"
                    return [TextContent(type="text", text=f"No petitions found matching {search_desc} in category '{category}'.")]

                # Format output
                output = f"Found {len(results)} petition(s)\n"
                if keyword or sponsor_name:
                    filters = []
                    if keyword:
                        filters.append(f"keyword: {keyword}")
                    if sponsor_name:
                        filters.append(f"sponsor: {sponsor_name}")
                    output += f"Filters: {', '.join(filters)}\n"
                output += f"Category: {category}\n\n"

                for i, petition in enumerate(results, 1):
                    output += f"{i}. {petition.petition_number}: {petition.title}\n"
                    output += f"   Status: {petition.status_name}\n"
                    output += f"   Signatures: {petition.signature_count:,}\n"
                    if petition.sponsor:
                        output += f"   Sponsor: {petition.sponsor.full_name} ({petition.sponsor.constituency}, {petition.sponsor.caucus})\n"
                    if petition.index_terms:
                        output += f"   Topics: {', '.join(petition.index_terms[:5])}\n"
                    if petition.signature_opening_date:
                        output += f"   Period: {petition.signature_opening_date} to {petition.signature_closing_date}\n"
                    if petition.government_response_date:
                        output += f"   Government Response: {petition.government_response_date}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for search_petitions: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_petitions")
                return [TextContent(type="text", text=f"Error searching petitions: {sanitize_error_message(e)}")]

        elif name == "get_petition_details":
            try:
                petition_number = arguments["petition_number"]
                logger.info(f"get_petition_details called with petition_number='{petition_number}'")

                # Get specific petition
                petition = await run_sync(petitions_client.get_petition, petition_number)

                if not petition:
                    return [TextContent(type="text", text=f"Petition {petition_number} not found.")]

                # Format detailed output
                output = f"Petition {petition.petition_number}\n"
                output += f"{'=' * 60}\n\n"
                output += f"Title: {petition.title}\n"
                output += f"Status: {petition.status_name}\n"
                if petition.status_reached_date:
                    output += f"Status Date: {petition.status_reached_date}\n"
                output += f"Parliament: {petition.parliament_number}-{petition.session}\n"
                output += f"Signatures: {petition.signature_count:,}\n\n"

                # Petitioner and sponsor
                if petition.petitioner_first_name or petition.petitioner_last_name:
                    output += f"Petitioner: {petition.petitioner_first_name or ''} {petition.petitioner_last_name or ''}\n"
                if petition.sponsor:
                    output += f"Sponsor MP: {petition.sponsor.full_name}\n"
                    output += f"  Constituency: {petition.sponsor.constituency}\n"
                    output += f"  Party: {petition.sponsor.caucus}\n"
                output += "\n"

                # Signature period
                if petition.signature_opening_date:
                    output += f"Signature Period:\n"
                    output += f"  Opening: {petition.signature_opening_date}\n"
                    output += f"  Closing: {petition.signature_closing_date}\n\n"

                # Dates
                if petition.certification_date:
                    output += f"Certified: {petition.certification_date}\n"
                if petition.presented_date:
                    output += f"Presented to House: {petition.presented_date}\n"
                if petition.government_response_date:
                    output += f"Government Response: {petition.government_response_date}\n"
                if any([petition.certification_date, petition.presented_date, petition.government_response_date]):
                    output += "\n"

                # Topics
                if petition.index_terms:
                    output += f"Topics: {', '.join(petition.index_terms)}\n\n"

                # Provincial breakdown
                if petition.provincial_signatures:
                    output += "Signatures by Province/Territory:\n"
                    for ps in sorted(petition.provincial_signatures, key=lambda x: x.signature_count, reverse=True):
                        output += f"  {ps.province}: {ps.signature_count:,}\n"
                    output += "\n"

                # Grievances (Whereas clauses)
                if petition.grievances_text:
                    output += "Grievances:\n"
                    output += f"{petition.grievances_text}\n\n"

                # Prayer (Call to Action)
                if petition.prayer_text:
                    output += "Petition Call to Action:\n"
                    output += f"{petition.prayer_text}\n\n"

                # Government Response
                if petition.response_text:
                    output += "Government Response:\n"
                    output += f"{petition.response_text}\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for get_petition_details: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_petition_details")
                return [TextContent(type="text", text=f"Error getting petition details: {sanitize_error_message(e)}")]

        elif name == "get_mp_petitions":
            try:
                mp_name = arguments["mp_name"]
                category = arguments.get("category", "All")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"get_mp_petitions called with mp_name='{mp_name}', category={category}, limit={limit}")

                # Get petitions by MP
                results = await run_sync(
                    petitions_client.get_petitions_by_mp,
                    mp_name,
                    category=category
                )

                if not results:
                    return [TextContent(type="text", text=f"No petitions found for MP '{mp_name}' in category '{category}'.")]

                # Apply limit
                results = results[:limit]

                # Format output
                sponsor_info = results[0].sponsor if results else None
                output = f"Petitions Sponsored by {sponsor_info.full_name if sponsor_info else mp_name}\n"
                if sponsor_info:
                    output += f"{sponsor_info.constituency} ({sponsor_info.caucus})\n"
                output += f"Category: {category}\n"
                output += f"Found: {len(results)} petition(s)\n\n"

                # Calculate statistics
                total_signatures = sum(p.signature_count for p in results)
                avg_signatures = total_signatures // len(results) if results else 0

                with_responses = sum(1 for p in results if p.government_response_date)
                presented = sum(1 for p in results if p.presented_date)

                output += f"Statistics:\n"
                output += f"  Total Signatures: {total_signatures:,}\n"
                output += f"  Average Signatures: {avg_signatures:,}\n"
                output += f"  Presented to House: {presented}\n"
                output += f"  With Government Response: {with_responses}\n\n"

                # List petitions
                for i, petition in enumerate(results, 1):
                    output += f"{i}. {petition.petition_number}: {petition.title}\n"
                    output += f"   Status: {petition.status_name}\n"
                    output += f"   Signatures: {petition.signature_count:,}\n"
                    if petition.index_terms:
                        output += f"   Topics: {', '.join(petition.index_terms[:3])}\n"
                    if petition.government_response_date:
                        output += f"   ✓ Government responded: {petition.government_response_date}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for get_mp_petitions: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for get_mp_petitions: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_mp_petitions")
                return [TextContent(type="text", text=f"Error getting MP petitions: {sanitize_error_message(e)}")]

        elif name == "search_lobbying_registrations":
            try:
                client_name = arguments.get("client_name")
                lobbyist_name = arguments.get("lobbyist_name")
                subject_keyword = arguments.get("subject_keyword")
                institution = arguments.get("institution")
                active_only = arguments.get("active_only", True)
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_lobbying_registrations called with client={client_name}, lobbyist={lobbyist_name}, subject={subject_keyword}, active_only={active_only}")

                # Search registrations
                results = await run_sync(
                    lobbying_client.search_registrations,
                    client_name=client_name,
                    lobbyist_name=lobbyist_name,
                    subject_keyword=subject_keyword,
                    institution=institution,
                    active_only=active_only,
                    limit=limit
                )

                if not results:
                    return [TextContent(type="text", text="No lobbying registrations found matching your criteria.")]

                # Format output
                output = f"Found {len(results)} lobbying registration(s)\n"
                if active_only:
                    output += "Status: Active only\n"
                output += "\n"

                for i, reg in enumerate(results, 1):
                    output += f"{i}. {reg.client_org_name}\n"
                    output += f"   Lobbyist: {reg.registrant_name}\n"
                    output += f"   Registration: {reg.reg_number}\n"
                    output += f"   Period: {reg.effective_date or 'N/A'} to {reg.end_date or 'Active'}\n"
                    if reg.government_institutions:
                        output += f"   Institutions: {', '.join(reg.government_institutions[:3])}\n"
                    if reg.subject_matters:
                        output += f"   Subject Matter:\n"
                        for sm in reg.subject_matters[:2]:
                            output += f"     - {sm[:150]}...\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for search_lobbying_registrations: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_lobbying_registrations")
                return [TextContent(type="text", text=f"Error searching lobbying registrations: {sanitize_error_message(e)}")]

        elif name == "search_lobbying_communications":
            try:
                client_name = arguments.get("client_name")
                lobbyist_name = arguments.get("lobbyist_name")
                official_name = arguments.get("official_name")
                institution = arguments.get("institution")
                subject_keyword = arguments.get("subject_keyword")
                date_from = arguments.get("date_from")
                date_to = arguments.get("date_to")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_lobbying_communications called with client={client_name}, official={official_name}, date_from={date_from}")

                # Search communications
                results = await run_sync(
                    lobbying_client.search_communications,
                    client_name=client_name,
                    lobbyist_name=lobbyist_name,
                    official_name=official_name,
                    institution=institution,
                    subject_keyword=subject_keyword,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit
                )

                if not results:
                    return [TextContent(type="text", text="No lobbying communications found matching your criteria.")]

                # Format output
                output = f"Found {len(results)} lobbying communication(s)\n"
                if date_from or date_to:
                    output += f"Date range: {date_from or 'Any'} to {date_to or 'Any'}\n"
                output += "\n"

                for i, comm in enumerate(results, 1):
                    output += f"{i}. {comm.client_org_name}\n"
                    output += f"   Date: {comm.comm_date}\n"
                    output += f"   Lobbyist: {comm.registrant_name}\n"
                    if comm.dpoh_names:
                        output += f"   Met with: {', '.join(comm.dpoh_names[:3])}\n"
                    if comm.dpoh_titles:
                        output += f"   Titles: {', '.join(set(comm.dpoh_titles[:3]))}\n"
                    if comm.institutions:
                        output += f"   Institutions: {', '.join(set(comm.institutions))}\n"
                    if comm.subject_matters:
                        output += f"   Subject: {comm.subject_matters[0][:120]}...\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for search_lobbying_communications: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_lobbying_communications")
                return [TextContent(type="text", text=f"Error searching lobbying communications: {sanitize_error_message(e)}")]

        elif name == "get_top_lobbying_clients":
            try:
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                active_only = arguments.get("active_only", True)
                logger.info(f"get_top_lobbying_clients called with limit={limit}, active_only={active_only}")

                # Get top clients
                results = await run_sync(
                    lobbying_client.get_top_clients,
                    limit=limit,
                    active_only=active_only
                )

                if not results:
                    return [TextContent(type="text", text="No lobbying clients found.")]

                # Format output
                output = f"Top {len(results)} Lobbying Clients\n"
                if active_only:
                    output += "By Active Registrations\n"
                output += "\n"

                for i, client_info in enumerate(results, 1):
                    client_name = client_info["client_name"]
                    count = client_info["registration_count"]
                    if client_name and client_name not in ["", "null"]:
                        output += f"{i}. {client_name}\n"
                        output += f"   Active Registrations: {count}\n\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for get_top_lobbying_clients: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_top_lobbying_clients")
                return [TextContent(type="text", text=f"Error getting top lobbying clients: {sanitize_error_message(e)}")]

        elif name == "analyze_bill_lobbying":
            try:
                bill_number = arguments.get("bill_number")
                bill_keyword = arguments["bill_keyword"]
                limit = validate_limit(arguments.get("limit"), default=10, max_val=30)
                logger.info(f"analyze_bill_lobbying called with bill_number={bill_number}, keyword={bill_keyword}")

                # Search both registrations and communications for the keyword
                registrations = await run_sync(
                    lobbying_client.search_registrations,
                    subject_keyword=bill_keyword,
                    active_only=True,
                    limit=limit
                )

                communications = await run_sync(
                    lobbying_client.search_communications,
                    subject_keyword=bill_keyword,
                    date_from="2023-01-01",  # Last 2+ years
                    limit=limit
                )

                # If bill number provided, also search for that specifically
                if bill_number:
                    bill_regs = await run_sync(
                        lobbying_client.search_registrations,
                        subject_keyword=bill_number,
                        active_only=True,
                        limit=limit
                    )
                    registrations.extend(bill_regs)
                    # Deduplicate
                    seen = set()
                    registrations = [r for r in registrations if not (r.reg_id in seen or seen.add(r.reg_id))]

                # Format output
                output = f"Bill Lobbying Analysis\n"
                if bill_number:
                    output += f"Bill: {bill_number}\n"
                output += f"Keywords: {bill_keyword}\n"
                output += "=" * 60 + "\n\n"

                # Registrations section
                output += f"Active Lobbying Registrations ({len(registrations)} found):\n\n"
                if registrations:
                    for i, reg in enumerate(registrations[:limit], 1):
                        output += f"{i}. {reg.client_org_name}\n"
                        output += f"   Lobbyist: {reg.registrant_name}\n"
                        if reg.subject_matters:
                            relevant_sm = [sm for sm in reg.subject_matters if bill_keyword.lower() in sm.lower()]
                            if relevant_sm:
                                output += f"   Relevant Subject: {relevant_sm[0][:150]}...\n"
                        output += "\n"
                else:
                    output += "   No active registrations found.\n\n"

                # Communications section
                output += f"Recent Lobbying Communications ({len(communications)} found since 2023):\n\n"
                if communications:
                    for i, comm in enumerate(communications[:limit], 1):
                        output += f"{i}. {comm.client_org_name} - {comm.comm_date}\n"
                        output += f"   Lobbyist: {comm.registrant_name}\n"
                        if comm.dpoh_names:
                            output += f"   Met with: {', '.join(comm.dpoh_names[:2])}\n"
                        if comm.institutions:
                            output += f"   Institution: {comm.institutions[0]}\n"
                        output += "\n"
                else:
                    output += "   No recent communications found.\n\n"

                # Summary
                unique_clients = len(set(r.client_org_name for r in registrations))
                output += f"Summary:\n"
                output += f"  • {len(registrations)} active registrations\n"
                output += f"  • {unique_clients} unique organizations\n"
                output += f"  • {len(communications)} communications since 2023\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for analyze_bill_lobbying: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for analyze_bill_lobbying: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_bill_lobbying")
                return [TextContent(type="text", text=f"Error analyzing bill lobbying: {sanitize_error_message(e)}")]

        elif name == "analyze_mp_bills":
            try:
                mp_name = arguments.get("mp_name")
                politician_url = arguments.get("politician_url")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"analyze_mp_bills called with mp_name={mp_name}, politician_url={politician_url}")

                # Get politician URL if not provided
                if not politician_url and not mp_name:
                    return [TextContent(type="text", text="Please provide either mp_name or politician_url.")]

                if not politician_url:
                    # Search for politician
                    def search_pol():
                        return list(op_client.search_politician(mp_name))
                    politicians = await run_sync(search_pol)

                    if not politicians:
                        return [TextContent(type="text", text=f"No MP found matching '{mp_name}'.")]

                    politician_url = politicians[0].get('url')
                    pol_name = politicians[0].get('name', mp_name)
                else:
                    pol_name = mp_name or "MP"

                # Get bills sponsored by this politician
                def get_bills():
                    return list(op_client.list_bills(sponsor=politician_url, limit=limit))

                bills = await run_sync(get_bills)

                if not bills:
                    return [TextContent(type="text", text=f"No bills found sponsored by {pol_name}.")]

                # Analyze bills
                total_bills = len(bills)
                by_status = {}
                by_chamber = {"C": 0, "S": 0}

                for bill in bills:
                    status = bill.get('status', 'Unknown')
                    by_status[status] = by_status.get(status, 0) + 1

                    number = bill.get('number', '')
                    if number.upper().startswith('C-'):
                        by_chamber["C"] += 1
                    elif number.upper().startswith('S-'):
                        by_chamber["S"] += 1

                # Format output
                output = f"Legislative Analysis: {pol_name}\n"
                output += "=" * 60 + "\n\n"

                output += f"Total Bills Sponsored: {total_bills}\n"
                output += f"House Bills (C-): {by_chamber['C']}\n"
                output += f"Senate Bills (S-): {by_chamber['S']}\n\n"

                output += "Status Breakdown:\n"
                for status, count in sorted(by_status.items(), key=lambda x: x[1], reverse=True):
                    pct = (count / total_bills * 100) if total_bills > 0 else 0
                    output += f"  • {status}: {count} ({pct:.1f}%)\n"

                output += f"\nRecent Bills:\n\n"
                for i, bill in enumerate(bills[:10], 1):
                    output += f"{i}. {bill.get('number', 'N/A')}: {bill.get('name', {}).get('en', 'N/A')}\n"
                    output += f"   Status: {bill.get('status', 'Unknown')}\n"
                    introduced = bill.get('introduced', 'N/A')
                    if introduced and introduced != 'N/A':
                        output += f"   Introduced: {introduced}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for analyze_mp_bills: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_mp_bills")
                return [TextContent(type="text", text=f"Error analyzing MP bills: {sanitize_error_message(e)}")]

        elif name == "compare_party_bills":
            try:
                session = arguments.get("session")
                limit = validate_limit(arguments.get("limit"), default=50, max_val=100)
                logger.info(f"compare_party_bills called with session={session}, limit={limit}")

                # Get bills
                def get_bills():
                    params = {'limit': limit}
                    return list(op_client.list_bills(**params))

                bills = await run_sync(get_bills)

                if not bills:
                    return [TextContent(type="text", text="No bills found.")]

                # Group by sponsor party
                party_bills = {}
                for bill in bills:
                    sponsor_mp = bill.get('sponsor_politician', {})
                    if sponsor_mp:
                        party_name = sponsor_mp.get('current_party', {}).get('name', {}).get('en', 'Independent')
                        if party_name not in party_bills:
                            party_bills[party_name] = []
                        party_bills[party_name].append(bill)

                if not party_bills:
                    return [TextContent(type="text", text="No party affiliation data found for bills.")]

                # Analyze by party
                party_stats = {}
                for party, party_bill_list in party_bills.items():
                    total = len(party_bill_list)
                    passed = sum(1 for b in party_bill_list if 'royal assent' in b.get('status', '').lower())
                    in_progress = sum(1 for b in party_bill_list if 'reading' in b.get('status', '').lower())

                    party_stats[party] = {
                        'total': total,
                        'passed': passed,
                        'in_progress': in_progress,
                        'success_rate': (passed / total * 100) if total > 0 else 0
                    }

                # Format output
                output = f"Party Bill Comparison\n"
                output += f"Analyzing {len(bills)} bills\n"
                output += "=" * 60 + "\n\n"

                # Sort by total bills
                sorted_parties = sorted(party_stats.items(), key=lambda x: x[1]['total'], reverse=True)

                for party, stats in sorted_parties:
                    output += f"{party}:\n"
                    output += f"  Total Bills: {stats['total']}\n"
                    output += f"  Passed (Royal Assent): {stats['passed']}\n"
                    output += f"  In Progress: {stats['in_progress']}\n"
                    output += f"  Success Rate: {stats['success_rate']:.1f}%\n\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for compare_party_bills: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in compare_party_bills")
                return [TextContent(type="text", text=f"Error comparing party bills: {sanitize_error_message(e)}")]

        elif name == "analyze_bill_progress":
            try:
                bill_number = arguments["bill_number"]
                session = arguments.get("session")
                logger.info(f"analyze_bill_progress called with bill_number={bill_number}, session={session}")

                # Try to get bill from LEGISinfo first for detailed timeline
                bill_code = bill_number.lower()
                sessions_to_try = [session] if session else ['45-1', '44-1', '43-2']

                bill_data = None
                for sess in sessions_to_try:
                    try:
                        result = await run_sync(legis_client.get_bill, sess, bill_code)
                        if isinstance(result, list) and result:
                            bill_data = result[0]
                            break
                    except:
                        continue

                if not bill_data:
                    return [TextContent(type="text", text=f"Bill {bill_number} not found in recent sessions.")]

                # Format output
                output = f"Bill Progress Analysis: {bill_number.upper()}\n"
                output += "=" * 60 + "\n\n"

                output += f"Title: {bill_data.get('BillTitle', {}).get('Title', 'N/A')}\n"
                output += f"Sponsor: {bill_data.get('SponsorPersonName', 'N/A')}\n"
                if bill_data.get('SponsorAffiliationTitle'):
                    output += f"  {bill_data.get('SponsorAffiliationTitle')}\n"
                output += f"Status: {bill_data.get('StatusName', 'N/A')}\n\n"

                # Timeline events
                events = bill_data.get('BillEvents', {}).get('BillEvent', [])
                if not isinstance(events, list):
                    events = [events] if events else []

                if events:
                    output += f"Legislative Timeline ({len(events)} events):\n\n"
                    for i, event in enumerate(events[:15], 1):
                        date = event.get('EventDate', 'N/A')
                        chamber = event.get('ChamberName', '')
                        event_name = event.get('EventTypeName', 'Event')
                        output += f"{i}. {date} - {chamber} - {event_name}\n"

                    if len(events) > 15:
                        output += f"\n... and {len(events) - 15} more events\n"
                else:
                    output += "No detailed timeline events available.\n"

                # Committee assignments
                committees = bill_data.get('CommitteeActivities', {}).get('CommitteeActivity', [])
                if committees:
                    if not isinstance(committees, list):
                        committees = [committees]
                    output += f"\n\nCommittee Activity:\n"
                    for comm in committees[:5]:
                        output += f"  • {comm.get('CommitteeName', 'Unknown Committee')}\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for analyze_bill_progress: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for analyze_bill_progress: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_bill_progress")
                return [TextContent(type="text", text=f"Error analyzing bill progress: {sanitize_error_message(e)}")]

        elif name == "get_mp_activity_scorecard":
            try:
                mp_name = arguments.get("mp_name")
                politician_url = arguments.get("politician_url")
                logger.info(f"get_mp_activity_scorecard called for mp_name={mp_name}")

                # Get politician info
                if not politician_url and not mp_name:
                    return [TextContent(type="text", text="Please provide either mp_name or politician_url.")]

                if not politician_url:
                    def search_pol():
                        return list(op_client.search_politician(mp_name))
                    politicians = await run_sync(search_pol)

                    if not politicians:
                        return [TextContent(type="text", text=f"No MP found matching '{mp_name}'.")]

                    politician = politicians[0]
                    politician_url = politician.get('url')
                    pol_name = politician.get('name', mp_name)
                else:
                    pol_name = mp_name or "MP"

                # Gather data from multiple sources
                output = f"MP Activity Scorecard: {pol_name}\n"
                output += "=" * 60 + "\n\n"

                # Bills sponsored
                def get_bills():
                    return list(op_client.list_bills(sponsor=politician_url, limit=50))
                bills = await run_sync(get_bills)
                output += f"📜 Legislative Activity:\n"
                output += f"  Bills Sponsored: {len(bills)}\n"
                if bills:
                    passed = sum(1 for b in bills if 'royal assent' in b.get('status', '').lower())
                    output += f"  Passed into Law: {passed}\n"
                output += "\n"

                # Petitions
                petitions = await run_sync(petitions_client.get_petitions_by_mp, pol_name, category="All")
                output += f"✉️  Citizen Engagement:\n"
                output += f"  Petitions Sponsored: {len(petitions)}\n"
                if petitions:
                    total_sigs = sum(p.signature_count for p in petitions)
                    with_response = sum(1 for p in petitions if p.government_response_date)
                    output += f"  Total Signatures Represented: {total_sigs:,}\n"
                    output += f"  With Government Response: {with_response}\n"
                output += "\n"

                # Expenses
                try:
                    expenses = await run_sync(expenditure_client.search_by_name, pol_name, 2026, 1)
                    if expenses:
                        exp = expenses[0]
                        output += f"💰 Expenditures (FY 2025-2026 Q1):\n"
                        output += f"  Total: ${exp.total:,.2f}\n"
                        output += f"  Travel: ${exp.travel:,.2f}\n"
                        output += f"  Hospitality: ${exp.hospitality:,.2f}\n"
                        output += "\n"
                except:
                    pass

                # Lobbying connections (if any)
                lobby_comms = await run_sync(
                    lobbying_client.search_communications,
                    official_name=pol_name,
                    date_from="2024-01-01",
                    limit=10
                )
                if lobby_comms:
                    output += f"🤝 Lobbying Meetings (since 2024):\n"
                    output += f"  Communications Recorded: {len(lobby_comms)}\n"
                    unique_clients = len(set(c.client_org_name for c in lobby_comms))
                    output += f"  Unique Organizations: {unique_clients}\n"
                    output += "\n"

                output += f"Activity Summary:\n"
                activity_score = len(bills) + len(petitions) + (len(lobby_comms) if lobby_comms else 0)
                output += f"  Combined Activity Score: {activity_score}\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for get_mp_activity_scorecard: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_mp_activity_scorecard")
                return [TextContent(type="text", text=f"Error generating scorecard: {sanitize_error_message(e)}")]

        elif name == "track_committee_activity":
            try:
                committee = arguments.get("committee")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=20)
                logger.info(f"track_committee_activity called for committee={committee}")

                # Search for committees
                def get_committees():
                    if committee:
                        return list(op_client.list_committees(limit=limit))
                    else:
                        return list(op_client.list_committees(limit=limit))

                committees = await run_sync(get_committees)

                # Filter if committee name provided
                if committee:
                    committee_lower = committee.lower()
                    committees = [c for c in committees if
                                  committee_lower in c.get('name', {}).get('en', '').lower() or
                                  committee_lower in c.get('short_name', {}).get('en', '').lower()]

                if not committees:
                    return [TextContent(type="text", text=f"No committees found matching '{committee}'.")]

                output = f"Committee Activity Report\n"
                output += "=" * 60 + "\n\n"

                for comm in committees[:5]:
                    name = comm.get('name', {}).get('en', 'N/A')
                    output += f"📋 {name}\n"

                    # Get members
                    members = comm.get('memberships', [])
                    output += f"  Members: {len(members)}\n"

                    # Party breakdown
                    party_counts = {}
                    for member in members:
                        pol = member.get('politician', {})
                        party = pol.get('current_party', {}).get('name', {}).get('en', 'Independent')
                        party_counts[party] = party_counts.get(party, 0) + 1

                    if party_counts:
                        output += f"  Composition: "
                        output += ", ".join([f"{p}: {c}" for p, c in sorted(party_counts.items(), key=lambda x: x[1], reverse=True)])
                        output += "\n"

                    output += "\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for track_committee_activity: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in track_committee_activity")
                return [TextContent(type="text", text=f"Error tracking committee activity: {sanitize_error_message(e)}")]

        elif name == "detect_conflicts_of_interest":
            try:
                mp_name = arguments.get("mp_name")
                topic_keyword = arguments.get("topic_keyword")
                logger.info(f"detect_conflicts_of_interest called for mp={mp_name}, topic={topic_keyword}")

                if not mp_name:
                    return [TextContent(type="text", text="Please provide mp_name.")]

                output = f"Conflict of Interest Analysis: {mp_name}\n"
                output += "=" * 60 + "\n\n"

                # Check lobbying meetings with MP
                lobby_meetings = await run_sync(
                    lobbying_client.search_communications,
                    official_name=mp_name,
                    subject_keyword=topic_keyword if topic_keyword else None,
                    date_from="2023-01-01",
                    limit=20
                )

                if lobby_meetings:
                    output += f"🚨 Lobbying Activity:\n"
                    output += f"  Meetings with Lobbyists (since 2023): {len(lobby_meetings)}\n\n"

                    # Group by client
                    client_counts = {}
                    for meeting in lobby_meetings:
                        client_counts[meeting.client_org_name] = client_counts.get(meeting.client_org_name, 0) + 1

                    output += f"  Top Organizations:\n"
                    for client, count in sorted(client_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                        if client and client not in ["", "null"]:
                            output += f"    • {client}: {count} meetings\n"
                    output += "\n"

                # Check expenses
                try:
                    expenses = await run_sync(expenditure_client.search_by_name, mp_name, 2026, 1)
                    if expenses:
                        exp = expenses[0]
                        output += f"💰 Recent Expenses (Q1 2025-2026):\n"
                        output += f"  Total: ${exp.total:,.2f}\n"
                        if exp.travel > 50000:
                            output += f"  ⚠️  High travel expenses: ${exp.travel:,.2f}\n"
                        if exp.hospitality > 10000:
                            output += f"  ⚠️  High hospitality: ${exp.hospitality:,.2f}\n"
                        output += "\n"
                except:
                    pass

                # Summary
                output += f"Assessment:\n"
                if lobby_meetings and len(lobby_meetings) > 10:
                    output += f"  • High lobbying contact frequency ({len(lobby_meetings)} meetings)\n"
                if topic_keyword:
                    output += f"  • Focused activity on topic: {topic_keyword}\n"
                else:
                    output += f"  • Consider reviewing voting record on relevant bills\n"

                if not lobby_meetings:
                    output += f"  • No significant lobbying activity detected\n"

                return [TextContent(type="text", text=output)]

            except ValueError as e:
                logger.warning(f"Invalid input for detect_conflicts_of_interest: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in detect_conflicts_of_interest")
                return [TextContent(type="text", text=f"Error detecting conflicts: {sanitize_error_message(e)}")]

        elif name == "analyze_industry_influence":
            try:
                industry_keyword = arguments["industry_keyword"]
                limit = validate_limit(arguments.get("limit"), default=10, max_val=20)
                logger.info(f"analyze_industry_influence called for industry={industry_keyword}")

                output = f"Industry Influence Analysis: {industry_keyword}\n"
                output += "=" * 60 + "\n\n"

                # Find lobbying registrations for this industry
                registrations = await run_sync(
                    lobbying_client.search_registrations,
                    subject_keyword=industry_keyword,
                    active_only=True,
                    limit=limit * 2
                )

                if registrations:
                    # Count by organization
                    org_counts = {}
                    for reg in registrations:
                        org_counts[reg.client_org_name] = org_counts.get(reg.client_org_name, 0) + 1

                    output += f"📊 Active Lobbying Organizations:\n"
                    for org, count in sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:limit]:
                        if org and org not in ["", "null"]:
                            output += f"  • {org}: {count} registrations\n"
                    output += "\n"

                    # Government institutions targeted
                    all_institutions = []
                    for reg in registrations:
                        all_institutions.extend(reg.government_institutions)

                    if all_institutions:
                        inst_counts = {}
                        for inst in all_institutions:
                            inst_counts[inst] = inst_counts.get(inst, 0) + 1

                        output += f"🏛️  Government Institutions Targeted:\n"
                        for inst, count in sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            output += f"  • {inst}: {count} registrations\n"
                        output += "\n"

                # Find recent communications
                communications = await run_sync(
                    lobbying_client.search_communications,
                    subject_keyword=industry_keyword,
                    date_from="2024-01-01",
                    limit=limit
                )

                if communications:
                    output += f"🤝 Recent Lobbying Activity (since 2024):\n"
                    output += f"  Communications: {len(communications)}\n"

                    # Most-contacted officials
                    official_contacts = {}
                    for comm in communications:
                        for official in comm.dpoh_names:
                            official_contacts[official] = official_contacts.get(official, 0) + 1

                    if official_contacts:
                        output += f"\n  Most-Contacted Officials:\n"
                        for official, count in sorted(official_contacts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            if official:
                                output += f"    • {official}: {count} meetings\n"
                    output += "\n"

                # Summary
                output += f"Industry Impact Summary:\n"
                output += f"  • {len(registrations)} active registrations\n"
                output += f"  • {len(communications)} communications since 2024\n"
                output += f"  • {len(set(r.client_org_name for r in registrations))} unique organizations\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for analyze_industry_influence: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for analyze_industry_influence: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_industry_influence")
                return [TextContent(type="text", text=f"Error analyzing industry influence: {sanitize_error_message(e)}")]

        elif name == "compare_mp_performance":
            try:
                mp_names = arguments["mp_names"]
                logger.info(f"compare_mp_performance called for {len(mp_names)} MPs")

                if len(mp_names) < 2:
                    return [TextContent(type="text", text="Please provide at least 2 MP names to compare.")]
                if len(mp_names) > 5:
                    return [TextContent(type="text", text="Maximum 5 MPs can be compared at once.")]

                output = f"MP Performance Comparison\n"
                output += "=" * 60 + "\n\n"

                mp_data = []

                for mp_name in mp_names:
                    # Search for politician
                    def search_pol():
                        return list(op_client.search_politician(mp_name))
                    politicians = await run_sync(search_pol)

                    if not politicians:
                        output += f"⚠️  {mp_name}: Not found\n\n"
                        continue

                    politician = politicians[0]
                    pol_name = politician.get('name', mp_name)
                    politician_url = politician.get('url')

                    # Gather metrics
                    data = {"name": pol_name}

                    # Bills
                    def get_bills():
                        return list(op_client.list_bills(sponsor=politician_url, limit=50))
                    bills = await run_sync(get_bills)
                    data["bills_total"] = len(bills)
                    data["bills_passed"] = sum(1 for b in bills if 'royal assent' in b.get('status', '').lower())

                    # Petitions
                    petitions = await run_sync(petitions_client.get_petitions_by_mp, pol_name, category="All")
                    data["petitions_total"] = len(petitions)
                    data["petitions_signatures"] = sum(p.signature_count for p in petitions)

                    # Expenses
                    try:
                        expenses = await run_sync(expenditure_client.search_by_name, pol_name, 2026, 1)
                        if expenses:
                            data["expenses_total"] = expenses[0].total
                        else:
                            data["expenses_total"] = 0
                    except:
                        data["expenses_total"] = 0

                    # Lobbying meetings
                    lobby_comms = await run_sync(
                        lobbying_client.search_communications,
                        official_name=pol_name,
                        date_from="2024-01-01",
                        limit=50
                    )
                    data["lobby_meetings"] = len(lobby_comms) if lobby_comms else 0

                    mp_data.append(data)

                # Format comparison table
                if mp_data:
                    output += f"{'Metric':<30} " + " ".join([f"{d['name'][:15]:>15}" for d in mp_data]) + "\n"
                    output += "-" * 80 + "\n"

                    # Bills
                    output += f"{'Bills Sponsored':<30} " + " ".join([f"{d['bills_total']:>15}" for d in mp_data]) + "\n"
                    output += f"{'Bills Passed':<30} " + " ".join([f"{d['bills_passed']:>15}" for d in mp_data]) + "\n"
                    if any(d['bills_total'] > 0 for d in mp_data):
                        output += f"{'Success Rate':<30} " + " ".join([
                            f"{(d['bills_passed']/d['bills_total']*100 if d['bills_total'] > 0 else 0):.1f}%".rjust(15)
                            for d in mp_data
                        ]) + "\n"

                    # Petitions
                    output += f"{'Petitions Sponsored':<30} " + " ".join([f"{d['petitions_total']:>15}" for d in mp_data]) + "\n"
                    output += f"{'Total Signatures':<30} " + " ".join([f"{d['petitions_signatures']:>15,}" for d in mp_data]) + "\n"

                    # Expenses
                    output += f"{'Expenses (Q1 2025-26)':<30} " + " ".join([f"${d['expenses_total']:>14,.0f}" for d in mp_data]) + "\n"

                    # Lobbying
                    output += f"{'Lobby Meetings (2024+)':<30} " + " ".join([f"{d['lobby_meetings']:>15}" for d in mp_data]) + "\n"

                return [TextContent(type="text", text=output)]

            except KeyError as e:
                logger.warning(f"Missing required parameter for compare_mp_performance: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for compare_mp_performance: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in compare_mp_performance")
                return [TextContent(type="text", text=f"Error comparing MP performance: {sanitize_error_message(e)}")]

        elif name == "search_mp":
            try:
                name = arguments.get("name")
                party = arguments.get("party")
                riding = arguments.get("riding")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)

                # Require at least one search criterion
                if not any([name, party, riding]):
                    return [TextContent(
                        type="text",
                        text="Please provide at least one search criterion: name, party, or riding."
                    )]

                logger.info(f"search_mp called with name='{name}', party='{party}', riding='{riding}', limit={limit}")

                def _search_mp():
                    # Start with all politicians or name-filtered if provided
                    if name:
                        politicians = op_client.search_politician(name)
                    else:
                        politicians = op_client._paginate("/politicians/")

                    # Apply additional filters
                    matched = []
                    party_lower = party.lower() if party else None
                    riding_lower = riding.lower() if riding else None

                    for p in politicians:
                        if len(matched) >= limit:
                            break

                        # Check party filter
                        if party_lower:
                            current_party = p.get('current_party', {})
                            party_name = (current_party.get('short_name', {}).get('en', '') or
                                        current_party.get('name', {}).get('en', '')).lower()
                            if party_lower not in party_name:
                                continue

                        # Check riding filter
                        if riding_lower:
                            current_riding = p.get('current_riding', {})
                            riding_name = current_riding.get('name', {}).get('en', '').lower()
                            if riding_lower not in riding_name:
                                continue

                        matched.append(p)

                    return matched

                politicians = await run_sync(_search_mp)

                if not politicians:
                    criteria = []
                    if name: criteria.append(f"name '{name}'")
                    if party: criteria.append(f"party '{party}'")
                    if riding: criteria.append(f"riding '{riding}'")
                    return [TextContent(
                        type="text",
                        text=f"No MPs found matching {' and '.join(criteria)}."
                    )]

                return [TextContent(
                    type="text",
                    text=f"Found {len(politicians)} MP(s):\n\n" +
                         "\n\n".join([
                             f"Name: {p.get('name')}\n" +
                             f"Party: {p.get('current_party', {}).get('short_name', {}).get('en', 'N/A')}\n" +
                             f"Riding: {p.get('current_riding', {}).get('name', {}).get('en', 'N/A')}\n" +
                             f"URL: {p.get('url')}"
                             for p in politicians
                         ])
                )]
            except ValueError as e:
                logger.warning(f"Invalid input for search_mp: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_mp")
                return [TextContent(type="text", text=f"Error searching for MP: {sanitize_error_message(e)}")]

        elif name == "get_mp_voting_history":
            try:
                mp_url = arguments["mp_url"]
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"get_mp_voting_history called with mp_url={mp_url}, limit={limit}")

                # Get politician details
                politician = await run_sync(op_client.get_politician, mp_url)
                mp_name = politician.get('name', 'Unknown MP')

                # Get voting history (ballots)
                ballots = await run_sync(op_client.get_politician_ballots, mp_url, limit)

                if not ballots:
                    return [TextContent(
                        type="text",
                        text=f"No recent voting records found for {mp_name}."
                    )]

                # Fetch vote details for each ballot to get descriptions
                vote_records = []
                for ballot in ballots:
                    vote_url = ballot.get('vote_url', '')
                    ballot_value = ballot.get('ballot', 'Unknown')

                    try:
                        vote = await run_sync(op_client.get_vote, vote_url)
                        vote_records.append({
                            'date': vote.get('date', 'Unknown'),
                            'ballot': ballot_value,
                            'description': vote.get('description', {}).get('en', 'No description')[:150],
                            'result': vote.get('result', 'Unknown'),
                            'vote_url': vote_url
                        })
                    except:
                        # If we can't get vote details, just include what we have
                        vote_records.append({
                            'date': 'Unknown',
                            'ballot': ballot_value,
                            'description': 'Vote details unavailable',
                            'result': 'Unknown',
                            'vote_url': vote_url
                        })

                return [TextContent(
                    type="text",
                    text=f"Voting history for {mp_name} (last {len(vote_records)} votes):\n\n" +
                         "\n\n".join([
                             f"Date: {vr['date']}\n" +
                             f"Voted: {vr['ballot']}\n" +
                             f"Topic: {vr['description']}{'...' if len(vr.get('description', '')) > 147 else ''}\n" +
                             f"Result: {vr['result']}\n" +
                             f"Vote URL: {vr['vote_url']}"
                             for vr in vote_records
                         ])
                )]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_mp_voting_history: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for get_mp_voting_history: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_mp_voting_history")
                return [TextContent(type="text", text=f"Error getting MP voting history: {sanitize_error_message(e)}")]

        elif name == "get_vote_details":
            try:
                vote_url = arguments["vote_url"]
                include_ballots = arguments.get("include_ballots", False)
                limit = validate_limit(arguments.get("limit"), default=50, max_val=350) if include_ballots else 0
                logger.info(f"get_vote_details called with vote_url={vote_url}, include_ballots={include_ballots}")

                # Get vote summary
                vote = await run_sync(op_client.get_vote, vote_url)

                response_parts = [
                    f"Vote Details:\n",
                    f"Date: {vote.get('date')}\n",
                    f"Number: {vote.get('number')}\n",
                    f"Session: {vote.get('session')}\n",
                    f"Description: {vote.get('description', {}).get('en', 'No description')}\n",
                    f"Result: {vote.get('result')}\n",
                    f"Yea: {vote.get('yea_total', 0)}, Nay: {vote.get('nay_total', 0)}, Paired: {vote.get('paired_total', 0)}\n"
                ]

                # Add party breakdown
                party_votes = vote.get('party_votes', [])
                if party_votes:
                    response_parts.append("\nParty Breakdown:\n")
                    for pv in party_votes:
                        party_name = pv.get('party', {}).get('short_name', {}).get('en', 'Unknown')
                        party_vote = pv.get('vote', 'Unknown')
                        response_parts.append(f"- {party_name}: {party_vote}\n")

                # Add individual ballots if requested
                if include_ballots:
                    ballots = await run_sync(op_client.get_vote_ballots, vote_url, limit)

                    if ballots:
                        response_parts.append(f"\nIndividual MP Votes (showing {min(len(ballots), limit)} of {len(ballots)}):\n\n")

                        for ballot in ballots[:limit]:
                            politician_url = ballot.get('politician_url', '')
                            ballot_value = ballot.get('ballot', 'Unknown')

                            # Extract MP name from URL (e.g., /politicians/pierre-poilievre/ -> Pierre Poilievre)
                            mp_name = politician_url.strip('/').split('/')[-1].replace('-', ' ').title()

                            response_parts.append(f"- {mp_name}: {ballot_value}\n")

                return [TextContent(type="text", text="".join(response_parts))]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_vote_details: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for get_vote_details: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_vote_details")
                return [TextContent(type="text", text=f"Error getting vote details: {sanitize_error_message(e)}")]

        elif name == "find_mp_by_postal_code":
            try:
                postal_code = arguments["postal_code"]
                logger.info(f"find_mp_by_postal_code called with postal_code={postal_code}")

                # Get federal MP by postal code
                mp = await run_sync(represent_client.get_federal_mp_by_postal_code, postal_code)

                if not mp:
                    return [TextContent(
                        type="text",
                        text=f"No federal MP found for postal code '{postal_code}'. Please verify the postal code is correct."
                    )]

                # Format the response with MP information
                response_parts = [
                    f"Your Federal Member of Parliament:\n\n",
                    f"Name: {mp.get('name', 'N/A')}\n",
                    f"Party: {mp.get('party_name', 'N/A')}\n",
                    f"Riding: {mp.get('district_name', 'N/A')}\n",
                ]

                # Add contact information if available
                if mp.get('email'):
                    response_parts.append(f"Email: {mp.get('email')}\n")
                if mp.get('url'):
                    response_parts.append(f"Website: {mp.get('url')}\n")

                # Add office information if available
                offices = mp.get('offices', [])
                if offices:
                    response_parts.append("\nOffices:\n")
                    for office in offices:
                        office_type = office.get('type', 'Office')
                        if office.get('postal'):
                            response_parts.append(f"  {office_type}:\n")
                            response_parts.append(f"    {office.get('postal', '').strip()}\n")
                        if office.get('tel'):
                            response_parts.append(f"    Phone: {office.get('tel')}\n")
                        if office.get('fax'):
                            response_parts.append(f"    Fax: {office.get('fax')}\n")

                # Add social media if available
                social = []
                for key in ['twitter', 'facebook', 'instagram']:
                    if mp.get(key):
                        social.append(f"{key.title()}: {mp.get(key)}")
                if social:
                    response_parts.append(f"\nSocial Media: {', '.join(social)}\n")

                return [TextContent(type="text", text="".join(response_parts))]

            except KeyError as e:
                logger.warning(f"Missing required parameter for find_mp_by_postal_code: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except ValueError as e:
                logger.warning(f"Invalid input for find_mp_by_postal_code: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in find_mp_by_postal_code")
                return [TextContent(type="text", text=f"Error finding MP by postal code: {sanitize_error_message(e)}")]

        elif name == "analyze_party_discipline":
            try:
                vote_url = arguments["vote_url"]
                logger.info(f"analyze_party_discipline called with vote_url={vote_url}")

                # Get vote details
                vote = await run_sync(op_client.get_vote, vote_url)

                # Get all individual ballots (limit 350 covers all MPs)
                ballots = await run_sync(op_client.get_vote_ballots, vote_url, 350)

                if not ballots:
                    return [TextContent(
                        type="text",
                        text=f"No ballot data available for this vote."
                    )]

                # Group ballots by party
                from collections import defaultdict
                party_ballots = defaultdict(list)

                for ballot in ballots:
                    politician_url = ballot.get('politician_url', '')
                    ballot_value = ballot.get('ballot', 'Unknown')

                    # Get politician details to find their party
                    try:
                        politician = await run_sync(op_client.get_politician, politician_url)
                        party_name = politician.get('current_party', {}).get('short_name', {}).get('en', 'Unknown')

                        party_ballots[party_name].append({
                            'name': politician.get('name', 'Unknown'),
                            'riding': politician.get('current_riding', {}).get('name', {}).get('en', 'Unknown'),
                            'ballot': ballot_value,
                            'url': politician_url
                        })
                    except:
                        # Skip if we can't get politician details
                        continue

                # Analyze party discipline
                response_parts = [
                    f"Party Discipline Analysis\n",
                    f"Vote: {vote.get('description', {}).get('en', 'N/A')}\n",
                    f"Date: {vote.get('date')}\n",
                    f"Result: {vote.get('result')}\n\n",
                ]

                dissidents = []

                for party, mps in sorted(party_ballots.items()):
                    # Count votes by type
                    vote_counts = defaultdict(int)
                    for mp in mps:
                        vote_counts[mp['ballot']] += 1

                    # Determine party majority position
                    majority_vote = max(vote_counts.items(), key=lambda x: x[1])[0]
                    majority_count = vote_counts[majority_vote]
                    total_count = len(mps)

                    response_parts.append(f"{party} ({total_count} MPs):\n")
                    response_parts.append(f"  Party Position: {majority_vote} ({majority_count}/{total_count})\n")

                    # Find dissidents (those who voted differently)
                    party_dissidents = [mp for mp in mps if mp['ballot'] != majority_vote]

                    if party_dissidents:
                        response_parts.append(f"  MPs who broke ranks ({len(party_dissidents)}):\n")
                        for mp in party_dissidents:
                            response_parts.append(f"    - {mp['name']} ({mp['riding']}): Voted {mp['ballot']}\n")
                            dissidents.append({
                                'party': party,
                                'name': mp['name'],
                                'riding': mp['riding'],
                                'voted': mp['ballot'],
                                'party_position': majority_vote
                            })
                    else:
                        response_parts.append(f"  All MPs voted with party\n")

                    response_parts.append("\n")

                # Summary
                if dissidents:
                    response_parts.append(f"Summary: {len(dissidents)} MP(s) voted against their party's majority position\n")
                else:
                    response_parts.append("Summary: All MPs voted with their party\n")

                return [TextContent(type="text", text="".join(response_parts))]

            except KeyError as e:
                logger.warning(f"Missing required parameter for analyze_party_discipline: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_party_discipline")
                return [TextContent(type="text", text=f"Error analyzing party discipline: {sanitize_error_message(e)}")]

        # Phase 4 tools
        elif name == "get_bill_legislative_progress":
            try:
                bill_number = arguments["bill_number"]
                session = arguments.get("session")  # Get session if provided
                logger.info(f"get_bill_legislative_progress called with bill_number={bill_number}, session={session}")

                # Normalize bill number (e.g., "Bill C-319" -> "c-319")
                bill_code = bill_number.upper().replace('BILL ', '').strip().lower()

                # Try to find bill across sessions
                bill = None
                searched_sessions = []

                # If session provided, try that first
                if session:
                    sessions_to_try = [session, '45-1', '44-1', '43-2', '43-1']
                else:
                    # Try recent sessions in order
                    sessions_to_try = ['45-1', '44-1', '43-2', '43-1', '42-1']

                for sess in sessions_to_try:
                    if sess in searched_sessions:
                        continue  # Skip duplicates
                    searched_sessions.append(sess)

                    try:
                        bills = await run_sync(legis_client.get_bill, sess, bill_code)
                        if bills and isinstance(bills, list) and len(bills) > 0:
                            bill = bills[0]
                            logger.info(f"Found bill {bill_code} in session {sess}")
                            break  # Found it!
                    except:
                        continue  # Try next session

                if not bill:
                    return [TextContent(
                        type="text",
                        text=f"Bill {bill_number} not found in sessions: {', '.join(searched_sessions)}.\n\n" +
                             f"Please check the bill number or specify the correct session."
                    )]

                response_parts = [
                    f"Legislative Progress for Bill {bill_number}\n",
                    f"=" * 50, "\n\n",
                    f"Title: {bill.get('LongTitle', 'N/A')}\n",
                    f"Short Title: {bill.get('ShortTitle', 'N/A')}\n",
                    f"Session: {bill.get('ParliamentNumber')}-{bill.get('SessionNumber')}\n",
                    f"Bill Type: {bill.get('BillDocumentTypeName', 'N/A')}\n",
                    f"Originating Chamber: {bill.get('OriginatingChamberName', 'N/A')}\n\n",
                    f"CURRENT STATUS\n",
                    f"-" * 50, "\n",
                    f"Status: {bill.get('StatusName', 'N/A')}\n",
                    f"Current Stage: {bill.get('OngoingStageName', 'N/A')}\n\n",
                    f"COMPLETED STAGES\n",
                    f"-" * 50, "\n",
                    f"Latest Completed Stage: {bill.get('LatestCompletedMajorStageName', 'N/A')}\n",
                    f"Chamber: {bill.get('LatestCompletedMajorStageChamberName', 'N/A')}\n",
                ]

                if bill.get('LatestCompletedBillStageDateTime'):
                    response_parts.append(f"Completed: {bill.get('LatestCompletedBillStageDateTime')}\n")

                # Sponsor information
                response_parts.append(f"\nSPONSOR\n")
                response_parts.append(f"-" * 50 + "\n")
                sponsor_name = bill.get('SponsorPersonShortHonorific', '')
                if sponsor_name:
                    sponsor_affiliation = bill.get('SponsorPersonLatestPartyName', '')
                    response_parts.append(f"{sponsor_name}")
                    if sponsor_affiliation:
                        response_parts.append(f" ({sponsor_affiliation})")
                    response_parts.append("\n")
                else:
                    response_parts.append("N/A\n")

                # Additional information
                is_govt_bill = bill.get('IsGovernmentBill', False)
                response_parts.append(f"\nGovernment Bill: {'Yes' if is_govt_bill else 'No'}\n")

                return [TextContent(type="text", text="".join(response_parts))]

            except KeyError as e:
                logger.warning(f"Missing required parameter for get_bill_legislative_progress: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_bill_legislative_progress")
                return [TextContent(type="text", text=f"Error getting bill progress: {sanitize_error_message(e)}")]

        elif name == "analyze_mp_voting_participation":
            try:
                politician_url = arguments["politician_url"]
                limit = validate_limit(arguments.get("limit"), default=50, max_val=100)
                logger.info(f"analyze_mp_voting_participation called with politician_url={politician_url}, limit={limit}")

                # Get politician details
                politician = await run_sync(op_client.get_politician, politician_url)

                # Get voting history
                ballots = await run_sync(op_client.get_politician_ballots, politician_url, limit)

                if not ballots:
                    return [TextContent(
                        type="text",
                        text=f"No voting history found for {politician.get('name', 'this politician')}."
                    )]

                # Analyze participation
                from collections import defaultdict
                vote_counts = defaultdict(int)
                total_votes = len(ballots)

                for ballot in ballots:
                    ballot_value = ballot.get('ballot', 'Unknown')
                    vote_counts[ballot_value] += 1

                # Calculate participation rate (Yea + Nay = participated)
                participated = vote_counts.get('Yea', 0) + vote_counts.get('Nay', 0)
                participation_rate = (participated / total_votes * 100) if total_votes > 0 else 0

                response_parts = [
                    f"Voting Participation Analysis\n",
                    f"=" * 50, "\n\n",
                    f"MP: {politician.get('name', 'N/A')}\n",
                    f"Party: {politician.get('current_party', {}).get('short_name', {}).get('en', 'N/A')}\n",
                    f"Riding: {politician.get('current_riding', {}).get('name', {}).get('en', 'N/A')}\n\n",
                    f"PARTICIPATION SUMMARY (last {total_votes} votes)\n",
                    f"-" * 50, "\n",
                    f"Participation Rate: {participation_rate:.1f}%\n",
                    f"Total Votes Analyzed: {total_votes}\n\n",
                    f"VOTE BREAKDOWN\n",
                    f"-" * 50, "\n",
                ]

                for vote_type, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / total_votes * 100) if total_votes > 0 else 0
                    response_parts.append(f"  {vote_type}: {count} ({percentage:.1f}%)\n")

                # Show recent votes
                response_parts.append(f"\nRECENT VOTES (last 10)\n")
                response_parts.append(f"-" * 50 + "\n")

                for i, ballot in enumerate(islice(ballots, 10)):
                    vote_info = ballot.get('vote', {})
                    vote_desc = vote_info.get('description', {}).get('en', 'N/A')
                    vote_date = vote_info.get('date', 'N/A')
                    ballot_value = ballot.get('ballot', 'N/A')
                    response_parts.append(f"{i+1}. {vote_desc[:60]}... ({vote_date}): {ballot_value}\n")

                return [TextContent(type="text", text="".join(response_parts))]

            except KeyError as e:
                logger.warning(f"Missing required parameter for analyze_mp_voting_participation: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in analyze_mp_voting_participation")
                return [TextContent(type="text", text=f"Error analyzing voting participation: {sanitize_error_message(e)}")]

        elif name == "search_topic_across_sources":
            try:
                topic = arguments["topic"]
                limit = validate_limit(arguments.get("limit_per_source"), default=5, max_val=20)
                logger.info(f"search_topic_across_sources called with topic='{topic}', limit={limit}")

                response_parts = [
                    f"Multi-Source Search Results for: '{topic}'\n",
                    f"=" * 50, "\n\n",
                ]

                # Search bills
                response_parts.append(f"BILLS\n")
                response_parts.append(f"-" * 50 + "\n")
                try:
                    bills = []

                    # Detect if topic is a bill number
                    topic_upper = topic.upper()
                    is_bill_number = topic_upper.startswith(('C-', 'S-', 'BILL C-', 'BILL S-')) and len(topic) < 20

                    # If it's a bill number, try LEGISinfo across recent sessions
                    if is_bill_number:
                        # Extract bill code (e.g., "C-319" from "Bill C-319")
                        bill_code = topic_upper.replace('BILL ', '').strip().lower()
                        # Try recent sessions
                        for session in ['45-1', '44-1', '43-2', '43-1']:
                            try:
                                bill_data = await run_sync(legis_client.get_bill, session, bill_code)
                                if isinstance(bill_data, list) and bill_data:
                                    bill_info = bill_data[0]
                                    bills.append({
                                        'number': bill_info.get('NumberCode', 'N/A'),
                                        'name': {'en': bill_info.get('LongTitle', 'N/A')},
                                        'session': f"{bill_info.get('ParliamentNumber')}-{bill_info.get('SessionNumber')}"
                                    })
                                    break  # Found it, stop searching
                            except:
                                continue  # Try next session

                    # If not found via LEGISinfo or not a bill number, try OpenParliament
                    if not bills:
                        bills = list(islice(await run_sync(op_client.list_bills, q=topic), limit))

                    if bills:
                        for i, bill in enumerate(bills, 1):
                            bill_num = bill.get('number', 'N/A')
                            bill_name = bill.get('name', {}).get('en', 'N/A')[:80]
                            session_info = bill.get('session', '')
                            if session_info:
                                response_parts.append(f"{i}. {bill_num} ({session_info}) - {bill_name}\n")
                            else:
                                response_parts.append(f"{i}. {bill_num} - {bill_name}\n")
                    else:
                        response_parts.append("No bills found\n")
                except Exception as e:
                    response_parts.append(f"Error searching bills: {str(e)}\n")
                response_parts.append("\n")

                # Search debates
                response_parts.append(f"DEBATES\n")
                response_parts.append(f"-" * 50 + "\n")
                try:
                    debates = list(islice(await run_sync(op_client.list_debates, q=topic), limit))
                    if debates:
                        for i, debate in enumerate(debates, 1):
                            speaker = debate.get('attribution', 'Unknown')
                            content = debate.get('text', {}).get('en', '')[:100]
                            date = debate.get('date', 'N/A')
                            response_parts.append(f"{i}. {speaker} ({date}): {content}...\n")
                    else:
                        response_parts.append("No debates found\n")
                except Exception as e:
                    response_parts.append(f"Error searching debates: {str(e)}\n")
                response_parts.append("\n")

                # Search votes
                response_parts.append(f"VOTES\n")
                response_parts.append(f"-" * 50 + "\n")
                try:
                    votes = list(islice(await run_sync(op_client.list_votes, q=topic), limit))
                    if votes:
                        for i, vote in enumerate(votes, 1):
                            desc = vote.get('description', {}).get('en', 'N/A')[:80]
                            date = vote.get('date', 'N/A')
                            result = vote.get('result', 'N/A')
                            response_parts.append(f"{i}. {desc} ({date}): {result}\n")
                    else:
                        response_parts.append("No votes found\n")
                except Exception as e:
                    response_parts.append(f"Error searching votes: {str(e)}\n")
                response_parts.append("\n")

                # Search Hansard
                response_parts.append(f"HANSARD\n")
                response_parts.append(f"-" * 50 + "\n")
                try:
                    sitting = await run_sync(hansard_client.get_sitting, "latest/hansard", parse=True)
                    if sitting and sitting.sections:
                        matches = []
                        for section in sitting.sections:
                            for speech in section.speeches:
                                if topic.lower() in speech.text.lower():
                                    matches.append({
                                        'speaker': speech.speaker_name or 'Unknown',
                                        'content': speech.text[:100]
                                    })
                                    if len(matches) >= limit:
                                        break
                            if len(matches) >= limit:
                                break

                        if matches:
                            for i, match in enumerate(matches, 1):
                                response_parts.append(f"{i}. {match['speaker']}: {match['content']}...\n")
                        else:
                            response_parts.append("No Hansard mentions found\n")
                    else:
                        response_parts.append("Hansard data unavailable\n")
                except Exception as e:
                    response_parts.append(f"Error searching Hansard: {str(e)}\n")

                return [TextContent(type="text", text="".join(response_parts))]

            except KeyError as e:
                logger.warning(f"Missing required parameter for search_topic_across_sources: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_topic_across_sources")
                return [TextContent(type="text", text=f"Error searching across sources: {sanitize_error_message(e)}")]

        # CanLII tools
        elif name == "search_cases":
            try:
                if not canlii_client:
                    return [TextContent(
                        type="text",
                        text="CanLII service unavailable. CANLII_API_KEY not configured."
                    )]

                database_id = arguments["database_id"]
                query = arguments["query"]
                language = arguments.get("language", "en")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=100)
                published_after = arguments.get("published_after")
                published_before = arguments.get("published_before")
                decision_date_after = arguments.get("decision_date_after")
                decision_date_before = arguments.get("decision_date_before")
                logger.info(f"search_cases called with database_id={database_id}, query='{query}', limit={limit}")

                cases = await run_sync(
                    canlii_client.search_cases_by_keyword,
                    database_id=database_id,
                    query=query,
                    language=language,
                    limit=limit,
                    published_after=published_after,
                    published_before=published_before,
                    decision_date_after=decision_date_after,
                    decision_date_before=decision_date_before,
                )

                return [TextContent(
                    type="text",
                    text=f"Found {len(cases)} case(s) in {database_id} matching '{query}':\n\n" +
                         "\n\n".join([
                             f"Title: {c.get('title', 'N/A')}\n" +
                             f"Citation: {c.get('citation', 'N/A')}\n" +
                             f"Date: {c.get('decisionDate', 'N/A')}\n" +
                             f"Docket: {c.get('docketNumber', 'N/A')}"
                             for c in cases
                         ])
                )]
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid input for search_cases: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_cases")
                return [TextContent(type="text", text=f"Error searching cases: {sanitize_error_message(e)}")]

        elif name == "get_case":
            try:
                if not canlii_client:
                    return [TextContent(
                        type="text",
                        text="CanLII service unavailable. CANLII_API_KEY not configured."
                    )]

                database_id = arguments["database_id"]
                case_id = arguments["case_id"]
                language = arguments.get("language", "en")
                logger.info(f"get_case called with database_id={database_id}, case_id={case_id}")

                case = await run_sync(canlii_client.get_case, database_id, case_id, language=language)

                return [TextContent(
                    type="text",
                    text=f"Case: {case.get('title', 'N/A')}\n" +
                         f"Citation: {case.get('citation', 'N/A')}\n" +
                         f"Docket: {case.get('docketNumber', 'N/A')}\n" +
                         f"Decision Date: {case.get('decisionDate', 'N/A')}\n" +
                         f"Keywords: {', '.join(case.get('keywords', []))}"
                )]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_case: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_case")
                return [TextContent(type="text", text=f"Error getting case: {sanitize_error_message(e)}")]

        elif name == "get_case_citations":
            try:
                if not canlii_client:
                    return [TextContent(
                        type="text",
                        text="CanLII service unavailable. CANLII_API_KEY not configured."
                    )]

                database_id = arguments["database_id"]
                case_id = arguments["case_id"]
                citation_type = arguments.get("citation_type", "citingCases")
                logger.info(f"get_case_citations called with database_id={database_id}, case_id={case_id}, citation_type={citation_type}")

                if citation_type == "citedCases":
                    result = await run_sync(canlii_client.get_cited_cases, database_id, case_id)
                elif citation_type == "citingCases":
                    result = await run_sync(canlii_client.get_citing_cases, database_id, case_id)
                else:  # citedLegislations
                    result = await run_sync(canlii_client.get_cited_legislations, database_id, case_id)

                return [TextContent(
                    type="text",
                    text=f"Citations ({citation_type}) for {database_id}/{case_id}:\n\n{result}"
                )]
            except KeyError as e:
                logger.warning(f"Missing required parameter for get_case_citations: {e}")
                return [TextContent(type="text", text=f"Missing required parameter: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in get_case_citations")
                return [TextContent(type="text", text=f"Error getting case citations: {sanitize_error_message(e)}")]

        elif name == "search_legislation":
            try:
                if not canlii_client:
                    return [TextContent(
                        type="text",
                        text="CanLII service unavailable. CANLII_API_KEY not configured."
                    )]

                database_id = arguments.get("database_id", "ca")
                language = arguments.get("language", "en")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=100)
                logger.info(f"search_legislation called with database_id={database_id}, limit={limit}")

                result = await run_sync(canlii_client.browse_legislation, database_id, language=language)

                if "legislations" in result:
                    legislations = result["legislations"][:limit]
                    return [TextContent(
                        type="text",
                        text=f"Legislation in {database_id}:\n\n" +
                             "\n".join([
                                 f"- {leg.get('title', 'N/A')}"
                                 for leg in legislations
                             ])
                    )]

                return [TextContent(type="text", text=f"Legislation data: {result}")]
            except ValueError as e:
                logger.warning(f"Invalid input for search_legislation: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in search_legislation")
                return [TextContent(type="text", text=f"Error searching legislation: {sanitize_error_message(e)}")]

        elif name == "list_canlii_databases":
            try:
                if not canlii_client:
                    return [TextContent(
                        type="text",
                        text="CanLII service unavailable. CANLII_API_KEY not configured."
                    )]

                db_type = arguments.get("type", "cases")
                language = arguments.get("language", "en")
                logger.info(f"list_canlii_databases called with type={db_type}, language={language}")

                if db_type == "legislation":
                    result = await run_sync(canlii_client.list_legislation_databases, language)
                    db_title = "Legislation Databases"
                else:
                    result = await run_sync(canlii_client.list_databases, language)
                    db_title = "Case Law Databases"

                # Format the result - structure varies by jurisdiction
                formatted_output = [f"{db_title} (Language: {language}):\n"]

                if isinstance(result, dict):
                    for jurisdiction, data in result.items():
                        if isinstance(data, dict) and 'databases' in data:
                            databases = data['databases']
                            formatted_output.append(f"\n{jurisdiction.upper()}:")
                            for db in databases:
                                db_id = db.get('databaseId', 'N/A')
                                db_name = db.get('name', 'N/A')
                                formatted_output.append(f"  - {db_id}: {db_name}")
                        elif isinstance(data, list):
                            formatted_output.append(f"\n{jurisdiction.upper()}:")
                            for db in data:
                                db_id = db.get('databaseId', 'N/A')
                                db_name = db.get('name', 'N/A')
                                formatted_output.append(f"  - {db_id}: {db_name}")

                return [TextContent(type="text", text="\n".join(formatted_output))]
            except ValueError as e:
                logger.warning(f"Invalid input for list_canlii_databases: {e}")
                return [TextContent(type="text", text=f"Invalid input: {str(e)}")]
            except Exception as e:
                logger.exception(f"Unexpected error in list_canlii_databases")
                return [TextContent(type="text", text=f"Error listing CanLII databases: {sanitize_error_message(e)}")]

        elif name == "search_federal_contracts":
            try:
                vendor_name = arguments.get("vendor_name")
                department = arguments.get("department")
                min_value = arguments.get("min_value")
                max_value = arguments.get("max_value")
                year = arguments.get("year")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_federal_contracts called with vendor={vendor_name}, dept={department}, year={year}, limit={limit}")

                contracts = await run_sync(
                    contracts_client.search_contracts,
                    vendor_name=vendor_name,
                    department=department,
                    min_value=min_value,
                    max_value=max_value,
                    year=year,
                    limit=limit
                )

                if not contracts:
                    return [TextContent(type="text", text="No contracts found matching the criteria.")]

                output = f"Found {len(contracts)} federal contract(s):\n\n"
                for i, contract in enumerate(contracts, 1):
                    output += f"{i}. Vendor: {contract.vendor_name}\n"
                    output += f"   Value: ${contract.contract_value:,.2f}\n"
                    output += f"   Department: {contract.owner_org_title}\n"
                    output += f"   Date: {contract.contract_date or 'N/A'}\n"
                    if contract.comments:
                        output += f"   Details: {contract.comments[:100]}...\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in search_federal_contracts")
                return [TextContent(type="text", text=f"Error searching contracts: {sanitize_error_message(e)}")]

        elif name == "get_top_contractors":
            try:
                year = arguments.get("year")
                department = arguments.get("department")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"get_top_contractors called with year={year}, dept={department}, limit={limit}")

                vendors = await run_sync(
                    contracts_client.get_top_vendors,
                    limit=limit,
                    year=year,
                    department=department
                )

                if not vendors:
                    return [TextContent(type="text", text="No contractor data available.")]

                output = f"Top {len(vendors)} federal contractors"
                if year:
                    output += f" in {year}"
                if department:
                    output += f" for {department}"
                output += ":\n\n"

                for i, vendor in enumerate(vendors, 1):
                    output += f"{i}. {vendor['vendor_name']}\n"
                    output += f"   Total Value: ${vendor['total_value']:,.2f}\n\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in get_top_contractors")
                return [TextContent(type="text", text=f"Error getting top contractors: {sanitize_error_message(e)}")]

        elif name == "search_political_contributions":
            try:
                contributor_name = arguments.get("contributor_name")
                recipient_name = arguments.get("recipient_name")
                political_party = arguments.get("political_party")
                min_amount = arguments.get("min_amount")
                max_amount = arguments.get("max_amount")
                year = arguments.get("year")
                province = arguments.get("province")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_political_contributions called with contributor={contributor_name}, party={political_party}, year={year}, limit={limit}")

                contributions = await run_sync(
                    political_contrib_client.search_contributions,
                    contributor_name=contributor_name,
                    recipient_name=recipient_name,
                    political_party=political_party,
                    min_amount=min_amount,
                    max_amount=max_amount,
                    year=year,
                    province=province,
                    limit=limit
                )

                if not contributions:
                    return [TextContent(type="text", text="No political contributions found matching the criteria.")]

                output = f"Found {len(contributions)} political contribution(s):\n\n"
                for i, contrib in enumerate(contributions, 1):
                    output += f"{i}. Contributor: {contrib.contributor_name}\n"
                    output += f"   Amount: ${contrib.contribution_amount:,.2f}\n"
                    output += f"   Date: {contrib.contribution_date}\n"
                    output += f"   Recipient: {contrib.recipient_name} ({contrib.political_party})\n"
                    if contrib.contributor_city:
                        output += f"   Location: {contrib.contributor_city}, {contrib.contributor_province}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in search_political_contributions")
                return [TextContent(type="text", text=f"Error searching contributions: {sanitize_error_message(e)}")]

        elif name == "get_top_political_donors":
            try:
                year = arguments.get("year")
                political_party = arguments.get("political_party")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"get_top_political_donors called with year={year}, party={political_party}, limit={limit}")

                donors = await run_sync(
                    political_contrib_client.get_top_donors,
                    limit=limit,
                    year=year,
                    political_party=political_party
                )

                if not donors:
                    return [TextContent(type="text", text="No donor data available.")]

                output = f"Top {len(donors)} political donors"
                if year:
                    output += f" in {year}"
                if political_party:
                    output += f" to {political_party}"
                output += ":\n\n"

                for i, donor in enumerate(donors, 1):
                    output += f"{i}. {donor['donor_name']}\n"
                    output += f"   Total Contributed: ${donor['total_amount']:,.2f}\n\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in get_top_political_donors")
                return [TextContent(type="text", text=f"Error getting top donors: {sanitize_error_message(e)}")]

        elif name == "get_party_fundraising":
            try:
                year = arguments.get("year")
                logger.info(f"get_party_fundraising called with year={year}")

                parties = await run_sync(
                    political_contrib_client.get_party_fundraising,
                    year=year
                )

                if not parties:
                    return [TextContent(type="text", text="No party fundraising data available.")]

                output = f"Political party fundraising"
                if year:
                    output += f" in {year}"
                output += ":\n\n"

                for i, party in enumerate(parties, 1):
                    output += f"{i}. {party['party_name']}\n"
                    output += f"   Total Raised: ${party['total_amount']:,.2f}\n"
                    output += f"   Contributors: {party['contributor_count']:,}\n\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in get_party_fundraising")
                return [TextContent(type="text", text=f"Error getting party fundraising: {sanitize_error_message(e)}")]

        elif name == "search_federal_grants":
            try:
                recipient_name = arguments.get("recipient_name")
                program_name = arguments.get("program_name")
                department = arguments.get("department")
                min_value = arguments.get("min_value")
                max_value = arguments.get("max_value")
                year = arguments.get("year")
                province = arguments.get("province")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_federal_grants called with recipient={recipient_name}, program={program_name}, year={year}, limit={limit}")

                grants = await run_sync(
                    grants_client.search_grants,
                    recipient_name=recipient_name,
                    program_name=program_name,
                    department=department,
                    min_value=min_value,
                    max_value=max_value,
                    year=year,
                    province=province,
                    limit=limit
                )

                if not grants:
                    return [TextContent(type="text", text="No grants found matching the criteria.")]

                output = f"Found {len(grants)} federal grant(s):\n\n"
                for i, grant in enumerate(grants, 1):
                    output += f"{i}. Recipient: {grant.recipient_name}\n"
                    output += f"   Amount: ${grant.agreement_value:,.2f}\n"
                    output += f"   Program: {grant.program_name}\n"
                    output += f"   Department: {grant.owner_org_title}\n"
                    output += f"   Date: {grant.agreement_date or 'N/A'}\n"
                    if grant.recipient_city:
                        output += f"   Location: {grant.recipient_city}, {grant.recipient_province}\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in search_federal_grants")
                return [TextContent(type="text", text=f"Error searching grants: {sanitize_error_message(e)}")]

        elif name == "get_top_grant_recipients":
            try:
                year = arguments.get("year")
                department = arguments.get("department")
                program_name = arguments.get("program_name")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"get_top_grant_recipients called with year={year}, dept={department}, program={program_name}, limit={limit}")

                recipients = await run_sync(
                    grants_client.get_top_recipients,
                    limit=limit,
                    year=year,
                    department=department,
                    program_name=program_name
                )

                if not recipients:
                    return [TextContent(type="text", text="No grant recipient data available.")]

                output = f"Top {len(recipients)} grant recipients"
                if year:
                    output += f" in {year}"
                if department:
                    output += f" from {department}"
                if program_name:
                    output += f" ({program_name})"
                output += ":\n\n"

                for i, recipient in enumerate(recipients, 1):
                    output += f"{i}. {recipient['recipient_name']}\n"
                    output += f"   Total Funding: ${recipient['total_value']:,.2f}\n\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in get_top_grant_recipients")
                return [TextContent(type="text", text=f"Error getting top recipients: {sanitize_error_message(e)}")]

        elif name == "get_grant_program_spending":
            try:
                year = arguments.get("year")
                department = arguments.get("department")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"get_grant_program_spending called with year={year}, dept={department}, limit={limit}")

                programs = await run_sync(
                    grants_client.get_program_spending,
                    year=year,
                    department=department,
                    limit=limit
                )

                if not programs:
                    return [TextContent(type="text", text="No program spending data available.")]

                output = f"Federal grant program spending"
                if year:
                    output += f" in {year}"
                if department:
                    output += f" by {department}"
                output += ":\n\n"

                for i, program in enumerate(programs, 1):
                    output += f"{i}. {program['program_name']}\n"
                    output += f"   Total Spending: ${program['total_value']:,.2f}\n"
                    output += f"   Recipients: {program['recipient_count']:,}\n\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in get_grant_program_spending")
                return [TextContent(type="text", text=f"Error getting program spending: {sanitize_error_message(e)}")]

        elif name == "search_departmental_travel":
            try:
                department = arguments.get("department")
                name = arguments.get("name")
                destination = arguments.get("destination")
                min_amount = arguments.get("min_amount")
                max_amount = arguments.get("max_amount")
                year = arguments.get("year")
                disclosure_group = arguments.get("disclosure_group")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_departmental_travel called with dept={department}, name={name}, dest={destination}, year={year}, limit={limit}")

                travel_records = await run_sync(
                    dept_expenses_client.search_travel,
                    department=department,
                    name=name,
                    destination=destination,
                    min_amount=min_amount,
                    max_amount=max_amount,
                    year=year,
                    disclosure_group=disclosure_group,
                    limit=limit
                )

                if not travel_records:
                    return [TextContent(type="text", text="No travel records found matching the criteria.")]

                output = f"Found {len(travel_records)} departmental travel record(s):\n\n"
                for i, travel in enumerate(travel_records, 1):
                    output += f"{i}. Traveler: {travel.name}\n"
                    output += f"   Title: {travel.title_en or 'N/A'}\n"
                    output += f"   Department: {travel.owner_org_title}\n"
                    output += f"   Destination: {travel.destination_en or 'N/A'}\n"
                    output += f"   Dates: {travel.start_date or 'N/A'} to {travel.end_date or 'N/A'}\n"
                    output += f"   Total Cost: ${travel.total:,.2f}\n"
                    if travel.purpose_en:
                        output += f"   Purpose: {travel.purpose_en[:100]}...\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in search_departmental_travel")
                return [TextContent(type="text", text=f"Error searching travel: {sanitize_error_message(e)}")]

        elif name == "search_departmental_hospitality":
            try:
                department = arguments.get("department")
                name = arguments.get("name")
                location = arguments.get("location")
                min_amount = arguments.get("min_amount")
                max_amount = arguments.get("max_amount")
                year = arguments.get("year")
                disclosure_group = arguments.get("disclosure_group")
                limit = validate_limit(arguments.get("limit"), default=10, max_val=50)
                logger.info(f"search_departmental_hospitality called with dept={department}, name={name}, loc={location}, year={year}, limit={limit}")

                hospitality_records = await run_sync(
                    dept_expenses_client.search_hospitality,
                    department=department,
                    name=name,
                    location=location,
                    min_amount=min_amount,
                    max_amount=max_amount,
                    year=year,
                    disclosure_group=disclosure_group,
                    limit=limit
                )

                if not hospitality_records:
                    return [TextContent(type="text", text="No hospitality records found matching the criteria.")]

                output = f"Found {len(hospitality_records)} departmental hospitality record(s):\n\n"
                for i, hosp in enumerate(hospitality_records, 1):
                    output += f"{i}. Host: {hosp.name}\n"
                    output += f"   Title: {hosp.title_en or 'N/A'}\n"
                    output += f"   Department: {hosp.owner_org_title}\n"
                    output += f"   Location: {hosp.location_en or 'N/A'}\n"
                    output += f"   Date: {hosp.start_date or 'N/A'}\n"
                    output += f"   Attendees: {hosp.attendees or 'N/A'}\n"
                    output += f"   Total Cost: ${hosp.total:,.2f}\n"
                    if hosp.purpose_en:
                        output += f"   Purpose: {hosp.purpose_en[:100]}...\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in search_departmental_hospitality")
                return [TextContent(type="text", text=f"Error searching hospitality: {sanitize_error_message(e)}")]

        elif name == "trace_money_flow":
            try:
                entity_name = arguments["entity_name"]
                year = arguments.get("year")
                include_lobbying = arguments.get("include_lobbying", True)
                include_contracts = arguments.get("include_contracts", True)
                include_grants = arguments.get("include_grants", True)
                include_contributions = arguments.get("include_contributions", True)
                logger.info(f"trace_money_flow called for entity='{entity_name}', year={year}")

                output = f"# Money Flow Analysis: {entity_name}\n\n"
                found_any = False

                # Search political contributions
                if include_contributions:
                    contributions = await run_sync(
                        political_contrib_client.search_contributions,
                        contributor_name=entity_name,
                        year=year,
                        limit=20
                    )
                    if contributions:
                        found_any = True
                        total = sum(c.contribution_amount for c in contributions)
                        output += f"## Political Contributions\n"
                        output += f"Found {len(contributions)} contribution(s) totaling ${total:,.2f}\n\n"
                        for contrib in contributions[:10]:
                            output += f"- ${contrib.contribution_amount:,.2f} to {contrib.recipient_name} ({contrib.political_party})\n"
                            output += f"  Date: {contrib.contribution_date}\n"
                        if len(contributions) > 10:
                            output += f"... and {len(contributions) - 10} more\n"
                        output += "\n"

                # Search lobbying activities
                if include_lobbying:
                    registrations = await run_sync(
                        lobbying_client.search_registrations,
                        client_name=entity_name,
                        active_only=False,
                        limit=20
                    )
                    communications = await run_sync(
                        lobbying_client.search_communications,
                        client_name=entity_name,
                        limit=20
                    )
                    if registrations or communications:
                        found_any = True
                        output += f"## Lobbying Activities\n"
                        output += f"Found {len(registrations)} registration(s) and {len(communications)} communication(s)\n\n"
                        if registrations:
                            output += "### Active Registrations:\n"
                            for reg in registrations[:5]:
                                output += f"- {reg.registrant_name} (Type: {reg.reg_type})\n"
                                if reg.subject_matters:
                                    output += f"  Topics: {', '.join(reg.subject_matters[:3])}\n"
                        if communications:
                            output += "\n### Recent Communications:\n"
                            for comm in communications[:5]:
                                output += f"- {comm.comm_date}: {comm.registrant_name}\n"
                                if comm.institutions:
                                    output += f"  With: {', '.join(comm.institutions[:2])}\n"
                        output += "\n"

                # Search government contracts
                if include_contracts:
                    contracts = await run_sync(
                        contracts_client.search_contracts,
                        vendor_name=entity_name,
                        year=year,
                        limit=20
                    )
                    if contracts:
                        found_any = True
                        total = sum(c.contract_value for c in contracts)
                        output += f"## Government Contracts\n"
                        output += f"Found {len(contracts)} contract(s) totaling ${total:,.2f}\n\n"
                        for contract in contracts[:10]:
                            output += f"- ${contract.contract_value:,.2f} from {contract.owner_org_title}\n"
                            output += f"  Date: {contract.contract_date}\n"
                        if len(contracts) > 10:
                            output += f"... and {len(contracts) - 10} more\n"
                        output += "\n"

                # Search federal grants
                if include_grants:
                    grants = await run_sync(
                        grants_client.search_grants,
                        recipient_name=entity_name,
                        year=year,
                        limit=20
                    )
                    if grants:
                        found_any = True
                        total = sum(g.agreement_value for g in grants)
                        output += f"## Federal Grants\n"
                        output += f"Found {len(grants)} grant(s) totaling ${total:,.2f}\n\n"
                        for grant in grants[:10]:
                            output += f"- ${grant.agreement_value:,.2f} for {grant.program_name}\n"
                            output += f"  From: {grant.owner_org_title}\n"
                            output += f"  Date: {grant.agreement_date}\n"
                        if len(grants) > 10:
                            output += f"... and {len(grants) - 10} more\n"
                        output += "\n"

                if not found_any:
                    output += "No financial or lobbying activity found for this entity.\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in trace_money_flow")
                return [TextContent(type="text", text=f"Error tracing money flow: {sanitize_error_message(e)}")]

        elif name == "analyze_mp_finances":
            try:
                mp_name = arguments["mp_name"]
                fiscal_year = arguments.get("fiscal_year", 2026)
                include_lobbying = arguments.get("include_lobbying", True)
                logger.info(f"analyze_mp_finances called for MP='{mp_name}', year={fiscal_year}")

                output = f"# Financial Analysis: {mp_name}\n\n"

                # Get MP expenses
                expenses = await run_sync(expenditure_client.search_by_name, mp_name, fiscal_year, 1)
                if expenses:
                    exp = expenses[0]
                    output += f"## Office Expenses (Q1 {fiscal_year})\n"
                    output += f"- Total: ${exp.total:,.2f}\n"
                    output += f"- Salaries & Benefits: ${exp.personnel:,.2f}\n"
                    output += f"- Travel: ${exp.travel:,.2f}\n"
                    output += f"- Hospitality: ${exp.hospitality:,.2f}\n"
                    output += f"- Contracts: ${exp.contracts:,.2f}\n"
                    output += f"- Constituency: {exp.constituency}\n"
                    output += f"- Party: {exp.party}\n\n"

                # Search lobbying communications
                if include_lobbying:
                    communications = await run_sync(
                        lobbying_client.search_communications,
                        official_name=mp_name,
                        limit=20
                    )
                    if communications:
                        output += f"## Lobbying Communications\n"
                        output += f"Found {len(communications)} lobbying communication(s) with this MP\n\n"
                        for comm in communications[:10]:
                            output += f"- {comm.comm_date}: {comm.client_org_name}\n"
                            output += f"  Lobbyist: {comm.registrant_name}\n"
                            if comm.subject_matters:
                                output += f"  Topics: {', '.join(comm.subject_matters[:2])}\n"
                        output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in analyze_mp_finances")
                return [TextContent(type="text", text=f"Error analyzing MP finances: {sanitize_error_message(e)}")]

        elif name == "compare_party_funding":
            try:
                year = arguments.get("year")
                include_donor_analysis = arguments.get("include_donor_analysis", True)
                min_donation = arguments.get("min_donation")
                logger.info(f"compare_party_funding called for year={year}")

                output = f"# Political Party Funding Comparison\n"
                if year:
                    output += f"Year: {year}\n"
                output += "\n"

                # Get party fundraising
                parties = await run_sync(political_contrib_client.get_party_fundraising, year=year)

                if not parties:
                    return [TextContent(type="text", text="No party fundraising data available.")]

                output += f"## Fundraising Totals\n\n"
                for i, party in enumerate(parties[:10], 1):
                    output += f"{i}. **{party['party_name']}**\n"
                    output += f"   - Total Raised: ${party['total_amount']:,.2f}\n"
                    output += f"   - Contributors: {party['contributor_count']:,}\n"
                    avg = party['total_amount'] / party['contributor_count'] if party['contributor_count'] > 0 else 0
                    output += f"   - Average Donation: ${avg:,.2f}\n\n"

                # Get top donors for major parties if requested
                if include_donor_analysis:
                    major_parties = ['Liberal', 'Conservative', 'NDP', 'Green', 'Bloc']
                    output += f"## Top Donors by Party\n\n"
                    for party_name in major_parties:
                        party_match = next((p for p in parties if party_name.lower() in p['party_name'].lower()), None)
                        if party_match:
                            donors = await run_sync(
                                political_contrib_client.get_top_donors,
                                limit=5,
                                year=year,
                                political_party=party_name
                            )
                            if donors:
                                output += f"### {party_name}\n"
                                for donor in donors:
                                    output += f"- {donor['donor_name']}: ${donor['total_amount']:,.2f}\n"
                                output += "\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in compare_party_funding")
                return [TextContent(type="text", text=f"Error comparing party funding: {sanitize_error_message(e)}")]

        elif name == "government_spending_analysis":
            try:
                focus = arguments.get("focus", "overview")
                department_name = arguments.get("department_name")
                year = arguments.get("year")
                limit = validate_limit(arguments.get("limit"), default=20, max_val=50)
                logger.info(f"government_spending_analysis called with focus={focus}, dept={department_name}, year={year}")

                output = f"# Government Spending Analysis\n"
                if year:
                    output += f"Year: {year}\n"
                output += f"Focus: {focus}\n\n"

                if focus == "overview":
                    # Get top contractors, grant recipients, and departmental spending
                    contractors = await run_sync(contracts_client.get_top_vendors, limit=10, year=year)
                    grant_recipients = await run_sync(grants_client.get_top_recipients, limit=10, year=year)

                    output += f"## Top Government Contractors\n\n"
                    for i, vendor in enumerate(contractors, 1):
                        output += f"{i}. {vendor['vendor_name']}: ${vendor['total_value']:,.2f}\n"

                    output += f"\n## Top Grant Recipients\n\n"
                    for i, recipient in enumerate(grant_recipients, 1):
                        output += f"{i}. {recipient['recipient_name']}: ${recipient['total_value']:,.2f}\n"

                elif focus == "department" and department_name:
                    # Analyze specific department
                    dept_contracts = await run_sync(
                        contracts_client.search_contracts,
                        department=department_name,
                        year=year,
                        limit=limit
                    )
                    dept_grants = await run_sync(
                        grants_client.search_grants,
                        department=department_name,
                        year=year,
                        limit=limit
                    )

                    contract_total = sum(c.contract_value for c in dept_contracts) if dept_contracts else 0
                    grant_total = sum(g.agreement_value for g in dept_grants) if dept_grants else 0

                    output += f"## {department_name} Spending\n\n"
                    output += f"- Contracts: ${contract_total:,.2f} ({len(dept_contracts)} contracts)\n"
                    output += f"- Grants: ${grant_total:,.2f} ({len(dept_grants)} grants)\n"
                    output += f"- **Total: ${contract_total + grant_total:,.2f}**\n\n"

                    if dept_contracts:
                        output += f"### Top Contractors\n"
                        for contract in dept_contracts[:10]:
                            output += f"- {contract.vendor_name}: ${contract.contract_value:,.2f}\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in government_spending_analysis")
                return [TextContent(type="text", text=f"Error analyzing spending: {sanitize_error_message(e)}")]

        elif name == "conflict_of_interest_check":
            try:
                entity_name = arguments["entity_name"]
                year = arguments.get("year")
                threshold_amount = arguments.get("threshold_amount", 100000)
                logger.info(f"conflict_of_interest_check called for entity='{entity_name}', threshold=${threshold_amount}")

                output = f"# Conflict of Interest Analysis: {entity_name}\n\n"
                flags = []

                # Get all financial activities
                contributions = await run_sync(
                    political_contrib_client.search_contributions,
                    contributor_name=entity_name,
                    year=year,
                    limit=50
                )
                contracts = await run_sync(
                    contracts_client.search_contracts,
                    vendor_name=entity_name,
                    year=year,
                    min_value=threshold_amount,
                    limit=50
                )
                grants = await run_sync(
                    grants_client.search_grants,
                    recipient_name=entity_name,
                    year=year,
                    min_value=threshold_amount,
                    limit=50
                )
                lobbying_regs = await run_sync(
                    lobbying_client.search_registrations,
                    client_name=entity_name,
                    active_only=False,
                    limit=50
                )

                # Analyze for conflicts
                if contributions and (contracts or grants):
                    flags.append("⚠️ Entity has both made political contributions AND received government funds")

                if contributions and lobbying_regs:
                    flags.append("⚠️ Entity has both made political contributions AND engaged in lobbying")

                if contracts and lobbying_regs:
                    flags.append("⚠️ Entity has both received government contracts AND engaged in lobbying")

                # Summary
                output += f"## Summary\n\n"
                output += f"- Political Contributions: {len(contributions)} (${sum(c.contribution_amount for c in contributions):,.2f})\n"
                output += f"- Government Contracts: {len(contracts)} (>${threshold_amount:,.0f})\n"
                output += f"- Federal Grants: {len(grants)} (>${threshold_amount:,.0f})\n"
                output += f"- Lobbying Registrations: {len(lobbying_regs)}\n\n"

                if flags:
                    output += f"## Potential Concerns\n\n"
                    for flag in flags:
                        output += f"{flag}\n"
                    output += "\n"
                else:
                    output += "✅ No obvious conflicts of interest detected.\n\n"

                # Detail high-value transactions
                if contracts:
                    output += f"## High-Value Contracts (>${threshold_amount:,.0f})\n\n"
                    for contract in contracts[:10]:
                        output += f"- ${contract.contract_value:,.2f} from {contract.owner_org_title} ({contract.contract_date})\n"

                if grants:
                    output += f"\n## High-Value Grants (>${threshold_amount:,.0f})\n\n"
                    for grant in grants[:10]:
                        output += f"- ${grant.agreement_value:,.2f} for {grant.program_name} ({grant.agreement_date})\n"

                return [TextContent(type="text", text=output)]
            except Exception as e:
                logger.exception(f"Error in conflict_of_interest_check")
                return [TextContent(type="text", text=f"Error checking conflicts: {sanitize_error_message(e)}")]

        else:
            logger.warning(f"Unknown tool requested: {name}")
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.exception(f"Unexpected error executing {name}")
        return [TextContent(type="text", text=f"Error executing {name}: {sanitize_error_message(e)}")]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
