"""
SEC Filing Fetch & Parse Tool

Downloads SEC filings, parses HTML content, and extracts key sections.
Prepares content for indexing into vector store.
"""

import httpx
import json
import re
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from dataclasses import dataclass


SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
USER_AGENT = "SEC-Filing-Analyzer contact@themenonlab.com"


@dataclass
class FilingSection:
    title: str
    content: str
    section_type: str  # 'text', 'table', 'header'
    start_index: int


async def fetch_filing(
    cik: str,
    accession_number: str,
    primary_document: Optional[str] = None,
    summary_only: bool = False
) -> dict:
    """
    Fetch and parse an SEC filing.
    
    Args:
        cik: Central Index Key
        accession_number: Filing accession number (e.g., '0001775097-24-000123')
        primary_document: Primary document filename (optional, will be detected)
        
    Returns:
        dict with parsed filing content, sections, tables
    """
    # Normalize inputs
    cik_clean = cik.replace("CIK", "").replace("cik", "").strip().lstrip("0")
    accession_nodash = accession_number.replace("-", "")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # If no primary document specified, get filing index
        if not primary_document:
            index_url = f"{SEC_ARCHIVES}/{cik_clean}/{accession_nodash}/index.json"
            try:
                index_response = await client.get(
                    index_url,
                    headers={"User-Agent": USER_AGENT}
                )
                index_response.raise_for_status()
                index_data = index_response.json()
                
                # Find primary document (usually the .htm file)
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith(".htm") and not name.startswith("R"):
                        primary_document = name
                        break
            except Exception as e:
                return {"error": f"Could not find primary document: {e}"}
        
        if not primary_document:
            return {"error": "No primary document found in filing"}
        
        # Fetch the actual filing
        filing_url = f"{SEC_ARCHIVES}/{cik_clean}/{accession_nodash}/{primary_document}"
        
        response = await client.get(
            filing_url,
            headers={"User-Agent": USER_AGENT}
        )
        
        if response.status_code == 404:
            return {"error": f"Filing not found: {filing_url}"}
        
        response.raise_for_status()
        html_content = response.text
        
        # Parse the filing
        parsed = parse_filing_html(html_content)
        
        # If summary_only, extract key metrics and return compact response
        if summary_only:
            key_metrics = extract_key_metrics(parsed.get("full_text", ""))
            return {
                "cik": cik_clean,
                "accession_number": accession_number,
                "url": filing_url,
                "title": parsed.get("title"),
                "key_metrics": key_metrics,
                "sections_found": [s["name"] for s in parsed.get("sections", [])],
                "table_count": len(parsed.get("tables", [])),
            }
        
        return {
            "cik": cik_clean,
            "accession_number": accession_number,
            "primary_document": primary_document,
            "url": filing_url,
            "title": parsed.get("title"),
            "sections": parsed.get("sections"),
            "tables": parsed.get("tables"),
            "full_text_length": len(parsed.get("full_text", "")),
            "full_text": parsed.get("full_text")[:50000],  # Truncate for API response
            "metadata": {
                "section_count": len(parsed.get("sections", [])),
                "table_count": len(parsed.get("tables", [])),
            }
        }


