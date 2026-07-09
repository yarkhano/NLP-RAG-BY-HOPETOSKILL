# Lecture 17 — RAG API with FastAPI

A production-style REST API that lets you upload documents, index them in a vector database (Qdrant), and ask questions that get answered using Retrieval-Augmented Generation (RAG).

**What you'll learn:**
- How to wrap a LangChain RAG pipeline inside a real web API
- FastAPI: routing, request validation, file uploads, dependency injection
- Lifespan management: loading the LLM and embeddings once at startup
- How Swagger UI lets you test an API without writing any frontend code

---

## Project Structure

```
lecture_17_fastapi_rag/
├── main.py              ← FastAPI app: startup, CORS, includes router
├── requirements.txt     ← Python dependencies
├── .env                 ← Your API keys (you create this)
├── uploads_tmp/         ← Temp folder for files while they are indexed
└── app/
    ├── config.py        ← All settings read from .env
    ├── models.py        ← Pydantic request/response shapes
    ├── routes.py        ← URL → handler mapping
    ├── api.py           ← Business logic for each endpoint
    ├── file_loader.py   ← Loads PDF, DOCX, MD, CSV, TXT into LangChain Docs
    └── rag_chain.py     ← Core RAG: embed, index, query, list, delete
```

---

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.10+ | Language runtime |
| OpenAI API key | Powers the LLM that generates answers |
| Qdrant Cloud account | Stores and searches your document vectors |

**Get a free Qdrant Cloud cluster:** https://cloud.qdrant.io  
**Get an OpenAI API key:** https://platform.openai.com/api-keys

---

## Step 1 — Clone / open the folder

Open a terminal and navigate to the project folder:

```bash
cd lecture_17_fastapi_rag
```

---

## Step 2 — Create a virtual environment

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On Mac / Linux:
source venv/bin/activate
```

Your terminal prompt should now show `(venv)`.

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> This may take a few minutes the first time — `sentence-transformers` downloads a model.

---

## Step 4 — Create your `.env` file

Create a file called `.env` in the `lecture_17_fastapi_rag/` folder (same level as `main.py`):

```env
# Required — your OpenAI secret key
OPENAI_API_KEY=sk-proj-...

# Required — from your Qdrant Cloud cluster dashboard
QDRANT_URL=https://xxxx.us-east-1-0.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=eyJhbGciO...

# Optional — change these if you want
QDRANT_COLLECTION=rag_uploads
EMBEDDING_PROVIDER=huggingface
LLM_MODEL=gpt-4o-mini
```

**Where to find your Qdrant credentials:**
1. Log in at https://cloud.qdrant.io
2. Click your cluster
3. Copy the **URL** and **API Key** from the cluster dashboard

---

## Step 5 — Start the server

```bash
uvicorn main:app --reload --port 8000
```

You should see:

```
INFO     | Loading embedding model...
INFO     | Connecting to Qdrant...
INFO     | Connecting to OpenAI LLM...
INFO     | Ready | embeddings=huggingface | collection=rag_uploads
INFO     | Application startup complete.
```

---

## Step 6 — Test the API

This project has **no frontend** — you interact with it through the auto-generated Swagger UI.

Open your browser and go to:

```
http://localhost:8000/docs
```

You'll see an interactive interface where you can:

### Upload a document
1. Click `POST /upload` → `Try it out`
2. Click `Choose File` and select a PDF, DOCX, TXT, MD, or CSV
3. Click `Execute`
4. You'll get back a `doc_id` — save this for the delete step

### Ask a question
1. Click `POST /query` → `Try it out`
2. Enter your question:
   ```json
   {
     "question": "What is the main topic of the document?",
     "top_k": 5
   }
   ```
3. Click `Execute`
4. The response includes the **answer** and **source references** (file name, page number, chunk text)

### List all indexed documents
1. Click `GET /documents` → `Try it out` → `Execute`

### Delete a document
1. Click `DELETE /documents/{doc_id}` → `Try it out`
2. Enter the `doc_id` from the upload response
3. Click `Execute`

### Health check
1. Click `GET /health` → `Try it out` → `Execute`

---

## API Reference

| Method | URL | Description |
|--------|-----|-------------|
| `POST` | `/upload` | Upload one or more files |
| `POST` | `/query` | Ask a question |
| `GET` | `/documents` | List all indexed documents |
| `DELETE` | `/documents/{doc_id}` | Remove a document and all its chunks |
| `GET` | `/health` | Check server status |

---

## Supported File Types

| Extension | Library used |
|-----------|-------------|
| `.pdf` | PyPDF — one chunk per page |
| `.docx` | docx2txt |
| `.md`, `.markdown` | unstructured (falls back to TextLoader) |
| `.csv` | CSVLoader — one chunk per row |
| `.txt` | TextLoader |

---

## Common Issues

**`OPENAI_API_KEY` error on startup**
→ Make sure your `.env` file is in the same folder as `main.py` and the key starts with `sk-`.

**`Connection to Qdrant failed`**
→ Double-check the `QDRANT_URL` includes `https://` and the port (`:6333`). Copy it exactly from the Qdrant dashboard.

**`sentence-transformers` download is slow**
→ Normal on first run — the model (~90 MB) is cached after the first download.

**`unstructured` install fails**
→ Remove `unstructured>=0.14.0` from `requirements.txt`. The code falls back to `TextLoader` for `.md` files automatically.

**Port 8000 already in use**
→ Change the port: `uvicorn main:app --reload --port 8080` and visit `http://localhost:8080/docs`

---

## How it Works (Quick Overview)

```
Upload flow:
  File → file_loader.py → LangChain Documents
       → RecursiveCharacterTextSplitter (500 chars, 50 overlap)
       → Embeddings (HuggingFace or OpenAI)
       → Store in Qdrant with metadata (file_name, page_number, doc_id)

Query flow:
  Question → Embed question → Qdrant similarity search (top_k chunks)
           → Build context from chunks
           → LLM: "Answer using only this context: {context}\nQuestion: {question}"
           → Return answer + references
```

---

## Stopping the Server

Press `Ctrl + C` in the terminal where uvicorn is running.

To deactivate the virtual environment:
```bash
deactivate
```
