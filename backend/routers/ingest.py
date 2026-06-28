import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
from backend import config
from backend.services.embedder import embedder
from backend.ingestion.loader import get_chroma_client, get_collections

router = APIRouter()

class IngestRequest(BaseModel):
    collection: str = Field(..., description="ChromaDB collection: 'movies'")
    text: str = Field(..., description="Cinema/Plot text to ingest")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata fields (movie_name, year, industry, director, genre)")

@router.post("/ingest")
async def ingest_endpoint(request: IngestRequest):
    """
    POST /ingest endpoint for admins to manually add movie chunks to ChromaDB.
    """
    col_name = request.collection.strip().lower()
    text = request.text.strip()
    meta = request.metadata
    
    if col_name != "movies":
        raise HTTPException(status_code=400, detail="Collection must be 'movies'.")
    if not text:
        raise HTTPException(status_code=400, detail="Text content cannot be empty.")
        
    try:
        client = get_chroma_client()
        collections = get_collections(client)
        collection = collections["movies"]
        
        # Setup metadata
        chunk_id = f"movie_{uuid.uuid4()}"
        chunk_metadata = {
            "source_file": "admin_api",
            "collection": "movies",
            "chunk_index": 0,
            "chunk_size": len(text),
            "movie_name": meta.get("movie_name", "Unknown Movie"),
            "year": int(meta.get("year", 2026)),
            "industry": meta.get("industry", "Unknown Industry"),
            "director": meta.get("director", "Unknown Director"),
            "genre": meta.get("genre", "Unknown Genre")
        }
        
        # Update with user provided metadata overrides
        chunk_metadata.update(meta)
        
        # Generate embedding
        embedding = embedder.embed_text(text)
        
        # Add to ChromaDB
        collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[chunk_metadata]
        )
        
        print(f"[INGEST] Movie chunk successfully added to collection 'movies' under ID '{chunk_id}'")
        return {
            "status": "success",
            "id": chunk_id,
            "collection": "movies",
            "message": "Content successfully ingested and indexed."
        }
    except Exception as e:
        print(f"[INGEST] Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest content: {str(e)}")
