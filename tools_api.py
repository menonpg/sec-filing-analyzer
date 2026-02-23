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
from dify.tools.vector_store import get_vector_store

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
    summary_only: bool = False  # Return only key metrics (for comparisons)
    index: bool = False  # Also index into vector store


class IndexFilingRequest(BaseModel):
    cik: str
    accession_number: str
    form_type: str = "10-Q"
    filing_date: str = ""
    company_name: str = ""


class SemanticSearchRequest(BaseModel):
    query: str
    cik: Optional[str] = None
    accession_number: Optional[str] = None  # Scope to specific filing
    form_type: Optional[str] = None
    limit: int = 10


class CompareFilingsRequest(BaseModel):
    cik: str
    accession_1: str
    accession_2: str
    topics: Optional[List[str]] = None


class SmartAnalyzeRequest(BaseModel):
    """Smart router that picks regex or RAG based on query type."""
    query: str
    company: str  # Company name or ticker
    form_type: str = "10-Q"  # Default to quarterly


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
    Use summary_only=true for comparisons (returns key metrics only).
    """
    result = await fetch_filing(
        cik=request.cik,
        accession_number=request.accession_number,
        primary_document=request.primary_document,
        summary_only=request.summary_only
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


# ============ RAG ENDPOINTS ============

@app.post("/tools/index_filing")
async def api_index_filing(request: IndexFilingRequest):
    """
    Index a filing into the vector store for semantic search.
    Fetches the filing, chunks it, and stores embeddings in Qdrant.
    """
    # First fetch the filing
    filing = await fetch_filing(
        cik=request.cik,
        accession_number=request.accession_number
    )
    
    if "error" in filing:
        raise HTTPException(status_code=404, detail=filing["error"])
    
    # Parse sections from the filing
    sections = {}
    full_text = filing.get("full_text", "")
    
    # Try to extract sections if available
    if filing.get("sections"):
        # For now, use full text chunked by detected sections
        # In production, would extract actual section content
        sections["full_document"] = full_text
    else:
        sections["full_document"] = full_text
    
    # Index into vector store
    store = get_vector_store()
    result = await store.index_filing(
        cik=request.cik,
        accession_number=request.accession_number,
        form_type=request.form_type,
        filing_date=request.filing_date or filing.get("filing_date", ""),
        company_name=request.company_name,
        sections=sections
    )
    
    return result


@app.post("/tools/semantic_search")
async def api_semantic_search(request: SemanticSearchRequest):
    """
    Semantic search across indexed SEC filings.
    Use this to find relevant content about a topic across filings.
    Pass accession_number to scope to a specific filing.
    """
    store = get_vector_store()
    results = await store.search(
        query=request.query,
        cik=request.cik,
        accession_number=request.accession_number,
        form_type=request.form_type,
        limit=request.limit
    )
    
    return {
        "query": request.query,
        "filters": {
            "cik": request.cik,
            "accession_number": request.accession_number,
            "form_type": request.form_type
        },
        "results": results,
        "count": len(results)
    }


@app.post("/tools/compare_filings")
async def api_compare_filings(request: CompareFilingsRequest):
    """
    Compare two indexed filings by topic.
    Retrieves relevant chunks from each filing for side-by-side comparison.
    Both filings must be indexed first using index_filing.
    """
    store = get_vector_store()
    result = await store.compare_filings(
        cik=request.cik,
        accession_1=request.accession_1,
        accession_2=request.accession_2,
        topics=request.topics
    )
    
    return result


@app.get("/tools/vector_stats")
async def api_vector_stats():
    """Get statistics about the vector store (indexed filings count, etc.)."""
    store = get_vector_store()
    return store.get_stats()


@app.get("/tools/indexed_filings")
async def api_list_indexed(cik: Optional[str] = None):
    """List all indexed filings in the vector store."""
    store = get_vector_store()
    return {"filings": store.list_indexed_filings(cik)}


# ============ SMART ROUTER ============

# Keywords that indicate structured data (use Regex mode)
METRIC_KEYWORDS = [
    'revenue', 'sales', 'income', 'eps', 'earnings', 'margin', 'profit',
    'cash flow', 'ebitda', 'assets', 'liabilities', 'debt', 'equity',
    'dividend', 'buyback', 'repurchase', 'shares outstanding',
    'how much', 'what was', 'total', 'net'
]

# Keywords that indicate narrative content (use RAG mode)
NARRATIVE_KEYWORDS = [
    'risk', 'factor', 'guidance', 'outlook', 'strategy', 'competition',
    'regulation', 'legal', 'lawsuit', 'investigation', 'supply chain',
    'compare', 'change', 'different', 'versus', 'vs', 'trend',
    'why', 'how did', 'explain', 'describe', 'summary of', 'overview'
]


def classify_query(query: str) -> str:
    """Classify query as 'metrics' or 'narrative'."""
    query_lower = query.lower()
    
    metric_score = sum(1 for kw in METRIC_KEYWORDS if kw in query_lower)
    narrative_score = sum(1 for kw in NARRATIVE_KEYWORDS if kw in query_lower)
    
    # Comparison keywords strongly favor RAG
    if any(word in query_lower for word in ['compare', 'versus', 'vs', 'change', 'different']):
        return 'narrative'
    
    if metric_score > narrative_score:
        return 'metrics'
    elif narrative_score > metric_score:
        return 'narrative'
    else:
        # Default to metrics (faster)
        return 'metrics'


@app.post("/tools/analyze")
async def smart_analyze(request: SmartAnalyzeRequest):
    """
    Smart SEC filing analyzer - automatically routes to Regex or RAG mode.
    
    - Metrics questions (revenue, EPS, margins) → Fast regex extraction
    - Narrative questions (risks, guidance, comparisons) → RAG semantic search
    
    Just ask your question - this endpoint figures out the best approach.
    """
    query = request.query
    mode = classify_query(query)
    
    # Step 1: Find the company
    company_result = await search_company(request.company)
    if "error" in company_result:
        return {"error": f"Company not found: {request.company}", "query": query}
    
    cik = company_result["cik"]
    company_name = company_result.get("name", request.company)
    
    # Step 2: Get latest filing of requested type
    filings_result = await get_filings(cik, form_types=[request.form_type], limit=1)
    if "error" in filings_result or not filings_result.get("filings"):
        return {"error": f"No {request.form_type} found for {company_name}", "query": query}
    
    latest_filing = filings_result["filings"][0]
    accession = latest_filing["accessionNumber"]
    filing_date = latest_filing.get("filingDate", "")
    
    result = {
        "query": query,
        "company": company_name,
        "cik": cik,
        "filing": {
            "form_type": request.form_type,
            "accession_number": accession,
            "filing_date": filing_date
        },
        "mode": mode
    }
    
    if mode == 'metrics':
        # Fast path: Regex extraction
        filing_data = await fetch_filing(cik, accession, summary_only=True)
        result["key_metrics"] = filing_data.get("key_metrics", {})
        result["analysis_type"] = "regex_extraction"
        
    else:
        # RAG path: Index if needed, then search
        store = get_vector_store()
        
        # Check if already indexed
        if not store.is_indexed(cik, accession):
            # Fetch and index the filing
            filing_data = await fetch_filing(cik, accession)
            if "error" not in filing_data:
                await store.index_filing(
                    cik=cik,
                    accession_number=accession,
                    form_type=request.form_type,
                    filing_date=filing_date,
                    company_name=company_name,
                    sections={"full_document": filing_data.get("full_text", "")}
                )
                result["indexed"] = True
        else:
            result["indexed"] = "already_indexed"
        
        # Semantic search - SCOPED TO THIS SPECIFIC FILING
        search_results = await store.search(
            query, 
            cik=cik, 
            accession_number=accession,  # Scope to this filing only
            limit=5
        )
        result["relevant_context"] = search_results
        result["analysis_type"] = "rag_semantic_search"
    
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
    # Hardcoded for reliability - Railway env vars can be inconsistent
    base_url = "https://sec-filing-analyzer-production.up.railway.app"
    
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
                                        "cik": {"type": "string", "description": "Company CIK"},
                                        "accession_number": {"type": "string", "description": "Filing accession number"},
                                        "primary_document": {"type": "string", "description": "Document filename (optional)"},
                                        "summary_only": {"type": "boolean", "description": "If true, return only key metrics (revenue, income, EPS, segments) - use this for comparisons", "default": False}
                                    },
                                    "required": ["cik", "accession_number"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Parsed filing with sections and tables (or key_metrics if summary_only=true)"}
                    }
                }
            },
            "/tools/index_filing": {
                "post": {
                    "operationId": "indexFiling",
                    "summary": "Index a filing into vector store for semantic search",
                    "description": "Fetches, chunks, and indexes a filing into Qdrant. Required before using semantic_search or compare_filings.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cik": {"type": "string", "description": "Company CIK"},
                                        "accession_number": {"type": "string", "description": "Filing accession number"},
                                        "form_type": {"type": "string", "description": "Form type (10-Q, 10-K, 8-K)", "default": "10-Q"},
                                        "filing_date": {"type": "string", "description": "Filing date"},
                                        "company_name": {"type": "string", "description": "Company name"}
                                    },
                                    "required": ["cik", "accession_number"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Indexing results with chunk count"}
                    }
                }
            },
            "/tools/semantic_search": {
                "post": {
                    "operationId": "semanticSearch",
                    "summary": "Search indexed filings by topic/question",
                    "description": "Semantic search across indexed SEC filings. Pass accession_number to scope to ONE filing (recommended). Without it, searches across ALL indexed filings for that company.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Search query (e.g., 'revenue growth', 'risk factors', 'cash flow')"},
                                        "cik": {"type": "string", "description": "Filter by company CIK"},
                                        "accession_number": {"type": "string", "description": "Filter by specific filing accession number (recommended for precision)"},
                                        "form_type": {"type": "string", "description": "Filter by form type (optional)"},
                                        "limit": {"type": "integer", "description": "Max results", "default": 10}
                                    },
                                    "required": ["query"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Matching text chunks with relevance scores"}
                    }
                }
            },
            "/tools/compare_filings": {
                "post": {
                    "operationId": "compareFilings",
                    "summary": "Compare two indexed filings side-by-side",
                    "description": "Retrieves relevant content from two filings for comparison. Both filings must be indexed first.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cik": {"type": "string", "description": "Company CIK"},
                                        "accession_1": {"type": "string", "description": "First filing accession number"},
                                        "accession_2": {"type": "string", "description": "Second filing accession number"},
                                        "topics": {"type": "array", "items": {"type": "string"}, "description": "Topics to compare (e.g., ['revenue', 'risk factors']). Defaults to common financial topics."}
                                    },
                                    "required": ["cik", "accession_1", "accession_2"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Side-by-side comparison of filing content by topic"}
                    }
                }
            },
            "/tools/analyze": {
                "post": {
                    "operationId": "analyze",
                    "summary": "Smart SEC filing analyzer (auto-routes to best method)",
                    "description": "Automatically picks Regex or RAG based on your question. For metrics (revenue, EPS) uses fast regex. For narrative (risks, guidance, comparisons) uses RAG semantic search. Just ask your question naturally.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "Your question about the company's SEC filing"},
                                        "company": {"type": "string", "description": "Company name or ticker (e.g., 'Apple', 'AAPL')"},
                                        "form_type": {"type": "string", "description": "Filing type (10-Q, 10-K, 8-K)", "default": "10-Q"}
                                    },
                                    "required": ["query", "company"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Analysis results with key_metrics (regex mode) or relevant_context (RAG mode)"}
                    }
                }
            }
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
