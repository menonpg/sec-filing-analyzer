"""
SEC Filing Vector Store

Indexes SEC filings into Qdrant for semantic search.
Uses Azure OpenAI embeddings (text-embedding-3-large).
"""

import os
import hashlib
import httpx
from typing import List, Optional, Dict
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

# Azure OpenAI Embeddings Config
AZURE_EMBEDDINGS_ENDPOINT = os.environ.get(
    "AZURE_EMBEDDINGS_ENDPOINT",
    "https://llminference01.cognitiveservices.azure.com"
)
AZURE_EMBEDDINGS_KEY = os.environ.get("AZURE_EMBEDDINGS_KEY", "")
AZURE_EMBEDDINGS_DEPLOYMENT = os.environ.get("AZURE_EMBEDDINGS_DEPLOYMENT", "text-embedding-3-large")
AZURE_API_VERSION = "2024-02-01"
EMBEDDING_DIMENSION = 3072

# Qdrant Config
QDRANT_URL = os.environ.get(
    "QDRANT_URL",
    "https://0a09c02d-e7c9-4ebf-a951-1353dba676f0.us-east-1-1.aws.cloud.qdrant.io"
)
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
COLLECTION_NAME = "sec_edgar_filings"  # Unique collection, won't conflict with job-bot

# Chunking config
CHUNK_SIZE = 1500  # characters per chunk
CHUNK_OVERLAP = 200


@dataclass
class FilingChunk:
    """A chunk of a filing for indexing."""
    id: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: str
    company_name: str
    section: str
    chunk_index: int
    text: str
    metadata: dict


