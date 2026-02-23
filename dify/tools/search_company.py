"""
SEC Company Search Tool

Searches SEC EDGAR for companies by name or ticker.
Returns CIK, full name, SIC code, and recent filings.
"""

import httpx
from typing import Optional
import json


SEC_COMPANY_SEARCH = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
USER_AGENT = "SEC-Filing-Analyzer contact@themenonlab.com"


async def search_company(query: str) -> dict:
    """
    Search for a company by name or ticker.
    
    Args:
        query: Company name or ticker symbol
        
    Returns:
        dict with cik, name, ticker, sic, recent_filings
    """
    # TODO: Implement company search
    # 1. Search SEC EDGAR by company name
    # 2. If ticker provided, lookup CIK directly
    # 3. Fetch company submissions for details
    # 4. Return structured response
    
    raise NotImplementedError("search_company not yet implemented")


async def get_company_info(cik: str) -> dict:
    """
    Get detailed company information from SEC submissions endpoint.
    
    Args:
        cik: Central Index Key (will be zero-padded to 10 digits)
        
    Returns:
        dict with company details and filing history
    """
    cik_padded = cik.zfill(10)
    url = SEC_SUBMISSIONS.format(cik=cik_padded)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        return response.json()


# Dify tool schema
TOOL_SCHEMA = {
    "name": "search_company",
    "description": "Search SEC EDGAR for a company by name or ticker. Returns CIK, full company name, industry classification, and recent filings.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Company name or ticker symbol (e.g., 'Apple', 'AAPL', 'BCRED')"
            }
        },
        "required": ["query"]
    }
}
