# Design Document: SEC Filing Analyzer

## Overview

This document details the technical design decisions for the SEC Filing Analyzer — an agentic RAG system for financial analysis of SEC filings.

---

## 1. Why Dify?

### Selected: Dify (Self-Hosted on Railway)

**Reasons:**

1. **LLMOps Built-In**
   - Production logging and monitoring
   - See exactly which queries fail and why
   - Track token usage and costs
   - A/B test different prompts

2. **Visual Workflow Builder**
   - Non-technical users can modify analysis flows
   - Easy to add new analysis templates
   - Debug agent reasoning visually

3. **Backend-as-a-Service**
   - Every workflow automatically exposes REST API
   - Frontend team consumes APIs without touching AI logic
   - Clean separation of concerns

4. **External Vector DB Support**
   - Connects to our existing Qdrant Cloud
   - No need to run another database

5. **Deployment Flexibility**
   - Docker Compose for Railway
   - Helm charts available if we move to K8s later
   - AWS Marketplace option for enterprise clients

### Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Custom FastAPI** | Full control, lightweight | No monitoring, manual everything | Too much DIY |
| **LangChain + LangSmith** | Popular, good tracing | LangSmith is paid, complex abstractions | Cost + complexity |
| **Flowise** | Similar to Dify, visual | Less mature, smaller community | Dify more production-ready |
| **CrewAI** | Great for multi-agent | No visual builder, no built-in monitoring | Overkill for this use case |

---

## 2. Document Parsing Strategy

SEC filings come in multiple formats:
- **HTML** — Most common, human-readable
- **XBRL** — Structured financial data, machine-readable
- **Plain text** — Older filings

### Parsing Pipeline

```
Filing URL
    │
    ▼
┌─────────────────┐
│  Format Check   │
│  (HTML/XBRL/TXT)│
└─────────────────┘
    │
    ├─── HTML ──────► HTML Parser ──► Clean Markdown
    │                     │
    │                     ▼
    │              Table Extractor ──► Structured Tables
    │
    ├─── XBRL ─────► XBRL Parser ──► Structured Facts
    │                (python-xbrl or edgartools)
    │
    └─── TXT ──────► Direct Chunking
    
    │
    ▼
┌─────────────────┐
│   Chunking      │
│ (section-aware) │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│   Embedding     │
│ (Azure OpenAI)  │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│    Qdrant       │
│    Storage      │
└─────────────────┘
```

### Section-Aware Chunking

SEC filings have predictable structure. We preserve this:

**10-K Sections:**
- Part I: Business, Risk Factors
- Part II: Financial Data, MD&A
- Part III: Directors, Executive Compensation
- Part IV: Exhibits, Financial Statements

**10-Q Sections:**
- Part I: Financial Statements, MD&A
- Part II: Other Information, Risk Factors

