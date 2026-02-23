# SEC Filing Analyzer

An agentic RAG system for analyzing SEC filings — built for financial analysts who need to track investment portfolios, compare quarterly changes, and extract insights from 10-K/10-Q filings.

## 🎯 Problem Statement

Financial analysts need to:
- Look up companies by name or ticker (e.g., "BCRED" → Blue Owl Capital Corporation)
- Fetch and parse SEC filings (10-K, 10-Q, 8-K)
- Extract specific data (investment tables, PIK listings, fair value schedules)
- Compare changes across quarters/years
- Ask natural language questions about filings

Currently this requires manual EDGAR navigation, copy-pasting into spreadsheets, and tedious comparison work.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                    (Dify Chat / API Endpoint)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Dify Orchestration                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Agent     │  │  Workflow   │  │       LLMOps            │ │
│  │  (ReAct)    │  │   Canvas    │  │  (Logs, Monitoring)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  SEC EDGAR   │ │   Document   │ │    RAG       │
        │    Tools     │ │   Parser     │ │  Retrieval   │
        └──────────────┘ └──────────────┘ └──────────────┘
                │               │               │
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  SEC EDGAR   │ │  HTML/XBRL   │ │   Qdrant     │
        │     API      │ │   Content    │ │    Cloud     │
        │    (Free)    │ │              │ │              │
        └──────────────┘ └──────────────┘ └──────────────┘
```

## 📋 Features

### Phase 1: Core Functionality
- [ ] Company search (name/ticker → CIK lookup)
- [ ] Filing list retrieval (10-K, 10-Q, 8-K by date range)
- [ ] Document fetching and parsing
- [ ] Basic RAG Q&A over filings
- [ ] Dify deployment on Railway

### Phase 2: Advanced Analysis
- [ ] Investment table extraction (Schedule of Investments)
- [ ] Quarter-over-quarter comparison
- [ ] PIK (Payment in Kind) tracking
- [ ] Fair value hierarchy analysis (Level 1/2/3)
- [ ] Pre-built analysis templates

### Phase 3: Production Features
- [ ] Multi-company comparison
- [ ] Automated alerts on new filings
- [ ] Export to Excel/PDF
- [ ] User authentication
- [ ] Usage analytics

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Orchestration** | Dify | Visual workflows, agent logic, LLMOps |
| **Vector Store** | Qdrant Cloud | Document embeddings, semantic search |
| **LLM** | Azure OpenAI (GPT-4) | Analysis, Q&A, extraction |
| **Embeddings** | Azure OpenAI | text-embedding-ada-002 |
| **Deployment** | Railway | Container hosting |
| **Data Source** | SEC EDGAR API | Free, official SEC data |

## 📡 SEC EDGAR API Reference

The SEC provides free, unauthenticated access to all filings.

### Key Endpoints

**Company Search (by name):**
```
https://www.sec.gov/cgi-bin/browse-edgar?company={name}&type=10-K&output=atom
```

**Company Filings (by CIK):**
```
https://data.sec.gov/submissions/CIK{cik_padded}.json
```
Returns: All filings, company info, SIC code, addresses

**Filing Documents:**
```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number_no_dashes}/{filename}
```

**Full-Text Search:**
```
https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom&startdt={start}&enddt={end}
```

### Rate Limits
- 10 requests per second
- Must include User-Agent header with contact email
- Example: `User-Agent: SEC-Filing-Analyzer contact@example.com`

### Filing Types We Care About

| Form | Description | Frequency |
|------|-------------|-----------|
| 10-K | Annual report | Yearly |
| 10-Q | Quarterly report | Q1, Q2, Q3 |
| 8-K | Current report (material events) | As needed |
| 13F | Institutional holdings | Quarterly |
| N-CSR | Fund shareholder reports | Semi-annual |

## 🛠️ Dify Custom Tools

We'll create these custom tools in Dify:

### 1. `search_company`
**Input:** Company name or ticker
**Output:** CIK, full name, SIC code, recent filings
**Implementation:** SEC EDGAR company search API

### 2. `get_filings`
**Input:** CIK, form types, date range
**Output:** List of filings with accession numbers, dates, descriptions
**Implementation:** SEC submissions endpoint

### 3. `fetch_filing`
**Input:** CIK, accession number
**Output:** Parsed filing content (indexed into Qdrant)
**Implementation:** Fetch HTML/XBRL, parse, chunk, embed, store

### 4. `query_filings`
**Input:** Natural language question, optional company/date filters
**Output:** Answer with citations to specific filings/pages
**Implementation:** RAG retrieval from Qdrant + LLM synthesis

### 5. `compare_periods`
**Input:** Company, metric type, period 1, period 2
**Output:** Structured comparison with changes highlighted
**Implementation:** Retrieve both periods, structured extraction, diff

## 📊 Pre-Built Analysis Templates

### Investment Table Analysis (BDCs)
```
Extract the Schedule of Investments from {company}'s latest 10-Q.
For each investment, identify:
- Portfolio company name
- Investment type (Senior Secured, Subordinated, Equity, etc.)
- Interest rate and PIK component
- Fair value
- % of net assets

