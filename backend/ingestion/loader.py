import os
import csv
import uuid
import ast
import re
import chromadb
from typing import Dict, List, Any, Tuple
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

def clean_title(title: str) -> str:
    if not title:
        return ""
    return title.strip().lower()

def get_year_from_date(date_str: str) -> int:
    if not date_str:
        return 0
    match = re.search(r'\b(19\d{2}|20\d{2})\b', date_str)
    if match:
        return int(match.group(1))
    return 0

def parse_year(year_str: str) -> int:
    if not year_str:
        return 0
    try:
        return int(float(year_str))
    except ValueError:
        return get_year_from_date(year_str)

def load_cast_map(csv_path: str) -> Dict[str, str]:
    """Loads cast_dataset.csv and returns a mapping of movie ID to a comma-separated string of top 5 actors."""
    cast_map = {}
    if not os.path.exists(csv_path):
        print(f"[LOADER] Cast dataset not found at {csv_path}. Skipping cast enrichment.")
        return cast_map
    print(f"[LOADER] Loading cast metadata from {csv_path}...")
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = row.get("id")
            raw_cast = row.get("cast")
            if not movie_id or not raw_cast:
                continue
            try:
                cast_list = ast.literal_eval(raw_cast)
                top_cast = [member["name"] for member in cast_list[:5] if "name" in member]
                cast_map[movie_id] = ", ".join(top_cast)
            except Exception:
                pass
    print(f"[LOADER] Loaded cast metadata for {len(cast_map)} movies.")
    return cast_map

def load_crew_map(csv_path: str) -> Dict[str, str]:
    """Loads crew_dataset.csv and returns a mapping of movie ID to director name(s)."""
    crew_map = {}
    if not os.path.exists(csv_path):
        print(f"[LOADER] Crew dataset not found at {csv_path}. Skipping crew enrichment.")
        return crew_map
    print(f"[LOADER] Loading crew metadata from {csv_path}...")
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = row.get("id")
            raw_crew = row.get("crew")
            if not movie_id or not raw_crew:
                continue
            try:
                crew_list = ast.literal_eval(raw_crew)
                directors = []
                for member in crew_list:
                    is_dir = member.get("department") == "Directing" or member.get("job") == "Director"
                    if is_dir and "name" in member:
                        directors.append(member["name"])
                seen = set()
                deduped_directors = []
                for d in directors:
                    if d not in seen:
                        seen.add(d)
                        deduped_directors.append(d)
                crew_map[movie_id] = ", ".join(deduped_directors)
            except Exception:
                pass
    print(f"[LOADER] Loaded crew metadata for {len(crew_map)} movies.")
    return crew_map