**Chunking Strategy:**
1. Split by section headers first
2. Then split large sections by paragraphs
3. Keep tables as single chunks (don't break mid-table)
4. Target chunk size: 1000-1500 tokens
5. Overlap: 100 tokens

### Investment Table Extraction

For BDC filings (BCRED, ARCC, etc.), the Schedule of Investments is critical.

**Identification:**
- Look for "Schedule of Investments" or "Consolidated Schedule of Investments"
- Usually in Part I, Item 1 of 10-Q
- Or Exhibit in 10-K

**Extraction Approach:**
1. Locate table via heading/caption
2. Parse HTML `<table>` structure
3. Map columns to schema:
   - Portfolio Company
   - Investment Type
   - Interest Rate (Cash + PIK)
   - Maturity Date
   - Principal/Shares
   - Cost
   - Fair Value
4. Store as structured JSON alongside text chunks

**Example Structured Output:**
```json
{
  "company": "ABC Holdings LLC",
  "investment_type": "Senior Secured First Lien Term Loan",
  "industry": "Software",
  "interest_rate": {
    "base": "SOFR",
    "spread": 5.50,
    "floor": 1.00,
    "pik": 0.00
  },
  "maturity": "2028-03-15",
  "principal": 15000000,
  "cost": 14850000,
  "fair_value": 14700000,
  "percent_of_net_assets": 1.2
}
```

---

## 3. Vector Store Schema (Qdrant)

### Collection: `sec_filings`

**Payload Schema:**
```json
{
  "cik": "0001775097",
  "company_name": "Blue Owl Capital Corporation",
  "ticker": "OBDC",
  "form_type": "10-Q",
  "filing_date": "2025-11-14",
  "period_of_report": "2025-09-30",
  "accession_number": "0001775097-25-000123",
  "section": "Schedule of Investments",
  "chunk_index": 42,
  "content_type": "table",
  "url": "https://www.sec.gov/Archives/edgar/data/..."
}
```

**Indexes:**
- Vector index on embeddings (HNSW)
- Filter indexes on: `cik`, `form_type`, `filing_date`, `section`

### Collection: `investment_tables`

Separate collection for structured investment data:

```json
{
  "cik": "0001775097",
  "filing_date": "2025-09-30",
  "portfolio_company": "ABC Holdings LLC",
  "investment_type": "Senior Secured First Lien",
  "fair_value": 14700000,
  "pik_rate": 0.00,
  "industry": "Software"
}
```

Enables structured queries like:
- "Sum of all PIK investments for BCRED Q3 2025"
- "Filter investments where fair_value decreased > 10%"

---

## 4. Dify Workflow Design

### Workflow 1: Basic Filing Q&A

```
[User Query]
     │
     ▼
[Intent Classification]
     │
     ├── Company Lookup ──► search_company tool
     │
     ├── Filing List ──► get_filings tool
     │
     ├── Document Q&A ──► RAG retrieval + LLM
     │
     └── Comparison ──► compare_periods tool
     
     │
     ▼
[Response Generation]
     │
     ▼
[Citation Attachment]
     │
     ▼
[User Response]
```

### Workflow 2: Investment Analysis (Pre-Built)

```
[Company Name] + [Period]
     │
     ▼
[Resolve CIK]
     │
     ▼
[Fetch 10-Q for Period]
     │
     ▼
[Extract Schedule of Investments]
     │
     ▼
[Structured Analysis]
  ├── Top 10 by Fair Value
  ├── PIK Summary
  ├── Industry Breakdown
  └── QoQ Changes (if prior period indexed)
     │
     ▼
[Formatted Report]
```

### Agent Mode: ReAct

For open-ended queries, use ReAct agent pattern:
1. **Thought:** What do I need to answer this?
2. **Action:** Call appropriate tool
3. **Observation:** Process tool result
4. **Repeat** until sufficient information
5. **Answer:** Synthesize final response

---

## 5. API Design

### Public Endpoints (via Dify)

**Chat Completion:**
```
POST /v1/chat-messages
{
  "query": "What are BCRED's top 5 investments by fair value?",
  "user": "user-123",
  "conversation_id": "conv-456"
}
```

**Workflow Execution:**
```
POST /v1/workflows/run
{
  "workflow_id": "investment-analysis",
  "inputs": {
    "company": "BCRED",
    "period": "Q3 2025"
  }
}
```

### Internal Tool APIs

**search_company:**
```
POST /tools/search_company
{
  "query": "BCRED"
}

Response:
{
  "cik": "0001775097",
  "name": "Blue Owl Capital Corporation", 
  "ticker": "OBDC",
  "sic": "6726",
  "sic_description": "Other Investment Offices",
  "recent_filings": [...]
}
```

**get_filings:**
```
POST /tools/get_filings
{
  "cik": "0001775097",
  "form_types": ["10-K", "10-Q"],
  "start_date": "2024-01-01",
  "end_date": "2025-12-31"
}
```

**fetch_filing:**
```
POST /tools/fetch_filing
{
  "cik": "0001775097",
  "accession_number": "0001775097-25-000123",
  "index": true
}
```

---

## 6. Error Handling

### SEC API Errors

| Error | Handling |
|-------|----------|
| 404 Not Found | Company/filing doesn't exist — return helpful message |
| 429 Rate Limited | Exponential backoff, queue requests |
| 500 Server Error | Retry 3x, then fail gracefully |
| Timeout | 30s timeout, retry once |

### Parsing Errors

| Error | Handling |
|-------|----------|
| Malformed HTML | Fall back to text extraction |
| Missing tables | Note in response, continue with available data |
| XBRL parse failure | Fall back to HTML version |

### LLM Errors

| Error | Handling |
|-------|----------|
| Context too long | Summarize chunks, reduce context |
| Hallucination detected | Cross-reference with source, flag uncertainty |
| Rate limit | Queue, exponential backoff |

---

## 7. Cost Estimation

### Per-Query Costs (Estimated)

| Component | Cost |
|-----------|------|
| Embedding (1500 tokens) | ~$0.0001 |
| GPT-4 input (8K context) | ~$0.024 |
| GPT-4 output (500 tokens) | ~$0.015 |
| **Total per query** | **~$0.04** |

### Monthly Projections

| Usage Level | Queries/Month | LLM Cost | Railway | Total |
|-------------|---------------|----------|---------|-------|
| Light | 500 | $20 | $10 | $30 |
| Medium | 2,000 | $80 | $15 | $95 |
| Heavy | 10,000 | $400 | $25 | $425 |

### Cost Optimization Opportunities

1. **Caching:** Cache common company lookups
2. **Smaller model for routing:** GPT-3.5 for intent classification
3. **Chunk deduplication:** Don't re-index unchanged filings
4. **Batch embedding:** Embed multiple chunks per API call

---

## 8. Security Considerations

### Data Handling
- All SEC data is public — no PII concerns
- User queries may contain sensitive info — don't log full queries in production
- API keys stored in Railway secrets, not in code

### Access Control
- Dify provides API key authentication
- Rate limiting per API key
- Optional: Add user authentication layer

### Compliance
- SEC API requires User-Agent with contact email — we comply
- No redistribution of SEC data (we link to source)
- GDPR: No personal data collected (unless auth added)

---

## 9. Testing Strategy

### Unit Tests
- SEC API response parsing
- HTML table extraction
- XBRL fact extraction
- Chunking logic

### Integration Tests
- End-to-end filing fetch and index
- RAG retrieval accuracy
- Tool execution in Dify

### Validation Tests
- Compare extracted values against manual review
- Sample 10 filings, verify all investment table values
- Test edge cases (amended filings, foreign filers)

---

## 10. Rollout Plan

### Week 1: Foundation
- [ ] Deploy Dify on Railway
- [ ] Configure Qdrant connection
- [ ] Implement search_company tool
- [ ] Implement get_filings tool

### Week 2: Parsing
- [ ] HTML parser for 10-K/10-Q
- [ ] Table extraction logic
- [ ] Chunking and embedding pipeline
- [ ] fetch_filing tool

### Week 3: RAG
- [ ] Basic Q&A workflow
- [ ] query_filings tool
- [ ] Citation generation
- [ ] Testing with sample companies

### Week 4: Advanced Features
- [ ] Investment table structured extraction
- [ ] compare_periods tool
- [ ] Pre-built analysis templates
- [ ] Documentation and demo

---

## Open Questions

1. **Multi-tenant?** Do we need separate data per user/org?
2. **Historical depth?** How far back should we index (5 years? 10 years?)?
3. **Real-time alerts?** RSS feed monitoring for new filings?
4. **Export formats?** Excel, PDF, or just chat responses?

---

## References

- [SEC EDGAR API Documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [Dify Documentation](https://docs.dify.ai)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [edgartools Python Library](https://github.com/dgunning/edgartools)
- [XBRL US GAAP Taxonomy](https://xbrl.us/home/filers/sec-reporting/)
