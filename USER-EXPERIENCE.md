# User Experience Design: SEC Filing Analyzer

## Who Is The User?

**Primary Persona: Financial Analyst at a Credit Fund**

- **Role:** Analyzes BDC (Business Development Company) portfolios
- **Companies tracked:** BCRED, ARCC, MAIN, ORCC, FSK, GBDC, etc.
- **Frequency:** Quarterly (when 10-Qs drop) + annual (10-K)
- **Time pressure:** First 48 hours after filing are critical for trading decisions

**Secondary Persona: Portfolio Manager**

- Needs summary reports, not raw data
- Asks "What changed?" and "Should I be worried?"
- Less time for deep dives, needs actionable insights

---

## Current Workflow (The Pain)

### Step 1: Monitor for New Filings
- Manually check EDGAR or set up email alerts
- Often miss filings, find out from colleagues
- **Pain:** No centralized monitoring, reactive not proactive

### Step 2: Navigate to Filing
- Go to SEC EDGAR → Search company → Find latest 10-Q
- Download or view in browser
- **Pain:** Clunky interface, multiple clicks, slow

### Step 3: Find the Investment Schedule
- Scroll through 100+ page document
- Ctrl+F "Schedule of Investments"
- Often buried in different locations per company
- **Pain:** Time-consuming, inconsistent document structure

### Step 4: Extract Data
- Manually copy tables to Excel
- Reformat columns, fix number formatting
- **Pain:** Error-prone, tedious, takes hours

### Step 5: Compare to Prior Quarter
- Open previous 10-Q side by side
- Manually match rows between quarters
- Calculate changes
- **Pain:** Most time-consuming step, easy to miss changes

### Step 6: Analyze Trends
- Look for PIK increases, fair value drops, new positions
- Cross-reference with news, other filings
- **Pain:** Requires domain expertise, easy to miss signals

### Step 7: Create Report
- Write up findings in Word/PowerPoint
- Share with PM and team
- **Pain:** Formatting, version control, repetitive work

**Total time per company per quarter: 4-8 hours**
**For 10 companies: 40-80 hours per quarter**

---

## Ideal Workflow (With Our Tool)

### Step 1: Get Notified (Automated)
```
📬 New Filing Alert
BCRED filed 10-Q for Q3 2025
→ [View Analysis] [Compare to Q2]
```
- Real-time alerts via email/Slack/chat
- One click to start analysis

### Step 2: Instant Summary (30 seconds)
```
User: "Summarize BCRED's Q3 10-Q"

AI: "BCRED's Q3 2025 10-Q shows:
• Total investments: $13.2B fair value (up 4% from Q2)
• Net investment income: $0.47/share (beat estimate of $0.45)
• NAV: $15.23/share (down 1.2% from Q2)
• New investments: $1.8B across 23 portfolio companies
• PIK income: 8.2% of total (up from 7.1% in Q2)

Key changes flagged:
⚠️ PIK increased 110bps — watch for credit stress
⚠️ 3 investments moved from Level 2 to Level 3
✅ No new non-accruals this quarter"
```

### Step 3: Deep Dive on Specific Questions (2 minutes each)
```
User: "Show me all investments where PIK increased this quarter"

AI: [Table]
| Company | Q2 PIK | Q3 PIK | Change | Fair Value |
|---------|--------|--------|--------|------------|
| ABC Corp | 2.0% | 4.5% | +250bps | $45M |
| XYZ LLC | 0% | 3.0% | +300bps | $28M |
| ... | ... | ... | ... | ... |

"5 investments showed PIK increases. Total exposure: $142M (1.1% of portfolio).
ABC Corp is the largest — recommend reviewing their Q3 financials."
```

### Step 4: Cross-Company Comparison (5 minutes)
```
User: "Compare PIK exposure across BCRED, ARCC, and MAIN"

AI: [Chart + Table]
| Company | Q3 PIK % | Q2 PIK % | Trend |
|---------|----------|----------|-------|
| BCRED | 8.2% | 7.1% | ↑ |
| ARCC | 5.4% | 5.2% | → |
| MAIN | 3.1% | 3.0% | → |

"BCRED has significantly higher PIK exposure (8.2%) vs peers (avg 4.3%).
This has increased for 3 consecutive quarters. ARCC and MAIN remain stable."
```

### Step 5: Generate Report (1 click)
```
User: "Generate Q3 BDC portfolio report"

AI: [Generates formatted PDF/Word]
- Executive summary
- Company-by-company analysis
- Risk flags
- Charts and tables
- Source citations (links to actual filings)
```

