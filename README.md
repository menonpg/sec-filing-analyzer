# SEC Filing Analyzer

A production-ready SEC EDGAR analysis API with **dual-mode architecture** — fast regex extraction for metrics, semantic RAG search for narrative content. Includes a smart router that auto-picks the best approach.

**Live Demo:** [https://udify.app/chatbot/OCkEUGuuRXM3RNBt](https://udify.app/chatbot/OCkEUGuuRXM3RNBt)

## 🎯 What It Does

Ask natural language questions about any company's SEC filings:

```
"What was Apple's revenue in their latest 10-Q?"
→ Regex mode: $143.76B (extracted in <1s)

"What are the risk factors in Ingram Micro's filing?"
→ RAG mode: Semantic search across indexed content

"Compare Apple's last two quarters"
→ Fetches both filings, extracts metrics, shows changes
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  POST /tools/analyze   ← Smart Router (use this!)          │
│  { "query": "...", "company": "Apple" }                     │
└─────────────────────────────────────────────────────────────┘
                          │
                    classify_query()
                          │
         ┌────────────────┴────────────────┐
         │                                 │
    METRIC keywords               NARRATIVE keywords
    revenue, eps, margin          risk, compare, guidance
         │                                 │
         ▼                                 ▼
   fetchFiling                      is_indexed()?
   (summary_only=true)              │         │
         │                         No        Yes
         │                          │         │
         │                    index_filing    │
         │                          │         │
         │                          └────┬────┘
         │                               │
         │                        semantic_search
         │                     (scoped by accession)
         ▼                               ▼
   { key_metrics: {...} }      { relevant_context: [...] }
```

### Why Dual Mode?

| Mode | Best For | Speed | Needs Indexing? |
|------|----------|-------|-----------------|
| **Regex** | Structured data (revenue, EPS, margins) | Fast (<1s) | No |
| **RAG** | Narrative content (risks, MD&A, guidance) | 2-5s | Yes (auto) |

The smart router analyzes your query and picks the right mode automatically.

## 🔧 API Endpoints

### Smart Router (Recommended)

```bash
POST /tools/analyze
{
  "query": "What was the revenue?",
  "company": "Apple",
  "form_type": "10-Q"  # optional, defaults to 10-Q
}
```

Returns either `key_metrics` (regex) or `relevant_context` (RAG) based on query type.

### Individual Tools

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tools/search_company` | POST | Find company by name/ticker → CIK |
| `/tools/get_filings` | POST | List SEC filings for a company |
| `/tools/fetch_filing` | POST | Parse filing, optionally `summary_only=true` |
| `/tools/index_filing` | POST | Index filing into Qdrant for RAG |
| `/tools/semantic_search` | POST | Search indexed filings by topic |
| `/tools/compare_filings` | POST | Side-by-side comparison of two filings |
| `/tools/indexed_filings` | GET | List all indexed filings |
| `/tools/vector_stats` | GET | Qdrant collection stats |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/openapi-tools.json` | GET | Dify-compatible schema |

### Example: Quick Metrics (Regex Mode)

```bash
curl -X POST https://sec-filing-analyzer-production.up.railway.app/tools/fetch_filing \
  -H "Content-Type: application/json" \
  -d '{
    "cik": "320193",
    "accession_number": "0000320193-26-000006",
    "summary_only": true
  }'
```

Response:
```json
{
  "key_metrics": {
    "revenue": "Total net sales 143,756",
    "net_income": "net income 237",
    "gross_margin": "Gross margin 69",
    "segments": {
      "iPhone": "iPhone 85,268",
      "Services": "Services 30,013"
    },
    "period": "December 27, 2025"
  }
}
```

### Example: Semantic Search (RAG Mode)

```bash
# First, index the filing
curl -X POST .../tools/index_filing \
  -d '{"cik": "320193", "accession_number": "0000320193-26-000006"}'

# Then search within it
curl -X POST .../tools/semantic_search \
  -d '{
    "query": "supply chain risks",
    "cik": "320193",
    "accession_number": "0000320193-26-000006"
  }'
```

## 📊 RAG: How Qdrant Indexing Works

### Collection Structure

```
Collection: sec_edgar_filings
│
├── Apple Q1'26 (accession: 320193-26-000006)
│   ├── chunk_0: "Total net sales were $143.7 billion..."
│   ├── chunk_1: "iPhone revenue increased 23%..."
│   └── chunk_n: ...
│
├── Apple Q4'25 (accession: 320193-25-000089)
│   └── [chunks...]
│
└── Ingram Micro Q3'25 (accession: 1628280-25-047537)
    └── [chunks...]
```

### Scoping: Preventing Mixed Results

Each search is **scoped by accession_number** to prevent mixing content from different filings:

```python
# BAD: Searches ALL Apple filings (mixed quarters)
search(query="risks", cik="320193")

# GOOD: Searches ONLY Q1'26 filing
search(query="risks", cik="320193", accession_number="320193-26-000006")
```

The smart router automatically scopes to the specific filing being analyzed.

### Deduplication

Before indexing, we check if the filing is already in Qdrant:

```python
if not store.is_indexed(cik, accession_number):
    await store.index_filing(...)  # Index it
else:
    pass  # Skip, already indexed
```

### Chunking Strategy

- **Chunk size:** 1,500 characters
- **Overlap:** 200 characters
- Breaks at sentence boundaries when possible
- Each chunk stores: `cik`, `accession_number`, `company_name`, `form_type`, `filing_date`, `section`, `text`

## 🚀 Deployment

### Railway (Recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/...)

**Environment Variables:**

```env
# Qdrant Cloud
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=your-key

# Azure OpenAI Embeddings
AZURE_EMBEDDINGS_ENDPOINT=https://xxx.cognitiveservices.azure.com
AZURE_EMBEDDINGS_KEY=your-key
AZURE_EMBEDDINGS_DEPLOYMENT=text-embedding-3-large
```

### Local Development

```bash
git clone https://github.com/menonpg/sec-filing-analyzer.git
cd sec-filing-analyzer
pip install -r requirements.txt
cp .env.example .env  # Add your keys
uvicorn tools_api:app --reload
```

### Docker

```bash
docker build -t sec-filing-analyzer .
docker run -p 8000:8000 --env-file .env sec-filing-analyzer
```

## 🔌 Dify Integration

Import tools into Dify from:
```
https://sec-filing-analyzer-production.up.railway.app/openapi-tools.json
```

### Recommended Agent Instruction

```
Use the analyze tool for all SEC filing questions.
Just pass the query and company name - it auto-picks the best method.

For comparisons, call analyze twice (once per filing) or use compare_filings.
```

### Embed Widget

```html
<iframe 
  src="https://udify.app/chatbot/OCkEUGuuRXM3RNBt" 
  style="width: 100%; height: 700px" 
  frameborder="0">
</iframe>
```

## ✅ Verified Tests

### Apple (Q1 FY2026)
- Filed: January 30, 2026
- Revenue: $143.76B (+16% YoY)
- iPhone: $85.27B (+23%)
- Services: $30.01B (+14%)

### Ingram Micro (Q3 2025 vs Q2 2025)
- Revenue: $11.73B → $11.95B (-1.8%)
- Net Income: $0.30B → $0.79B (+163%)

## 📁 Project Structure

```
sec-filing-analyzer/
├── tools_api.py              # FastAPI endpoints + smart router
├── dify/
│   └── tools/
│       ├── search_company.py # Company lookup
│       ├── get_filings.py    # Filing list
│       ├── fetch_filing.py   # Parse + regex extraction
│       └── vector_store.py   # Qdrant RAG (index, search, compare)
├── parsers/
│   └── ...                   # HTML/XBRL parsing
├── requirements.txt
├── Dockerfile
├── railway.toml
└── .env.example
```

## 🔜 Future Enhancements

- [ ] 8-K real-time alerts (new filing detection)
- [ ] Self-hosted Dify on home server
- [ ] GCP Agent Ecosystem deployment
- [ ] More filing types (proxy statements, 13F)
- [ ] Excel export

## 📄 License

MIT

## 🙏 Credits

- [SEC EDGAR](https://www.sec.gov/edgar) — Free public API
- [Dify](https://dify.ai) — LLM orchestration
- [Qdrant](https://qdrant.tech) — Vector database
- [The Menon Lab](https://blog.themenonlab.com) — Blog & research