class SECVectorStore:
    """Vector store for SEC filings using Qdrant."""
    
    def __init__(self):
        self.qdrant = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=60
        )
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist."""
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        
        if not exists:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection: {COLLECTION_NAME}")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from Azure OpenAI."""
        url = f"{AZURE_EMBEDDINGS_ENDPOINT}/openai/deployments/{AZURE_EMBEDDINGS_DEPLOYMENT}/embeddings?api-version={AZURE_API_VERSION}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={
                    "api-key": AZURE_EMBEDDINGS_KEY,
                    "Content-Type": "application/json"
                },
                json={"input": texts}
            )
            response.raise_for_status()
            data = response.json()
            
            return [item["embedding"] for item in data["data"]]
    
    def chunk_text(self, text: str, section: str = "unknown") -> List[dict]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind('. ')
                if last_period > CHUNK_SIZE // 2:
                    chunk_text = chunk_text[:last_period + 1]
                    end = start + last_period + 1
            
            chunks.append({
                "section": section,
                "chunk_index": chunk_index,
                "text": chunk_text.strip()
            })
            
            start = end - CHUNK_OVERLAP
            chunk_index += 1
        
        return chunks
    
    async def index_filing(
        self,
        cik: str,
        accession_number: str,
        form_type: str,
        filing_date: str,
        company_name: str,
        sections: Dict[str, str],  # section_name -> text
        full_text: str = None
    ) -> dict:
        """
        Index a filing into the vector store.
        
        Args:
            cik: Company CIK
            accession_number: Filing accession number
            form_type: 10-Q, 10-K, 8-K, etc.
            filing_date: Filing date
            company_name: Company name
            sections: Dict of section names to text content
            full_text: Optional full text if sections not available
        
        Returns:
            dict with indexing stats
        """
        all_chunks = []
        
        # Chunk each section
        if sections:
            for section_name, section_text in sections.items():
                if section_text and len(section_text) > 100:
                    chunks = self.chunk_text(section_text, section_name)
                    all_chunks.extend(chunks)
        elif full_text:
            # Fallback to full text chunking
            chunks = self.chunk_text(full_text, "full_document")
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return {"error": "No content to index", "chunks": 0}
        
        # Generate unique IDs for each chunk
        points = []
        texts_to_embed = []
        
        for chunk in all_chunks:
            chunk_id = hashlib.md5(
                f"{cik}:{accession_number}:{chunk['section']}:{chunk['chunk_index']}".encode()
            ).hexdigest()
            
            chunk["id"] = chunk_id
            texts_to_embed.append(chunk["text"])
        
        # Get embeddings in batches
        batch_size = 20
        all_embeddings = []
        
        for i in range(0, len(texts_to_embed), batch_size):
            batch = texts_to_embed[i:i + batch_size]
            embeddings = await self.get_embeddings(batch)
            all_embeddings.extend(embeddings)
        
        # Create points for Qdrant
        for chunk, embedding in zip(all_chunks, all_embeddings):
            points.append(PointStruct(
                id=chunk["id"],
                vector=embedding,
                payload={
                    "cik": cik,
                    "accession_number": accession_number,
                    "form_type": form_type,
                    "filing_date": filing_date,
                    "company_name": company_name,
                    "section": chunk["section"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"]
                }
            ))
        
        # Upsert to Qdrant
        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        return {
            "status": "indexed",
            "cik": cik,
            "accession_number": accession_number,
            "chunks_indexed": len(points),
            "sections": list(set(c["section"] for c in all_chunks))
        }
    
    async def search(
        self,
        query: str,
        cik: Optional[str] = None,
        accession_number: Optional[str] = None,
        form_type: Optional[str] = None,
        limit: int = 10
    ) -> List[dict]:
        """
        Semantic search across indexed filings.
        
        Args:
            query: Search query
            cik: Filter by company CIK
            accession_number: Filter by specific filing (recommended for precision)
            form_type: Filter by form type (10-Q, 10-K, etc.)
            limit: Max results
        
        Returns:
            List of matching chunks with scores
        """
        # Get query embedding
        query_embedding = (await self.get_embeddings([query]))[0]
        
        # Build filter
        must_conditions = []
        if cik:
            must_conditions.append(
                models.FieldCondition(
                    key="cik",
                    match=models.MatchValue(value=cik)
                )
            )
        if accession_number:
            must_conditions.append(
                models.FieldCondition(
                    key="accession_number",
                    match=models.MatchValue(value=accession_number)
                )
            )
        if form_type:
            must_conditions.append(
                models.FieldCondition(
                    key="form_type",
                    match=models.MatchValue(value=form_type)
                )
            )
        
        query_filter = None
        if must_conditions:
            query_filter = models.Filter(must=must_conditions)
        
        # Search using query_points (newer qdrant_client API)
        results = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            query_filter=query_filter,
            limit=limit
        )
        
        return [
            {
                "score": hit.score,
                "cik": hit.payload["cik"],
                "accession_number": hit.payload["accession_number"],
                "company_name": hit.payload["company_name"],
                "form_type": hit.payload["form_type"],
                "filing_date": hit.payload["filing_date"],
                "section": hit.payload["section"],
                "text": hit.payload["text"]
            }
            for hit in results.points
        ]
    
    async def compare_filings(
        self,
        cik: str,
        accession_1: str,
        accession_2: str,
        topics: List[str] = None
    ) -> dict:
        """
        Compare two filings by searching for similar content.
        
        Args:
            cik: Company CIK
            accession_1: First filing accession number
            accession_2: Second filing accession number
            topics: Topics to compare (e.g., ["revenue", "risk factors", "guidance"])
        
        Returns:
            Comparison results for each topic
        """
        if not topics:
            topics = [
                "total revenue and sales",
                "net income and earnings",
                "gross margin",
                "operating expenses",
                "cash flow",
                "risk factors",
                "forward guidance"
            ]
        
        comparisons = {}
        
        for topic in topics:
            # Search in filing 1
            results_1 = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=(await self.get_embeddings([topic]))[0],
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="cik", match=models.MatchValue(value=cik)),
                        models.FieldCondition(key="accession_number", match=models.MatchValue(value=accession_1))
                    ]
                ),
                limit=2
            )
            
            # Search in filing 2
            results_2 = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=(await self.get_embeddings([topic]))[0],
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="cik", match=models.MatchValue(value=cik)),
                        models.FieldCondition(key="accession_number", match=models.MatchValue(value=accession_2))
                    ]
                ),
                limit=2
            )
            
            comparisons[topic] = {
                "filing_1": [
                    {"section": r.payload["section"], "text": r.payload["text"][:500]}
                    for r in results_1.points
                ],
                "filing_2": [
                    {"section": r.payload["section"], "text": r.payload["text"][:500]}
                    for r in results_2.points
                ]
            }
        
        return {
            "cik": cik,
            "filing_1": accession_1,
            "filing_2": accession_2,
            "comparisons": comparisons
        }
    
    def get_stats(self) -> dict:
        """Get collection statistics."""
        info = self.qdrant.get_collection(COLLECTION_NAME)
        # Handle different qdrant_client versions
        points = getattr(info, 'points_count', None) or getattr(info, 'vectors_count', 0)
        return {
            "collection": COLLECTION_NAME,
            "points_count": points,
            "status": str(info.status) if info.status else "unknown"
        }
    
    def is_indexed(self, cik: str, accession_number: str) -> bool:
        """Check if a filing is already indexed."""
        results = self.qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="cik", match=models.MatchValue(value=cik)),
                    models.FieldCondition(key="accession_number", match=models.MatchValue(value=accession_number))
                ]
            ),
            limit=1
        )
        return len(results[0]) > 0
    
    def list_indexed_filings(self, cik: Optional[str] = None) -> List[dict]:
        """List all indexed filings, optionally filtered by CIK."""
        scroll_filter = None
        if cik:
            scroll_filter = models.Filter(
                must=[models.FieldCondition(key="cik", match=models.MatchValue(value=cik))]
            )
        
        # Get unique filings by scrolling and deduplicating
        results, _ = self.qdrant.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=1000,
            with_payload=True
        )
        
        seen = set()
        filings = []
        for point in results:
            key = f"{point.payload['cik']}:{point.payload['accession_number']}"
            if key not in seen:
                seen.add(key)
                filings.append({
                    "cik": point.payload["cik"],
                    "accession_number": point.payload["accession_number"],
                    "company_name": point.payload.get("company_name", ""),
                    "form_type": point.payload.get("form_type", ""),
                    "filing_date": point.payload.get("filing_date", "")
                })
        
        return filings
    
    def delete_filing(self, cik: str, accession_number: str) -> dict:
        """Delete a filing from the index."""
        self.qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="cik", match=models.MatchValue(value=cik)),
                        models.FieldCondition(key="accession_number", match=models.MatchValue(value=accession_number))
                    ]
                )
            )
        )
        return {"status": "deleted", "cik": cik, "accession_number": accession_number}


# Singleton instance
_store: Optional[SECVectorStore] = None


def get_vector_store() -> SECVectorStore:
    """Get or create vector store instance."""
    global _store
    if _store is None:
        _store = SECVectorStore()
    return _store
