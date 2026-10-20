import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # AURA OS Application Settings
    APP_NAME: str = "AURA OS"
    VERSION: str = "0.1.0-alpha"
    
    # API Server Configuration
    HOST: str = os.getenv("AURA_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("AURA_PORT", 8000))
    
    # SQLite Database Configuration
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aura.db"))
    
    # AI Provider Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

settings = Settings()
