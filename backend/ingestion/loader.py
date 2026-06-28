import os
import csv
import uuid
import chromadb
from typing import Dict, List, Any
from backend import config
from backend.services.embedder import embedder
from backend.ingestion.chunker import split_text_into_chunks

def get_chroma_client() -> chromadb.PersistentClient:
    """Returns a persistent ChromaDB client pointing to the configured folder."""
    return chromadb.PersistentClient(path=config.CHROMA_STORE_DIR)

def get_collections(client: chromadb.PersistentClient) -> Dict[str, chromadb.Collection]:
    """Retrieves or creates the primary movies collection in ChromaDB."""
    return {
        "movies": client.get_or_create_collection(
            name="movies", 
            metadata={"hnsw:space": "cosine"}
        )
    }

def populate_database(overwrite: bool = True):
    """
    Reads the Wikipedia movie plots CSV, filters for Telugu and recent American movies,
    chunks the plots, embeds them, and populates ChromaDB.
    """
    client = get_chroma_client()
    collections = get_collections(client)
    collection = collections["movies"]
    
    count = collection.count()
    if count > 0 and not overwrite:
        print(f"[LOADER] Collection 'movies' already populated ({count} documents). Skipping.")
        return
        
    if overwrite and count > 0:
        print(f"[LOADER] Overwriting 'movies' collection. Deleting existing vectors...")
        try:
            client.delete_collection("movies")
        except Exception:
            pass
        # Re-fetch collection
        collection = client.get_or_create_collection(
            name="movies", 
            metadata={"hnsw:space": "cosine"}
        )
    
    # Path to the Wikipedia movie plots CSV
    csv_path = os.path.join(config.BASE_DIR, "datasets", "wiki_movie_plots_deduped.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Could not find Wikipedia movie plots dataset at {csv_path}")
        
    print(f"[LOADER] Scanning dataset: {csv_path}")
    
    movies_to_ingest = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                year = int(row.get("Release Year", 0))
            except ValueError:
                year = 0
                
            title = row.get("Title", "")
            origin = row.get("Origin/Ethnicity", "")
            director = row.get("Director", "")
            cast = row.get("Cast", "")
            genre = row.get("Genre", "")
            plot = row.get("Plot", "")
            
            if not plot or not title:
                continue
                
            # Filter:
            # 1. All Telugu movies
            # 2. American movies from 2012 onwards
            is_telugu = (origin == "Telugu")
            is_american_recent = (origin == "American" and year >= 2012)
            
            if is_telugu or is_american_recent:
                movies_to_ingest.append({
                    "year": year,
                    "title": title,
                    "industry": "Tollywood" if is_telugu else "Hollywood",
                    "director": director,
                    "cast": cast,
                    "genre": genre,
                    "plot": plot
                })
                
    total = len(movies_to_ingest)
    print(f"[LOADER] Found {total} matching movies (Telugu or American >= 2012) to ingest.")
    
    # Ingest in batches of 50 movies to manage CPU and RAM consumption
    batch_size = 50
    for start_idx in range(0, total, batch_size):
        batch = movies_to_ingest[start_idx:start_idx + batch_size]
        print(f"[LOADER] Processing batch {start_idx // batch_size + 1} / {-(total // -batch_size)} ({len(batch)} movies)...")
        
        ids = []
        documents = []
        metadatas = []
        
        for movie in batch:
            # Prefix the chunk with movie metadata context so the LLM knows what film it is about!
            movie_context = f"Movie: {movie['title']} ({movie['year']})\nIndustry: {movie['industry']}\nGenre: {movie['genre']}\nDirector: {movie['director']}\nCast: {movie['cast']}\nPlot: "
            
            chunks = split_text_into_chunks(movie["plot"])
            for idx, chunk in enumerate(chunks):
                chunk_id = f"movie_{uuid.uuid4()}"
                
                meta = {
                    "source_file": "wiki_movie_plots_deduped.csv",
                    "collection": "movies",
                    "movie_name": movie["title"],
                    "year": int(movie["year"]),
                    "industry": movie["industry"],
                    "director": movie["director"],
                    "genre": movie["genre"],
                    "chunk_index": idx
                }
                
                ids.append(chunk_id)
                documents.append(movie_context + chunk)
                metadatas.append(meta)
        
        if not documents:
            continue
            
        # Generate embeddings and add to ChromaDB
        embeddings = embedder.embed_documents(documents)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
    print(f"[LOADER] Successfully populated ChromaDB with {total} cinema plot records!")

if __name__ == "__main__":
    populate_database(overwrite=True)
