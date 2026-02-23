"""
SEC Filing HTML Parser

Extracts clean text and tables from SEC HTML filings.
Handles the specific formatting quirks of EDGAR HTML.
"""

from bs4 import BeautifulSoup
from typing import List, Tuple
import re


def parse_filing_html(html_content: str) -> dict:
    """
    Parse SEC filing HTML into structured content.
    
    Args:
        html_content: Raw HTML from SEC filing
        
    Returns:
        dict with sections, tables, and metadata
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for element in soup(['script', 'style', 'meta', 'link']):
        element.decompose()
    
    # Extract sections based on common SEC heading patterns
    sections = extract_sections(soup)
    
    # Extract tables separately for structured processing
    tables = extract_tables(soup)
    
    return {
        "sections": sections,
        "tables": tables,
        "full_text": soup.get_text(separator='\n', strip=True)
    }


def extract_sections(soup: BeautifulSoup) -> List[dict]:
    """
    Extract document sections based on SEC filing structure.
    
    Common patterns:
    - "PART I" / "PART II" etc.
    - "Item 1." / "Item 1A." etc.
    - "SCHEDULE OF INVESTMENTS"
    """
    sections = []
    
    # TODO: Implement section extraction
    # 1. Find section headers (bold text, specific patterns)
    # 2. Extract content between headers
    # 3. Preserve hierarchy (Part > Item > Subsection)
    
    return sections


def extract_tables(soup: BeautifulSoup) -> List[dict]:
    """
    Extract and parse HTML tables from filing.
    
    Returns list of tables with:
    - caption/title if available
    - headers
    - rows (as list of lists)
    - surrounding context
    """
    tables = []
    
    for table in soup.find_all('table'):
        # Get table caption or preceding text
        caption = get_table_caption(table)
        
        # Parse table structure
        headers, rows = parse_table_structure(table)
        
        tables.append({
            "caption": caption,
            "headers": headers,
            "rows": rows,
            "html": str(table)
        })
    
    return tables


def get_table_caption(table) -> str:
    """Find caption or title for a table."""
    # Check for <caption> element
    caption = table.find('caption')
    if caption:
        return caption.get_text(strip=True)
    
    # Check preceding sibling for title
    prev = table.find_previous_sibling()
    if prev and prev.name in ['p', 'div', 'b', 'strong']:
        text = prev.get_text(strip=True)
        if len(text) < 200:  # Likely a title, not a paragraph
            return text
    
    return ""


def parse_table_structure(table) -> Tuple[List[str], List[List[str]]]:
    """
    Parse table into headers and rows.
    
    Handles:
    - Multiple header rows
    - Merged cells (colspan/rowspan)
    - Nested tables (common in SEC filings)
    """
    headers = []
    rows = []
    
    # Find header rows (in thead or first rows with th)
    thead = table.find('thead')
    if thead:
        for tr in thead.find_all('tr'):
            headers.extend([th.get_text(strip=True) for th in tr.find_all('th')])
    
    # Find data rows
    tbody = table.find('tbody') or table
    for tr in tbody.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        row = [cell.get_text(strip=True) for cell in cells]
        if row and not all(c == '' for c in row):
            rows.append(row)
    
    return headers, rows


def is_investment_schedule(table_caption: str, headers: List[str]) -> bool:
    """
    Detect if a table is likely the Schedule of Investments.
    """
    caption_lower = table_caption.lower()
    
    # Check caption
    if any(term in caption_lower for term in [
        'schedule of investments',
        'consolidated schedule of investments',
        'portfolio investments'
    ]):
        return True
    
    # Check headers for investment-related columns
    header_text = ' '.join(headers).lower()
    investment_terms = ['fair value', 'cost', 'principal', 'maturity', 'interest rate']
    matches = sum(1 for term in investment_terms if term in header_text)
    
    return matches >= 3


# Section patterns for 10-K/10-Q
SECTION_PATTERNS = {
    "10-K": [
        (r"PART\s+I\b", "Part I"),
        (r"ITEM\s+1\.?\s*BUSINESS", "Item 1 - Business"),
        (r"ITEM\s+1A\.?\s*RISK\s+FACTORS", "Item 1A - Risk Factors"),
        (r"ITEM\s+7\.?\s*MANAGEMENT", "Item 7 - MD&A"),
        (r"ITEM\s+8\.?\s*FINANCIAL\s+STATEMENTS", "Item 8 - Financial Statements"),
        (r"SCHEDULE\s+OF\s+INVESTMENTS", "Schedule of Investments"),
    ],
    "10-Q": [
        (r"PART\s+I\b", "Part I"),
        (r"ITEM\s+1\.?\s*FINANCIAL\s+STATEMENTS", "Item 1 - Financial Statements"),
        (r"ITEM\s+2\.?\s*MANAGEMENT", "Item 2 - MD&A"),
        (r"ITEM\s+3\.?\s*QUANTITATIVE", "Item 3 - Market Risk"),
        (r"SCHEDULE\s+OF\s+INVESTMENTS", "Schedule of Investments"),
    ]
}
