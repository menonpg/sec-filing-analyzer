"""
SEC Filing List Tool

Retrieves list of filings for a company by CIK.
Supports filtering by form type and date range.
"""

import httpx
import json
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
        cik: Central Index Key (with or without leading zeros)
        form_types: Filter by form types (e.g., ["10-K", "10-Q", "8-K"])
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum number of filings to return (default 20)
        
    Returns:
        dict with company info and filtered filings list
    """
    # Normalize CIK to 10 digits
    cik_clean = cik.replace("CIK", "").replace("cik", "").strip()
    cik_padded = cik_clean.zfill(10)
    
    # Normalize form types to uppercase
    if form_types:
        form_types = [f.upper() for f in form_types]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            SEC_SUBMISSIONS.format(cik=cik_padded),
            headers={"User-Agent": USER_AGENT}
        )
        
        if response.status_code == 404:
            return {"error": f"Company not found for CIK: {cik}"}
        
        response.raise_for_status()
        data = response.json()
        
        # Extract recent filings
        recent = data.get("filings", {}).get("recent", {})
        
        # Build filtered list
        filings = []
        
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        report_dates = recent.get("reportDate", [])
        
        for i in range(len(forms)):
            form = forms[i]
            filing_date = filing_dates[i] if i < len(filing_dates) else None
            
            # Filter by form type
            if form_types and form.upper() not in form_types:
                continue
            
            # Filter by date range
            if start_date and filing_date and filing_date < start_date:
                continue
            if end_date and filing_date and filing_date > end_date:
                continue
            
            # Build filing URL
            accession = accessions[i] if i < len(accessions) else None
            primary_doc = primary_docs[i] if i < len(primary_docs) else None
            
            filing_url = None
            if accession and primary_doc:
                accession_nodash = accession.replace("-", "")
                filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik_clean)}/{accession_nodash}/{primary_doc}"
            
            filings.append({
                "form": form,
                "filingDate": filing_date,
                "reportDate": report_dates[i] if i < len(report_dates) else None,
                "accessionNumber": accession,
                "primaryDocument": primary_doc,
                "url": filing_url
            })
            
            if len(filings) >= limit:
                break
        
        return {
            "cik": cik_clean,
            "company_name": data.get("name"),
            "total_filings": len(forms),
            "filtered_count": len(filings),
            "filters_applied": {
                "form_types": form_types,
                "start_date": start_date,
                "end_date": end_date
            },
            "filings": filings
        }


async def get_latest_filing(cik: str, form_type: str = "10-Q") -> Optional[dict]:
    """
    Get the most recent filing of a specific type.
    
    Args:
        cik: Central Index Key
        form_type: Type of filing (default "10-Q")
        
    Returns:
        Filing dict or None if not found
    """
    result = await get_filings(cik, form_types=[form_type], limit=1)
    
    if "error" in result:
        return None
    
    filings = result.get("filings", [])
    return filings[0] if filings else None


# Dify tool schema (OpenAPI format)
TOOL_SCHEMA = {
    "name": "get_filings",
    "description": "Get list of SEC filings for a company by their CIK (Central Index Key). Filter by form type (10-K for annual, 10-Q for quarterly, 8-K for current events) and date range. Returns filing dates, accession numbers, and direct URLs to the documents.",
    "parameters": {
        "type": "object",
        "properties": {
            "cik": {
                "type": "string",
                "description": "SEC Central Index Key for the company (e.g., '1775097' or '0001775097')"
            },
            "form_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by form types. Common values: '10-K' (annual), '10-Q' (quarterly), '8-K' (current events), '4' (insider trading)"
            },
            "start_date": {
                "type": "string",
                "description": "Filter filings on or after this date (YYYY-MM-DD format)"
            },
            "end_date": {
                "type": "string",
                "description": "Filter filings on or before this date (YYYY-MM-DD format)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of filings to return (default 20)"
            }
        },
        "required": ["cik"]
    }
}


# CLI for testing
if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        cik = sys.argv[1] if len(sys.argv) > 1 else "1775097"
        form_types = sys.argv[2].split(",") if len(sys.argv) > 2 else ["10-Q", "10-K"]
        
        print(f"Getting filings for CIK: {cik}")
        print(f"Form types: {form_types}\n")
        
        result = await get_filings(cik, form_types=form_types, limit=5)
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())
