"""
SEC Filing List Tool

Retrieves list of filings for a company by CIK.
Supports filtering by form type and date range.
"""

import httpx
from typing import List, Optional
from datetime import datetime


SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
USER_AGENT = "SEC-Filing-Analyzer contact@themenonlab.com"


async def get_filings(
    cik: str,
    form_types: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    Get list of filings for a company.
    
    Args:
        cik: Central Index Key
        form_types: Filter by form types (e.g., ["10-K", "10-Q"])
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of filings to return
        
    Returns:
        dict with company info and filtered filings list
    """
    # TODO: Implement filing retrieval
    # 1. Fetch submissions JSON
    # 2. Filter by form type if specified
    # 3. Filter by date range if specified
    # 4. Return structured list with accession numbers
    
    raise NotImplementedError("get_filings not yet implemented")


def filter_filings(filings: dict, form_types: List[str], start_date: str, end_date: str) -> List[dict]:
    """
    Filter filings by form type and date range.
    """
    recent = filings.get("filings", {}).get("recent", {})
    
    results = []
    for i, form in enumerate(recent.get("form", [])):
        if form_types and form not in form_types:
            continue
            
        filing_date = recent["filingDate"][i]
        if start_date and filing_date < start_date:
            continue
        if end_date and filing_date > end_date:
            continue
            
        results.append({
            "accessionNumber": recent["accessionNumber"][i],
            "form": form,
            "filingDate": filing_date,
            "reportDate": recent.get("reportDate", [None] * len(recent["form"]))[i],
            "primaryDocument": recent.get("primaryDocument", [None] * len(recent["form"]))[i],
        })
    
    return results


# Dify tool schema
TOOL_SCHEMA = {
    "name": "get_filings",
    "description": "Get list of SEC filings for a company. Filter by form type (10-K, 10-Q, 8-K) and date range.",
    "parameters": {
        "type": "object",
        "properties": {
            "cik": {
                "type": "string",
                "description": "SEC Central Index Key for the company"
            },
            "form_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Form types to filter (e.g., ['10-K', '10-Q'])"
            },
            "start_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format"
            },
            "end_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format"
            }
        },
        "required": ["cik"]
    }
}
