import os
from dotenv import load_dotenv

# Define the root directory of the workspace (one level above this backend file)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load the environmental variables from the .env file in the root workspace
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

# LLM Configurations
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# RAG Configurations
try:
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
except ValueError:
    CONFIDENCE_THRESHOLD = 0.35

# Resolve ChromaDB Store Directory
# If path is relative, resolve it relative to the backend folder
raw_chroma_dir = os.getenv("CHROMA_STORE_DIR", "./chroma_store")
if not os.path.isabs(raw_chroma_dir):
    CHROMA_STORE_DIR = os.path.abspath(os.path.join(BASE_DIR, "backend", raw_chroma_dir))
else:
    CHROMA_STORE_DIR = raw_chroma_dir

# Resolve Knowledge Base Source Directory
raw_kb_dir = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
if not os.path.isabs(raw_kb_dir):
    KNOWLEDGE_BASE_DIR = os.path.abspath(os.path.join(BASE_DIR, "backend", raw_kb_dir))
else:
    KNOWLEDGE_BASE_DIR = raw_kb_dir

# Ensure all critical folders are present on startup
os.makedirs(CHROMA_STORE_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

print(f"[CONFIG] Loaded provider: {LLM_PROVIDER}")
print(f"[CONFIG] Chroma Store path: {CHROMA_STORE_DIR}")
print(f"[CONFIG] Knowledge Base path: {KNOWLEDGE_BASE_DIR}")
print(f"[CONFIG] Confidence threshold: {CONFIDENCE_THRESHOLD}")
