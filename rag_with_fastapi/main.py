import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from langchain_groq import ChatGroq

from app.config import settings
from app.rag_chain import get_embeddings, get_qdrant_client
from app.api import app_state
from app.routes import router

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
     Code before 'yield' runs once when the server starts.
    Code after 'yield' runs once when the server shuts down.
    We load expensive objects here so every request can reuse them instantly.
    """

    logger.info("Starting embedding model...")
    app_state["embeddings"] = get_embeddings(settings.embedding_provider)

    logger.info("Connecting to Qdrant...")
    app_state["qdrant_client"] = get_qdrant_client(settings.qdrant_url, settings.qdrant_api_key)

    logger.info("Connecting to GROQ LLM...")
    app_state["llm"] = ChatGroq(
        model=settings.llm_model,
        temperature=0,
        api_key=settings.GROQAPIKEY,
    )

    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)  # Create temp upload folder

    logger.info(f"Ready | embeddings={settings.embedding_provider} | collection={settings.qdrant_collection}")

    yield
    app_state.clear()   # Release all resources on shutdown
    logger.info("Server shut down.")


app = FastAPI(
    title       = "RAG API",
    description = "Upload files → Ask questions → Get answers with exact source references",
    version     = "1.0.0",
    lifespan    = lifespan,
)

#The middleware define the access-> which domain ,headres and methods can request to your api,aloow credentials=true to use cookies,sessions etc.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)

app.include_router(router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)