"""
SEC Filing Analyzer - Tools API

FastAPI server that exposes SEC tools as HTTP endpoints.
Connect this to Dify as custom tools.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

# Import our tools
from dify.tools.search_company import search_company
from dify.tools.get_filings import get_filings, get_latest_filing
from dify.tools.fetch_filing import fetch_filing

app = FastAPI(
    title="SEC Filing Analyzer API",
    description="Tools for searching and analyzing SEC EDGAR filings",
    version="0.1.0"
)

# CORS for Dify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class CompanySearchRequest(BaseModel):
    query: str


class GetFilingsRequest(BaseModel):
    cik: str
    form_types: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 20


class FetchFilingRequest(BaseModel):
    cik: str
    accession_number: str
    primary_document: Optional[str] = None


# Health Check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "sec-filing-analyzer"}


# Tool Endpoints
@app.post("/tools/search_company")
async def api_search_company(request: CompanySearchRequest):
    """
    Search for a company by name or ticker.
    Returns CIK, company info, and recent filings.
    """
    result = await search_company(request.query)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/tools/get_filings")
async def api_get_filings(request: GetFilingsRequest):
    """
    Get list of SEC filings for a company.
    Filter by form type and date range.
    """
    result = await get_filings(
        cik=request.cik,
        form_types=request.form_types,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/tools/fetch_filing")
async def api_fetch_filing(request: FetchFilingRequest):
    """
    Fetch and parse an SEC filing document.
    Returns sections, tables, and full text.
    """
    result = await fetch_filing(
        cik=request.cik,
        accession_number=request.accession_number,
        primary_document=request.primary_document
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/tools/latest_filing/{cik}")
async def api_latest_filing(cik: str, form_type: str = "10-Q"):
    """
    Get the most recent filing of a specific type.
    """
    result = await get_latest_filing(cik, form_type)
    if not result:
        raise HTTPException(status_code=404, detail=f"No {form_type} found for CIK {cik}")
    return result


# Quick test endpoints
@app.get("/test/bcred")
async def test_bcred():
    """Quick test: Look up Blue Owl Capital Corporation (BCRED)"""
    result = await search_company("BCRED")
    return result


@app.get("/test/bcred/filings")
async def test_bcred_filings():
    """Quick test: Get BCRED's recent 10-Q and 10-K filings"""
    result = await get_filings("1775097", form_types=["10-Q", "10-K"], limit=5)
    return result


# OpenAPI schema for Dify custom tools
@app.get("/openapi-tools.json")
async def openapi_tools():
    """
    Returns OpenAPI schema formatted for Dify custom tools import.
    """
    import os
    base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "sec-filing-analyzer-production.up.railway.app")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "SEC Filing Analyzer Tools",
            "version": "1.0.0"
        },
        "servers": [
            {"url": base_url}
        ],
        "paths": {
            "/tools/search_company": {
                "post": {
                    "operationId": "searchCompany",
                    "summary": "Search for a company by name or ticker",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Company name or ticker (e.g., 'AAPL', 'BCRED')"}
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Company info with CIK and recent filings"}
                    }
                }
            },
            "/tools/get_filings": {
                "post": {
                    "operationId": "getFilings",
                    "summary": "Get SEC filings for a company",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cik": {"type": "string", "description": "Company CIK"},
                                        "form_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by form types"},
                                        "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                                        "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                                        "limit": {"type": "integer", "description": "Max results"}
                                    },
                                    "required": ["cik"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "List of filings with URLs"}
                    }
                }
            },
            "/tools/fetch_filing": {
                "post": {
                    "operationId": "fetchFiling",
                    "summary": "Fetch and parse an SEC filing",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cik": {"type": "string"},
                                        "accession_number": {"type": "string"},
                                        "primary_document": {"type": "string"}
                                    },
                                    "required": ["cik", "accession_number"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Parsed filing with sections and tables"}
                    }
                }
            }
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