def populate_database(overwrite: bool = True):
    """
    Consolidates movies from all CSV files in the datasets folder,
    deduplicates them, enriches them with cast/crew metadata,
    chunks the descriptions, embeds them, and populates ChromaDB.
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
    
    datasets_dir = os.path.join(config.BASE_DIR, "datasets")
    
    # Load cast & crew metadata tables
    cast_map = load_cast_map(os.path.join(datasets_dir, "cast_dataset.csv"))
    crew_map = load_crew_map(os.path.join(datasets_dir, "crew_dataset.csv"))
    
    # Store unique movies
    # Key: (clean_title, year)
    unique_movies = {}
    
    # Helper to add/merge a movie into the unique list
    def add_movie(title: str, year: int, genre: str, plot: str, director: str, cast: str, industry: str, source_file: str):
        if not title or not plot:
            return
        
        key = (clean_title(title), year)
        if key not in unique_movies:
            unique_movies[key] = {
                "title": title,
                "year": year,
                "genre": genre,
                "plot": plot,
                "director": director,
                "cast": cast,
                "industry": industry,
                "source_file": source_file
            }
        else:
            # Duplicate movie! Keep the one with the longer plot description
            existing = unique_movies[key]
            if len(plot) > len(existing["plot"]):
                # Update with the longer description
                existing["plot"] = plot
                existing["source_file"] = source_file
            # Merge fields if missing
            if not existing["genre"] and genre:
                existing["genre"] = genre
            if not existing["director"] and director:
                existing["director"] = director
            if not existing["cast"] and cast:
                existing["cast"] = cast
            if not existing["industry"] and industry:
                existing["industry"] = industry
                
    # 1. wiki_movie_plots_deduped.csv
    wiki_path = os.path.join(datasets_dir, "wiki_movie_plots_deduped.csv")
    if os.path.exists(wiki_path):
        print(f"[LOADER] Scanning wiki_movie_plots_deduped.csv...")
        with open(wiki_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("Title", "")
                origin = row.get("Origin/Ethnicity", "")
                year = parse_year(row.get("Release Year"))
                plot = row.get("Plot", "")
                
                is_telugu = (origin == "Telugu")
                is_american_recent = (origin == "American" and year >= 2012)
                
                if is_telugu or is_american_recent:
                    add_movie(
                        title=title,
                        year=year,
                        genre=row.get("Genre", ""),
                        plot=plot,
                        director=row.get("Director", ""),
                        cast=row.get("Cast", ""),
                        industry="Tollywood" if is_telugu else "Hollywood",
                        source_file="wiki_movie_plots_deduped.csv"
                    )
                    
    # 2. TeluguMovies_dataset.csv
    telugu_path = os.path.join(datasets_dir, "TeluguMovies_dataset.csv")
    if os.path.exists(telugu_path):
        print(f"[LOADER] Scanning TeluguMovies_dataset.csv...")
        with open(telugu_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("Movie", "")
                year = parse_year(row.get("Year"))
                overview = row.get("Overview")
                overview = overview.strip() if overview else ""
                genre = row.get("Genre")
                genre = genre.strip() if genre else ""
                add_movie(
                    title=title,
                    year=year,
                    genre=genre,
                    plot=overview,
                    director="",
                    cast="",
                    industry="Tollywood",
                    source_file="TeluguMovies_dataset.csv"
                )
                
    # 3. Wiki_Telugu_Movies_1930_1999.csv
    wiki_telugu_path = os.path.join(datasets_dir, "Wiki_Telugu_Movies_1930_1999.csv")
    if os.path.exists(wiki_telugu_path):
        print(f"[LOADER] Scanning Wiki_Telugu_Movies_1930_1999.csv...")
        with open(wiki_telugu_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("Title", "")
                year = parse_year(row.get("Year"))
                director = row.get("Director", "")
                cast = row.get("Cast", "")
                genre = row.get("Genre", "")
                production = row.get("Production", "")
                music = row.get("Music Composer", "")
                
                # Construct structured descriptive overview since plot is missing
                desc_parts = [f"Movie: {title} ({year})"]
                if director and director.lower() != "unknown":
                    desc_parts.append(f"directed by {director}")
                if cast:
                    desc_parts.append(f"starring {cast.strip().rstrip(',')}")
                if genre and genre.lower() != "unknown":
                    desc_parts.append(f"in the genre of {genre}")
                if production and production.lower() != "unknown":
                    desc_parts.append(f"produced by {production}")
                if music and music.lower() != "unknown":
                    desc_parts.append(f"with music composed by {music}")
                
                desc_text = ", ".join(desc_parts[1:])
                overview = f"{desc_parts[0]} is a film {desc_text}." if len(desc_parts) > 1 else f"{desc_parts[0]}."
                
                add_movie(
                    title=title,
                    year=year,
                    genre=genre,
                    plot=overview,
                    director=director,
                    cast=cast,
                    industry="Tollywood",
                    source_file="Wiki_Telugu_Movies_1930_1999.csv"
                )
                
    # Helper to process TMDb format files
    def process_tmdb_file(filename: str):
        path = os.path.join(datasets_dir, filename)
        if not os.path.exists(path):
            return
        print(f"[LOADER] Scanning {filename}...")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title") or row.get("original_title")
                release_date = row.get("release_date")
                year = get_year_from_date(release_date)
                overview = row.get("overview")
                overview = overview.strip() if overview else ""
                genre = row.get("genre") or row.get("genres") or ""
                movie_id = row.get("id")
                
                # Enrich with cast and crew maps if matching ID found
                cast = cast_map.get(movie_id, "") if movie_id else ""
                director = crew_map.get(movie_id, "") if movie_id else ""
                
                add_movie(
                    title=title,
                    year=year,
                    genre=genre,
                    plot=overview,
                    director=director,
                    cast=cast,
                    industry="Hollywood",
                    source_file=filename
                )

    # Ingest the TMDb datasets
    process_tmdb_file("movies_dataset.csv")
    process_tmdb_file("Movies_dataset_1.csv")
    process_tmdb_file("Top_10000_Movies.csv")
    
    movies_to_ingest = list(unique_movies.values())
    total = len(movies_to_ingest)
    print(f"[LOADER] Consolidated and found {total} unique movies to ingest.")
    
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
                    "source_file": movie["source_file"],
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
        
    print(f"[LOADER] Successfully populated ChromaDB with {collection.count()} total cinema plot records!")

if __name__ == "__main__":
    populate_database(overwrite=True)