Compare to previous quarter and highlight:
- New investments
- Exits
- Fair value changes > 10%
- PIK rate changes
```

### Fair Value Hierarchy
```
Extract Level 1, 2, and 3 asset classifications.
Calculate % in each level.
Compare to prior period.
Flag any transfers between levels.
```

### Concentration Risk
```
Identify top 10 investments by fair value.
Calculate concentration in top 10.
Compare to prior quarter.
Flag any position > 5% of portfolio.
```

## 🚀 Deployment

### Railway Setup

```bash
# Clone and deploy
git clone https://github.com/yourusername/sec-filing-analyzer.git
cd sec-filing-analyzer

# Deploy Dify via Docker Compose on Railway
# (Railway template coming soon)
```

### Environment Variables

```env
# LLM
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_ENDPOINT=xxx
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Vector Store
QDRANT_URL=xxx
QDRANT_API_KEY=xxx

# SEC API (no key needed, just identity)
SEC_USER_AGENT=SEC-Filing-Analyzer contact@yourdomain.com
```

## 📁 Project Structure

```
sec-filing-analyzer/
├── README.md                 # This file
├── DESIGN.md                 # Detailed design decisions
├── docker-compose.yml        # Dify + dependencies
├── railway.toml              # Railway deployment config
├── dify/
│   ├── tools/                # Custom tool definitions
│   │   ├── search_company.py
│   │   ├── get_filings.py
│   │   ├── fetch_filing.py
│   │   ├── query_filings.py
│   │   └── compare_periods.py
│   └── workflows/            # Exported Dify workflows
│       ├── basic_qa.json
│       └── investment_analysis.json
├── parsers/
│   ├── html_parser.py        # SEC HTML filing parser
│   ├── xbrl_parser.py        # XBRL structured data
│   └── table_extractor.py    # Investment table extraction
├── tests/
│   ├── test_sec_api.py
│   └── test_parsers.py
└── scripts/
    ├── index_company.py      # Batch index a company's filings
    └── backfill.py           # Historical data loading
```

## 🧪 Example Queries

Once deployed, users can ask:

1. **Basic lookup:**
   > "What is BCRED's CIK number and when was their last 10-K filed?"

2. **Investment analysis:**
   > "Show me the top 10 investments in Blue Owl's latest 10-Q by fair value"

3. **Comparison:**
   > "How did BCRED's PIK percentage change from Q2 to Q3 2025?"

4. **Risk analysis:**
   > "What percentage of ARCC's portfolio is in Level 3 assets?"

5. **Cross-company:**
   > "Compare the industry concentration between BCRED and ARCC"

## 📈 Success Metrics

- Query response time < 10 seconds
- Accurate citation to source filings
- Correct extraction of financial figures (validated against source)
- Support for 50+ simultaneous users

## 🔜 Future Enhancements

- Real-time filing alerts (new 8-K detection)
- Integration with financial data APIs (for market data context)
- Custom trained models for financial table extraction
- Mobile app / Slack bot interface
- GCP deployment option (see: Agent Ecosystem project)

---

## License

MIT

## Contributing

PRs welcome! See CONTRIBUTING.md for guidelines.
