"""
Tests for SEC EDGAR API integration.
"""

import pytest
import httpx

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
USER_AGENT = "SEC-Filing-Analyzer-Test contact@themenonlab.com"


class TestSECAPI:
    """Test SEC EDGAR API access."""
    
    @pytest.mark.asyncio
    async def test_company_lookup_apple(self):
        """Test fetching Apple's company info."""
        cik = "0000320193"  # Apple Inc.
        url = SEC_SUBMISSIONS.format(cik=cik)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Apple Inc."
        assert "filings" in data
    
    @pytest.mark.asyncio
    async def test_company_lookup_bcred(self):
        """Test fetching Blue Owl Capital Corporation (BCRED/OBDC)."""
        cik = "0001775097"  # Blue Owl Capital Corporation
        url = SEC_SUBMISSIONS.format(cik=cik)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "Blue Owl" in data["name"] or "OBDC" in data.get("tickers", [])
    
    @pytest.mark.asyncio
    async def test_filings_contain_10k_10q(self):
        """Test that filings include 10-K and 10-Q forms."""
        cik = "0001775097"
        url = SEC_SUBMISSIONS.format(cik=cik)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT}
            )
        
        data = response.json()
        forms = data["filings"]["recent"]["form"]
        
        assert "10-K" in forms or "10-K/A" in forms
        assert "10-Q" in forms or "10-Q/A" in forms
    
    @pytest.mark.asyncio
    async def test_rate_limit_header(self):
        """Test that we're including proper User-Agent."""
        cik = "0000320193"
        url = SEC_SUBMISSIONS.format(cik=cik)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": USER_AGENT}
            )
        
        # SEC returns 200 if User-Agent is proper
        # Returns 403 if missing or invalid
        assert response.status_code == 200


class TestFilingURLs:
    """Test filing document URL construction."""
    
    def test_filing_url_format(self):
        """Test constructing filing document URLs."""
        cik = "1775097"
        accession = "0001775097-24-000123"
        
        # Remove dashes from accession for URL
        accession_nodash = accession.replace("-", "")
        
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/"
        
        assert "1775097" in base_url
        assert "000177509724000123" in base_url
    
    def test_primary_document_url(self):
        """Test constructing URL for primary document."""
        cik = "1775097"
        accession = "0001775097-24-000123"
        primary_doc = "obdc-20240930.htm"
        
        accession_nodash = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{primary_doc}"
        
        assert url.endswith(".htm")
        assert "edgar/data" in url
