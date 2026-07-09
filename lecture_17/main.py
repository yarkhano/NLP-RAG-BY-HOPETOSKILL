# main.py — Entry point. Creates the FastAPI app, handles startup/shutdown,
# and connects everything together with one line: app.include_router(router)
#
# All API endpoints live in app/routes.py — not here.
#
# Run:
#   uvicorn main:app --reload --port 8000
#   Then open: http://localhost:8000/docs

import logging
from contextlib import asynccontextmanager  # Powers the startup/shutdown lifespan pattern
from pathlib import Path                    # Cross-platform folder creation

from fastapi import FastAPI                             # The web framework
from fastapi.middleware.cors import CORSMiddleware      # Allows browsers on other ports to call this API
from langchain_openai import ChatOpenAI                 # LLM for generating answers

from app.config import settings                         # All settings from .env
from app.rag_chain import get_embeddings, get_qdrant_client  # Factory functions for shared objects
from app.api import app_state                           # Shared state dict (embeddings, client, llm)
from app.routes import router                           # All registered routes from routes.py

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP & SHUTDOWN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before 'yield' runs once when the server starts.
    Code after 'yield' runs once when the server shuts down.
    We load expensive objects here so every request can reuse them instantly.
    """
    logger.info("Loading embedding model...")
    app_state["embeddings"] = get_embeddings(settings.embedding_provider)   # Loads model into memory

    logger.info("Connecting to Qdrant...")
    app_state["qdrant_client"] = get_qdrant_client(settings.qdrant_url, settings.qdrant_api_key)

    logger.info("Connecting to OpenAI LLM...")
    app_state["llm"] = ChatOpenAI(
        model       = settings.llm_model,
        temperature = 0,                       # 0 = deterministic answers
        api_key     = settings.openai_api_key,
    )

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)   # Create temp upload folder

    logger.info(f"Ready | embeddings={settings.embedding_provider} | collection={settings.qdrant_collection}")
    yield   # Server is now running and handling requests

    app_state.clear()   # Release all resources on shutdown
    logger.info("Server shut down.")


# ─────────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "RAG API",
    description = "Upload files → Ask questions → Get answers with exact source references",
    version     = "1.0.0",
    lifespan    = lifespan,
)

# Allow browsers (served from a different port) to call this API
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Register all routes defined in app/routes.py
app.include_router(router)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