**Total time per company: 15-30 minutes**
**For 10 companies: 3-5 hours (vs 40-80 hours)**

---

## Key User Journeys

### Journey 1: New Filing Analysis
```
Trigger: New 10-Q/10-K filed
→ Alert sent to analyst
→ Analyst opens tool
→ "Summarize [company] latest filing"
→ AI provides summary with flags
→ Analyst asks follow-up questions
→ Analyst exports report
```

### Journey 2: Quarterly Comparison
```
Trigger: Analyst preparing quarterly review
→ "Compare [company] Q3 to Q2"
→ AI shows side-by-side with changes highlighted
→ "What are the biggest changes?"
→ AI surfaces material changes
→ Analyst drills into specific areas
```

### Journey 3: Thematic Research
```
Trigger: PM asks "What's our PIK exposure?"
→ "Show PIK trends across all tracked BDCs"
→ AI aggregates across companies
→ "Which companies have increasing PIK?"
→ AI identifies trends
→ Analyst generates risk report
```

### Journey 4: Due Diligence on New Company
```
Trigger: Evaluating new BDC investment
→ "Index all filings for [new company]"
→ AI fetches and indexes 3 years of filings
→ "What are the key risks?"
→ AI analyzes risk factors, trends
→ "Compare to [existing holding]"
→ AI provides comparative analysis
```

---

## Interface Options

### Option A: Chat Interface (MVP)
- Simple chat window (Dify provides this)
- Natural language queries
- Responses with tables, charts inline
- Export to PDF/Excel

**Pros:** Fast to build, flexible, low learning curve
**Cons:** No persistent dashboards, requires knowing what to ask

### Option B: Dashboard + Chat (v2)
- Pre-built dashboards for tracked companies
- Charts: NAV trends, PIK exposure, sector allocation
- Alerts panel for new filings and flags
- Chat for ad-hoc queries

**Pros:** Better for daily monitoring, visual trends
**Cons:** More development work, needs frontend

### Option C: Slack/Teams Bot (v2)
- Interact via existing tools
- "/sec summary BCRED" commands
- Alerts posted to channels
- Threads for follow-up questions

**Pros:** Zero new interface to learn, fits workflow
**Cons:** Limited formatting, no complex visualizations

**Recommendation:** Start with **Option A (Chat)**, add **Option C (Slack)** for alerts, evolve to **Option B (Dashboard)** based on user feedback.

---

## Pre-Built Analysis Templates

For one-click analysis, we'll offer templates:

### 1. Quarterly Summary
```
Inputs: Company, Quarter
Outputs:
- Key metrics (NAV, NII, dividend coverage)
- Investment activity (new, exits, changes)
- Fair value changes
- Risk flags
```

### 2. Investment Schedule Extract
```
Inputs: Company, Quarter
Outputs:
- Full investment table as Excel
- Sorted by fair value
- Includes all columns (rate, maturity, cost, FV)
```

### 3. Quarter-over-Quarter Comparison
```
Inputs: Company, Period 1, Period 2
Outputs:
- Side-by-side metrics
- New investments
- Exits
- Fair value changes by investment
- PIK changes
```

### 4. Peer Comparison
```
Inputs: List of companies, Metric(s)
Outputs:
- Comparative table
- Ranking
- Trend charts
```

### 5. Risk Factor Changes
```
Inputs: Company, Period 1, Period 2
Outputs:
- New risk factors added
- Removed risk factors
- Modified language (diff view)
```

### 6. PIK Analysis
```
Inputs: Company or portfolio
Outputs:
- PIK as % of total income
- Investments with PIK
- PIK trends over time
- Comparison to peers
```

---

## Sample Conversations

### Conversation 1: Basic Lookup
```
User: What's BCRED's CIK?

AI: Blue Owl Capital Corporation (BCRED/OBDC)
    CIK: 0001775097
    Latest filing: 10-Q filed 2025-11-14 (Q3 2025)
    Would you like me to analyze the latest filing?
```

### Conversation 2: Investment Deep Dive
```
User: Show me BCRED's largest investments

AI: Top 10 investments by fair value (Q3 2025):

| # | Company | Type | Rate | Fair Value | % NAV |
|---|---------|------|------|------------|-------|
| 1 | ABC Holdings | 1L Term Loan | S+550 | $234M | 1.8% |
| 2 | XYZ Corp | 1L Term Loan | S+600 | $198M | 1.5% |
| ... | ... | ... | ... | ... | ... |

Total top 10: $1.42B (10.7% of portfolio)

Would you like details on any of these investments?
```

