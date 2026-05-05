import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Default embedding models per provider
_EMBEDDING_DEFAULTS: dict[str, str] = {
    "openai":    "text-embedding-3-small",
    "gemini":    "models/embedding-001",
    "vertexai":  "text-multilingual-embedding-002",
    "lm_studio": "local-model",
    "huggingface": "sentence-transformers/all-MiniLM-L6-v2",
    "groq":      "",  # Groq no soporta embeddings
}


class Config:
    # ── LLM Provider ──────────────────────────────────────────────────────────
    # Options: openai | groq | gemini | vertexai | lm_studio
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lm_studio").lower()
    MODEL_NANO    = os.getenv("MODEL_NANO",    "gemma-3-1b")   # Routing / clasificación rápida
    MODEL_POWERFUL = os.getenv("MODEL_POWERFUL", "gemma-3-4b") # Especialistas / Crítico / Evaluador
    # Compat: MODEL_NAME apunta al modelo potente cuando no se usa LM Studio
    MODEL_NAME = os.getenv("MODEL_NAME", MODEL_POWERFUL)

    # ── Embeddings Provider (independiente del LLM) ───────────────────────────
    # Si no se define, hereda el mismo provider que el LLM.
    # Groq NO soporta embeddings → debe cambiarse a otro provider.
    EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", LLM_PROVIDER).lower()
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL_NAME",
        _EMBEDDING_DEFAULTS.get(os.getenv("EMBEDDINGS_PROVIDER", LLM_PROVIDER).lower(), "local-model")
    )
    # Para LM Studio como proveedor de embeddings
    EMBEDDINGS_BASE_URL = os.getenv("EMBEDDINGS_BASE_URL", os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"))

    # ── API Keys ───────────────────────────────────────────────────────────────
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Gemini via API Key

    # ── Vertex AI / Google Cloud ───────────────────────────────────────────────
    GOOGLE_CLOUD_PROJECT            = os.getenv("GOOGLE_CLOUD_PROJECT")
    GOOGLE_CLOUD_REGION             = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    GOOGLE_APPLICATION_CREDENTIALS  = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # ── LM Studio ─────────────────────────────────────────────────────────────
    LM_STUDIO_BASE_URL     = os.getenv("LM_STUDIO_BASE_URL",     "http://localhost:1234/v1")
    LM_STUDIO_NANO_URL     = os.getenv("LM_STUDIO_NANO_URL",     LM_STUDIO_BASE_URL)
    LM_STUDIO_POWERFUL_URL = os.getenv("LM_STUDIO_POWERFUL_URL", LM_STUDIO_BASE_URL)

    # ── Langfuse ───────────────────────────────────────────────────────────────
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST       = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    # ── RAG Data Paths ─────────────────────────────────────────────────────────
    PROMPTS_DIR       = os.path.join(os.getcwd(), "prompts")
    BASE_DATA_DIR     = os.path.join(os.getcwd(), "data")
    DATA_PATH_RRHH    = os.path.join(BASE_DATA_DIR, "rrhh")
    DATA_PATH_TECH    = os.path.join(BASE_DATA_DIR, "tecnologia")
    DATA_PATH_FINANZAS  = os.path.join(BASE_DATA_DIR, "finanzas")
    DATA_PATH_RECLAMOS  = os.path.join(BASE_DATA_DIR, "reclamos")
    DATA_PATH_GENERAL   = os.path.join(BASE_DATA_DIR, "general")
    DATA_PATH_SEGURIDAD = os.path.join(BASE_DATA_DIR, "seguridad")
    METRICS_DIR       = os.path.join(os.getcwd(), "metrics")
    PERSISTENT_DIR    = "/app/persistent"

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{PERSISTENT_DIR}/multi_agent_system.db")

    @classmethod
    def validate(cls) -> None:
        """Valida que las claves requeridas estén presentes para el provider elegido."""
        _provider_checks = {
            "openai":   (cls.OPENAI_API_KEY,   "OPENAI_API_KEY"),
            "groq":     (cls.GROQ_API_KEY,     "GROQ_API_KEY"),
            "gemini":   (cls.GOOGLE_API_KEY,   "GOOGLE_API_KEY"),
            "vertexai": (cls.GOOGLE_CLOUD_PROJECT, "GOOGLE_CLOUD_PROJECT"),
        }

        key_val, key_name = _provider_checks.get(cls.LLM_PROVIDER, (True, ""))
        if not key_val:
            print(f"WARNING: {key_name} no está configurado para LLM_PROVIDER='{cls.LLM_PROVIDER}'.")

        if cls.EMBEDDINGS_PROVIDER != cls.LLM_PROVIDER:
            emb_val, emb_name = _provider_checks.get(cls.EMBEDDINGS_PROVIDER, (True, ""))
            if not emb_val:
                print(f"WARNING: {emb_name} no está configurado para EMBEDDINGS_PROVIDER='{cls.EMBEDDINGS_PROVIDER}'.")

        if cls.EMBEDDINGS_PROVIDER == "groq":
            print("WARNING: Groq no soporta embeddings. Configura EMBEDDINGS_PROVIDER con otro provider.")

        if not cls.LANGFUSE_PUBLIC_KEY or not cls.LANGFUSE_SECRET_KEY:
            print("WARNING: Langfuse credentials no configuradas. El tracing estará deshabilitado.")

