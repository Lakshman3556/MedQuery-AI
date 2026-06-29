import os
import urllib.request
import zipfile
import io
import re
import shutil
from backend import config

def get_direct_download_url(url: str) -> str:
    url = url.strip()
    # 1. Dropbox link conversion
    if "dropbox.com" in url:
        if "dl=0" in url:
            return url.replace("dl=0", "dl=1")
        elif "dl=1" not in url:
            # Append dl=1 if no query param
            return url + ("&dl=1" if "?" in url else "?dl=1")
        return url
    
    # 2. Google Drive link conversion
    gdrive_match = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)", url)
    if gdrive_match:
        file_id = gdrive_match.group(1)
        return f"https://drive.google.com/uc?id={file_id}&export=download"
        
    return url

def download_and_extract_db():
    db_url = os.getenv("CHROMA_DB_URL", "").strip()
    if not db_url:
        print("[STARTUP] No CHROMA_DB_URL environment variable found. Skipping auto-download.")
        return

    # Check if chroma.sqlite3 already exists in CHROMA_STORE_DIR
    sqlite_path = os.path.join(config.CHROMA_STORE_DIR, "chroma.sqlite3")
    if os.path.exists(sqlite_path):
        print(f"[STARTUP] Database already exists at '{sqlite_path}'. Skipping download.")
        return

    direct_url = get_direct_download_url(db_url)
    print(f"[STARTUP] Pre-built database not found. Downloading from URL: {direct_url}...")
    try:
        os.makedirs(config.CHROMA_STORE_DIR, exist_ok=True)
        
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(direct_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            file_data = response.read()

        # Check if the downloaded file is a ZIP archive (starts with 'PK\x03\x04')
        if file_data.startswith(b"PK\x03\x04"):
            print("[STARTUP] Download complete. Unpacking zip database archive...")
            with zipfile.ZipFile(io.BytesIO(file_data)) as z:
                z.extractall(config.CHROMA_STORE_DIR)
                
                # Check if it was zipped with a parent folder (e.g. chroma_store/chroma.sqlite3)
                extracted_files = z.namelist()
                db_file_rel = next((name for name in extracted_files if name.endswith("chroma.sqlite3")), None)
                if db_file_rel and "/" in db_file_rel:
                    parent_dir_name = db_file_rel.split("/")[0]
                    source_folder = os.path.join(config.CHROMA_STORE_DIR, parent_dir_name)
                    
                    # Move all files up to config.CHROMA_STORE_DIR
                    for item in os.listdir(source_folder):
                        s_path = os.path.join(source_folder, item)
                        d_path = os.path.join(config.CHROMA_STORE_DIR, item)
                        if os.path.exists(d_path):
                            if os.path.isdir(d_path):
                                shutil.rmtree(d_path)
                            else:
                                os.remove(d_path)
                        os.rename(s_path, d_path)
                    shutil.rmtree(source_folder)
            print(f"[STARTUP] Database unpacked successfully into '{config.CHROMA_STORE_DIR}'!")
        else:
            # Assume direct sqlite file
            print("[STARTUP] Download complete. Writing sqlite database file directly...")
            with open(sqlite_path, "wb") as f:
                f.write(file_data)
            print(f"[STARTUP] Database file written successfully to '{sqlite_path}'!")
            
    except Exception as e:
        print(f"[STARTUP] Error downloading/unpacking database: {e}")

# Download database before importing routers, which initialize retriever and connect to ChromaDB
download_and_extract_db()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import chat, ingest

app = FastAPI(
    title="CineQuery AI Backend",
    description="Cinema Knowledge Assistant RAG backend",
    version="1.0.0"
)

# Enable CORS for frontend requests (React app runs on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers under the '/api' prefix
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(ingest.router, prefix="/api", tags=["Admin Ingestion"])

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "provider": config.LLM_PROVIDER}

if __name__ == "__main__":
    # Start the server on port 8000
    print("[MAIN] Starting FastAPI server on http://localhost:8000")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
