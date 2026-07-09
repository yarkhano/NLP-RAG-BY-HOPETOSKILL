# config.py — All app settings are read from the .env file automatically.
# pydantic-settings maps every environment variable to a typed field here.
# In notebooks we wrote: os.environ["OPENAI_API_KEY"] = "sk-..."
# Here we just keep them in .env and this class picks them up.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── LLM ──────────────────────────────────────────────────────────────────
    openai_api_key: str               # Your OpenAI secret key
    llm_model: str = "gpt-4o-mini"   # Which model to use for answering questions

    # ── Embeddings ────────────────────────────────────────────────────────────
    # "huggingface" = free, runs on your CPU, 384-dimensional vectors
    # "openai"      = paid, runs in the cloud, 1536-dimensional vectors
    # IMPORTANT: once you index documents with one provider, you cannot
    # switch without deleting the collection and re-indexing from scratch.
    embedding_provider: str = "openai"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_url: str                           # e.g. https://xxx.aws.cloud.qdrant.io:6333
    qdrant_api_key: str                       # From Qdrant Cloud dashboard
    qdrant_collection: str = "rag_uploads"   # Name of the collection we create/use

    # ── File upload ───────────────────────────────────────────────────────────
    upload_dir: str = "uploads_tmp"        # Temporary folder for files while they are being processed
    max_upload_size_mb: int = 50           # Reject files larger than this (50 MB default)

    class Config:
        env_file = ".env"              # Read from .env file in the project root
        env_file_encoding = "utf-8"
        extra = "ignore"               # Silently skip unknown env vars (e.g. old RETRIEVER_K)


# Create one shared instance — every other file imports this object
settings = Settings()