### Conversation 3: Trend Analysis
```
User: Has BCRED's PIK exposure been increasing?

AI: Yes, BCRED's PIK exposure has increased for 4 consecutive quarters:

| Quarter | PIK % of Income | PIK $ Amount |
|---------|-----------------|--------------|
| Q4 2024 | 5.8% | $42M |
| Q1 2025 | 6.3% | $47M |
| Q2 2025 | 7.1% | $54M |
| Q3 2025 | 8.2% | $63M |

This is above the BDC peer average of 4.3%.

Investments with highest PIK:
1. ABC Corp: $12M PIK (4.5% rate)
2. DEF LLC: $8M PIK (3.0% rate)
...

⚠️ Increasing PIK can indicate credit stress — borrowers paying 
interest with more debt rather than cash. Recommend monitoring 
these positions.
```

### Conversation 4: Comparison
```
User: How does BCRED compare to ARCC on credit quality?

AI: Credit Quality Comparison (Q3 2025):

| Metric | BCRED | ARCC |
|--------|-------|------|
| Non-accruals (% of portfolio) | 1.2% | 0.8% |
| PIK income (% of total) | 8.2% | 5.4% |
| Level 3 assets (% of FV) | 89% | 82% |
| Weighted avg yield | 11.2% | 10.4% |
| First lien (%) | 78% | 85% |

Assessment:
- ARCC has better credit metrics overall
- BCRED has higher yield but more risk indicators
- BCRED's PIK trend is concerning
- Both have high Level 3 (typical for BDCs)

Sources:
- BCRED 10-Q Q3 2025 (filed 2025-11-14)
- ARCC 10-Q Q3 2025 (filed 2025-11-08)
```

---

## Success Metrics

### Time Savings
- **Baseline:** 4-8 hours per company per quarter
- **Target:** 30 minutes per company per quarter
- **Metric:** Track time from filing to completed analysis

### Accuracy
- **Baseline:** Manual extraction has ~2-5% error rate
- **Target:** <0.5% error rate on extracted data
- **Metric:** Spot-check AI extractions vs source documents

### Coverage
- **Metric:** % of analyst questions answerable without leaving tool
- **Target:** >90% of routine questions

### User Satisfaction
- **Metric:** Would you recommend this tool? (NPS)
- **Target:** NPS > 50

---

## Competitive Alternatives

| Tool | Strengths | Weaknesses | Price |
|------|-----------|------------|-------|
| **Bloomberg Terminal** | Comprehensive, trusted | Expensive, complex, not AI-native | $24K/year |
| **S&P Capital IQ** | Good data, some AI | Expensive, limited customization | $15K+/year |
| **AlphaSense** | AI search, good UI | Broad focus, not BDC-specific | $10K+/year |
| **Sentieo** | Good for docs | Being sunset (acquired) | N/A |
| **Our Tool** | BDC-focused, cheap, AI-native | New, unproven | ~$50/month |

**Our differentiators:**
1. Purpose-built for BDC analysis
2. 10-100x cheaper than alternatives
3. Natural language interface
4. Self-hostable / customizable
5. Integrates tools we've validated on our blog

---

## MVP Feature List

### Must Have (Week 1-2)
- [ ] Company search by name/ticker
- [ ] List filings for a company
- [ ] Fetch and index a filing
- [ ] Basic Q&A over indexed filings
- [ ] Chat interface (via Dify)

### Should Have (Week 3-4)
- [ ] Investment schedule extraction
- [ ] Quarter-over-quarter comparison
- [ ] Pre-built summary template
- [ ] Export to Excel

### Nice to Have (Future)
- [ ] Real-time filing alerts
- [ ] Multi-company portfolio view
- [ ] Slack/Teams integration
- [ ] Dashboard with charts
- [ ] PDF report generation

---

## Open UX Questions

1. **How technical can we be?** Do analysts want raw data or interpreted insights?
2. **Citation format?** Link to filing? Page number? Exact quote?
3. **Error handling?** What if we can't find data? Best guess or explicit "not found"?
4. **Confidence levels?** Should we show how confident we are in extractions?
5. **Customization?** Can analysts define their own metrics/templates?

---

*This document should be validated with actual financial analysts before building.*
