import os
import chromadb
from typing import List, Dict, Any, Tuple
from sentence_transformers import CrossEncoder
from backend import config
from backend.services.embedder import embedder
from backend.ingestion.loader import get_chroma_client, get_collections

class CinemaRetriever:
    """
    Handles vector search from the ChromaDB movies collection and local 
    Cross-Encoder re-ranking to deliver highly relevant movie plots.
    """
    def __init__(self):
        # Initialize the persistent ChromaDB client
        self.client = get_chroma_client()
        self.collections = get_collections(self.client)
        
        # Load the lightweight Cross-Encoder model locally for semantic re-ranking.
        print("[RETRIEVER] Initializing local CrossEncoder model 'cross-encoder/ms-marco-MiniLM-L-6-v2'...")
        self.re_ranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("[RETRIEVER] CrossEncoder loaded successfully.")

    def retrieve(self, query: str) -> Tuple[List[Dict[str, Any]], float]:
        """
        Main retrieval pipeline:
        1. Embed the query.
        2. Query ChromaDB movies collection.
        3. Translate distances to cosine similarity.
        4. Re-rank results using the local Cross-Encoder.
        5. Compute confidence as the average cosine similarity of the top 3 chunks.
        
        Returns:
            Tuple[List[Dict[str, Any]], float]: (List of top 3 chunks, confidence score)
        """
        print(f"[RETRIEVER] Processing query: '{query}'")
        
        # 1. Embed the query locally
        query_vector = embedder.embed_text(query)
        
        # 2. Query movies collection
        all_retrieved = []
        try:
            collection = self.collections["movies"]
            # Retrieve top 12 candidates
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=12,
                include=["documents", "metadatas", "distances"]
            )
            
            if results and results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                ids = results["ids"][0]
                
                for i in range(len(documents)):
                    dist = distances[i]
                    similarity = max(0.0, min(1.0, 1.0 - dist))
                    
                    all_retrieved.append({
                        "id": ids[i],
                        "text": documents[i],
                        "metadata": metadatas[i],
                        "similarity": similarity,
                        "collection": "movies"
                    })
        except Exception as e:
            print(f"[RETRIEVER] Error querying movies collection: {e}")
            
        if not all_retrieved:
            print("[RETRIEVER] No documents retrieved.")
            return [], 0.0
            
        # 3. Sort by cosine similarity
        all_retrieved.sort(key=lambda x: x["similarity"], reverse=True)
        top_10 = all_retrieved[:10]
        
        # 4. Re-rank using Cross-Encoder
        pairs = [(query, chunk["text"]) for chunk in top_10]
        print(f"[RETRIEVER] Re-ranking with CrossEncoder...")
        cross_scores = self.re_ranker.predict(pairs)
        
        for idx, score in enumerate(cross_scores):
            top_10[idx]["rerank_score"] = float(score)
            
        # Sort by re-rank score (highest first)
        top_10.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_3 = top_10[:3]
        
        # 5. Calculate average similarity as confidence score
        if top_3:
            avg_similarity = sum(chunk["similarity"] for chunk in top_3) / len(top_3)
        else:
            avg_similarity = 0.0
            
        print(f"[RETRIEVER] Selected top-3 chunks. Avg Cosine Similarity (Confidence): {avg_similarity:.4f}")
        for i, chunk in enumerate(top_3):
            meta = chunk['metadata']
            print(f"  Chunk {i+1} | Movie: {meta.get('movie_name')} ({meta.get('year')}) | Cosine Sim: {chunk['similarity']:.4f} | Rerank Score: {chunk['rerank_score']:.4f}")
            
        return top_3, avg_similarity

# Export a single global instance for routers
retriever = CinemaRetriever()
