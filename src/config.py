import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # Files
    GRAPH_MEMORY_FILE = os.path.join(DATA_DIR, "memory_graph.gml")
    
    @classmethod
    def validate(cls):
        if not cls.GITHUB_TOKEN or "your_" in cls.GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN is missing or invalid in .env")
        if not cls.GROQ_API_KEY or "your_" in cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing or invalid in .env")

# Ensure directories exist
os.makedirs(Config.DATA_DIR, exist_ok=True)
os.makedirs(Config.LOGS_DIR, exist_ok=True)
