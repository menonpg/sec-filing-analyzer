"""
SEC Company Search Tool

Searches SEC EDGAR for companies by name or ticker.
Returns CIK, full name, SIC code, and recent filings.
"""

import httpx
import json
import re
from typing import Optional, List
from dataclasses import dataclass

SEC_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"
USER_AGENT = "SEC-Filing-Analyzer contact@themenonlab.com"


@dataclass
class CompanyInfo:
    cik: str
    name: str
    ticker: str
    sic: str
    sic_description: str
    state: str
    fiscal_year_end: str
    recent_filings: List[dict]


async def search_company(query: str) -> dict:
    """
    Search for a company by name or ticker.
    
    Args:
        query: Company name or ticker symbol (e.g., "BCRED", "Apple", "Blue Owl")
        
    Returns:
        dict with cik, name, ticker, sic, sic_description, recent_filings
    """
    query = query.strip().upper()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, try to find by ticker in the company tickers file
        tickers_response = await client.get(
            SEC_COMPANY_TICKERS,
            headers={"User-Agent": USER_AGENT}
        )
        tickers_response.raise_for_status()
        tickers_data = tickers_response.json()
        
        # Search through tickers
        cik = None
        matched_name = None
        matched_ticker = None
        
        for key, company in tickers_data.items():
            ticker = company.get("ticker", "").upper()
            name = company.get("title", "").upper()
            
            # Exact ticker match
            if ticker == query:
                cik = str(company["cik_str"])
                matched_name = company["title"]
                matched_ticker = ticker
                break
            
            # Name contains query
            if query in name and not cik:
                cik = str(company["cik_str"])
                matched_name = company["title"]
                matched_ticker = ticker
        
        if not cik:
            return {
                "error": f"Company not found: {query}",
                "suggestion": "Try the full company name or exact ticker symbol"
            }
        
        # Now get full company details
        cik_padded = cik.zfill(10)
        submissions_response = await client.get(
            SEC_SUBMISSIONS.format(cik=cik_padded),
            headers={"User-Agent": USER_AGENT}
        )
        submissions_response.raise_for_status()
        data = submissions_response.json()
        
        # Extract recent filings (last 10)
        recent = data.get("filings", {}).get("recent", {})
        recent_filings = []
        
        forms = recent.get("form", [])[:10]
        filing_dates = recent.get("filingDate", [])[:10]
        accessions = recent.get("accessionNumber", [])[:10]
        primary_docs = recent.get("primaryDocument", [])[:10]
        
        for i in range(min(10, len(forms))):
            recent_filings.append({
                "form": forms[i] if i < len(forms) else None,
                "filingDate": filing_dates[i] if i < len(filing_dates) else None,
                "accessionNumber": accessions[i] if i < len(accessions) else None,
                "primaryDocument": primary_docs[i] if i < len(primary_docs) else None,
            })
        
        return {
            "cik": cik,
            "cik_padded": cik_padded,
            "name": data.get("name", matched_name),
            "ticker": matched_ticker or (data.get("tickers", [None])[0] if data.get("tickers") else None),
            "sic": data.get("sic", ""),
            "sic_description": data.get("sicDescription", ""),
            "state": data.get("stateOfIncorporation", ""),
            "fiscal_year_end": data.get("fiscalYearEnd", ""),
            "business_address": data.get("addresses", {}).get("business", {}),
            "recent_filings": recent_filings
        }


async def get_company_cik(ticker_or_name: str) -> Optional[str]:
    """
    Quick lookup to get just the CIK for a company.
    """
    result = await search_company(ticker_or_name)
    if "error" in result:
        return None
    return result.get("cik")


# Dify tool schema (OpenAPI format)
TOOL_SCHEMA = {
    "name": "search_company",
    "description": "Search SEC EDGAR for a company by name or ticker symbol. Returns the company's CIK (Central Index Key), full name, industry classification (SIC code), state of incorporation, and list of recent SEC filings. Use this to find a company before fetching their filings.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Company name or ticker symbol. Examples: 'AAPL', 'Apple', 'BCRED', 'Blue Owl Capital'"
            }
        },
        "required": ["query"]
    }
}


# CLI for testing
if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        query = sys.argv[1] if len(sys.argv) > 1 else "BCRED"
        print(f"Searching for: {query}\n")
        
        result = await search_company(query)
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())
