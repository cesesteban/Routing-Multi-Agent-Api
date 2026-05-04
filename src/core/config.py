import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lm_studio").lower()
    MODEL_NAME = os.getenv("MODEL_NAME", "local-model")
    MODEL_NANO = os.getenv("MODEL_NANO", "gemma-3-1b")
    MODEL_POWERFUL = os.getenv("MODEL_POWERFUL", "gemma-3-4b")
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Gemini
    
    # Vertex AI
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # LM Studio
    LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    LM_STUDIO_NANO_URL = os.getenv("LM_STUDIO_NANO_URL", LM_STUDIO_BASE_URL)
    LM_STUDIO_POWERFUL_URL = os.getenv("LM_STUDIO_POWERFUL_URL", LM_STUDIO_BASE_URL)

    # Langfuse
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # RAG Data Paths
    PROMPTS_DIR = os.path.join(os.getcwd(), "prompts")
    BASE_DATA_DIR = os.path.join(os.getcwd(), "data")
    DATA_PATH_RRHH = os.path.join(BASE_DATA_DIR, "rrhh")
    DATA_PATH_TECH = os.path.join(BASE_DATA_DIR, "tecnologia")
    DATA_PATH_FINANZAS = os.path.join(BASE_DATA_DIR, "finanzas")
    DATA_PATH_RECLAMOS = os.path.join(BASE_DATA_DIR, "reclamos")
    DATA_PATH_GENERAL = os.path.join(BASE_DATA_DIR, "general")
    DATA_PATH_SEGURIDAD = os.path.join(BASE_DATA_DIR, "seguridad")
    METRICS_DIR = os.path.join(os.getcwd(), "metrics")
    PERSISTENT_DIR = "/app/persistent"

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{PERSISTENT_DIR}/multi_agent_system.db")

    @classmethod
    def validate(cls):
        """Simple validation to ensure keys are present for chosen provider."""
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            print("WARNING: OPENAI_API_KEY is not set.")
        elif cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
            print("WARNING: GROQ_API_KEY is not set.")
        elif cls.LLM_PROVIDER == "gemini" and not cls.GOOGLE_API_KEY:
            print("WARNING: GOOGLE_API_KEY is not set.")
        
        if not cls.LANGFUSE_PUBLIC_KEY or not cls.LANGFUSE_SECRET_KEY:
            print("WARNING: Langfuse credentials are not set. Tracing will be disabled.")