def parse_filing_html(html_content: str) -> dict:
    """
    Parse SEC filing HTML into structured content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and other non-content elements
    for element in soup(['script', 'style', 'meta', 'link', 'noscript']):
        element.decompose()
    
    # Get document title
    title = ""
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # Extract sections
    sections = extract_sections(soup)
    
    # Extract tables
    tables = extract_tables(soup)
    
    # Get full text
    full_text = soup.get_text(separator='\n', strip=True)
    # Clean up excessive whitespace
    full_text = re.sub(r'\n\s*\n', '\n\n', full_text)
    
    return {
        "title": title,
        "sections": sections,
        "tables": tables,
        "full_text": full_text
    }


def extract_sections(soup: BeautifulSoup) -> List[dict]:
    """
    Extract document sections based on SEC filing structure.
    """
    sections = []
    
    # Common SEC section patterns
    section_patterns = [
        (r'PART\s+I\b', 'Part I'),
        (r'PART\s+II\b', 'Part II'),
        (r'PART\s+III\b', 'Part III'),
        (r'PART\s+IV\b', 'Part IV'),
        (r'ITEM\s+1[.\s]', 'Item 1'),
        (r'ITEM\s+1A[.\s]', 'Item 1A - Risk Factors'),
        (r'ITEM\s+2[.\s]', 'Item 2'),
        (r'ITEM\s+3[.\s]', 'Item 3'),
        (r'ITEM\s+7[.\s]', 'Item 7 - MD&A'),
        (r'ITEM\s+8[.\s]', 'Item 8 - Financial Statements'),
        (r'SCHEDULE\s+OF\s+INVESTMENTS', 'Schedule of Investments'),
        (r'CONSOLIDATED\s+SCHEDULE\s+OF\s+INVESTMENTS', 'Consolidated Schedule of Investments'),
        (r'NOTES\s+TO\s+(CONSOLIDATED\s+)?FINANCIAL\s+STATEMENTS', 'Notes to Financial Statements'),
        (r'MANAGEMENT.S\s+DISCUSSION', 'MD&A'),
        (r'RISK\s+FACTORS', 'Risk Factors'),
    ]
    
    text = soup.get_text()
    
    for pattern, section_name in section_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        for match in matches:
            sections.append({
                "name": section_name,
                "start_position": match.start(),
                "matched_text": match.group()
            })
    
    # Sort by position
    sections.sort(key=lambda x: x["start_position"])
    
    # Remove duplicates (keep first occurrence)
    seen_names = set()
    unique_sections = []
    for section in sections:
        if section["name"] not in seen_names:
            seen_names.add(section["name"])
            unique_sections.append(section)
    
    return unique_sections


def extract_tables(soup: BeautifulSoup) -> List[dict]:
    """
    Extract and parse HTML tables from filing.
    """
    tables = []
    
    for idx, table in enumerate(soup.find_all('table')):
        # Get table context (preceding text for caption)
        caption = ""
        prev = table.find_previous_sibling()
        if prev:
            prev_text = prev.get_text(strip=True)
            if len(prev_text) < 200:  # Likely a caption
                caption = prev_text
        
        # Check for actual caption element
        caption_elem = table.find('caption')
        if caption_elem:
            caption = caption_elem.get_text(strip=True)
        
        # Parse rows
        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cell_text = td.get_text(strip=True)
                cells.append(cell_text)
            if cells and not all(c == '' for c in cells):
                rows.append(cells)
        
        if rows:  # Only include non-empty tables
            # Check if this might be the Schedule of Investments
            is_investment_schedule = False
            caption_lower = caption.lower()
            if 'schedule of investments' in caption_lower or 'portfolio' in caption_lower:
                is_investment_schedule = True
            
            # Check headers for investment-related columns
            if rows and len(rows) > 0:
                header_text = ' '.join(str(c) for c in rows[0]).lower()
                if any(term in header_text for term in ['fair value', 'cost', 'principal', 'maturity']):
                    is_investment_schedule = True
            
            tables.append({
                "index": idx,
                "caption": caption,
                "row_count": len(rows),
                "column_count": max(len(row) for row in rows) if rows else 0,
                "is_investment_schedule": is_investment_schedule,
                "headers": rows[0] if rows else [],
                "sample_rows": rows[1:6] if len(rows) > 1 else [],  # First 5 data rows
            })
    
    return tables


def extract_key_metrics(full_text: str) -> dict:
    """
    Extract key financial metrics from filing text using regex patterns.
    Returns a compact summary suitable for LLM comparison.
    """
    metrics = {}
    text_lower = full_text.lower()
    
    # Revenue patterns
    revenue_patterns = [
        r'(?:total\s+)?(?:net\s+)?(?:sales|revenue)[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million|B|M)?',
        r'(?:net\s+)?sales\s+(?:were|was|of)\s+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?',
    ]
    for pattern in revenue_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            metrics['revenue'] = match.group(0)[:100]
            break
    
    # Net income
    income_patterns = [
        r'net\s+income[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?',
        r'net\s+income\s+(?:was|were|of)\s+\$?([\d,]+(?:\.\d+)?)',
    ]
    for pattern in income_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            metrics['net_income'] = match.group(0)[:100]
            break
    
    # EPS
    eps_patterns = [
        r'(?:diluted\s+)?(?:earnings|EPS)\s+per\s+share[:\s]+\$?([\d.]+)',
        r'diluted\s+EPS[:\s]+\$?([\d.]+)',
    ]
    for pattern in eps_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            metrics['eps'] = match.group(0)[:80]
            break
    
    # Gross margin
    margin_match = re.search(r'gross\s+margin[:\s]+([\d.]+)\s*%?', full_text, re.IGNORECASE)
    if margin_match:
        metrics['gross_margin'] = margin_match.group(0)[:60]
    
    # Operating cash flow
    cash_flow_match = re.search(r'operating\s+cash\s+flow[:\s]+\$?([\d,]+(?:\.\d+)?)', full_text, re.IGNORECASE)
    if cash_flow_match:
        metrics['operating_cash_flow'] = cash_flow_match.group(0)[:80]
    
    # Segment data - look for product lines
    segments = {}
    segment_patterns = [
        (r'iPhone[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?', 'iPhone'),
        (r'Mac[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?', 'Mac'),
        (r'iPad[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?', 'iPad'),
        (r'Services[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?', 'Services'),
        (r'Wearables[,\s]+Home[:\s]+\$?([\d,]+(?:\.\d+)?)', 'Wearables'),
    ]
    for pattern, segment_name in segment_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            segments[segment_name] = match.group(0)[:60]
    
    if segments:
        metrics['segments'] = segments
    
    # Share repurchases
    buyback_match = re.search(r'(?:repurchased|buyback)[:\s]+\$?([\d,]+(?:\.\d+)?)\s*(?:billion|million)?', full_text, re.IGNORECASE)
    if buyback_match:
        metrics['share_repurchases'] = buyback_match.group(0)[:80]
    
    # Quarter/period
    period_match = re.search(r'(?:quarter|period)\s+ended\s+(\w+\s+\d+,?\s+\d{4})', full_text, re.IGNORECASE)
    if period_match:
        metrics['period'] = period_match.group(1)
    
    return metrics


def find_investment_schedule(tables: List[dict]) -> Optional[dict]:
    """
    Find the Schedule of Investments table from parsed tables.
    """
    for table in tables:
        if table.get("is_investment_schedule"):
            return table
    return None


# Dify tool schema
TOOL_SCHEMA = {
    "name": "fetch_filing",
    "description": "Fetch and parse an SEC filing document. Downloads the HTML filing, extracts sections (Item 1, Item 2, MD&A, Risk Factors, Schedule of Investments, etc.), and identifies tables. Use this after get_filings to retrieve the actual document content.",
    "parameters": {
        "type": "object",
        "properties": {
            "cik": {
                "type": "string",
                "description": "SEC Central Index Key for the company"
            },
            "accession_number": {
                "type": "string",
                "description": "Filing accession number (e.g., '0001775097-24-000123')"
            },
            "primary_document": {
                "type": "string",
                "description": "Primary document filename (optional, will be auto-detected)"
            }
        },
        "required": ["cik", "accession_number"]
    }
}


# CLI for testing
if __name__ == "__main__":
    import asyncio
    import sys
    
    async def main():
        # Default: Blue Owl recent 10-Q
        cik = sys.argv[1] if len(sys.argv) > 1 else "1775097"
        accession = sys.argv[2] if len(sys.argv) > 2 else "0001775097-24-000089"
        
        print(f"Fetching filing: CIK={cik}, Accession={accession}\n")
        
        result = await fetch_filing(cik, accession)
        
        # Print summary (not full text)
        summary = {k: v for k, v in result.items() if k != 'full_text'}
        print(json.dumps(summary, indent=2))
        
        if result.get("tables"):
            print(f"\n--- Found {len(result['tables'])} tables ---")
            for t in result["tables"][:5]:
                print(f"  Table {t['index']}: {t['caption'][:50]}... ({t['row_count']} rows)")
                if t.get("is_investment_schedule"):
                    print("    ⭐ INVESTMENT SCHEDULE DETECTED")
    
    asyncio.run(main())
