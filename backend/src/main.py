import asyncio
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
from sentence_transformers import SentenceTransformer

from dataLoader import load_documents, load_selected_arxivs, search_arxiv, load_web_urls
from chunking import Chunker
from embedding import Embedder
from vector_store import QDrantStore
from query import QueryProcessor
from generator import Generator

ENV_PATH = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Real time global loading state
SYSTEM_STATUS = {
    "ready": False,
    "current_step": "Server spinning up....",
    "progress": 0
}

async def load_resources_in_background(app: FastAPI):
    global SYSTEM_STATUS
    load_dotenv(dotenv_path="../.env")

    try:
        # Connect to Vector DB
        SYSTEM_STATUS["current_step"] = "Connecting to QDrant Database local storage...."
        SYSTEM_STATUS["progress"] = 20
        await asyncio.sleep(1)  # Small visual vuffer for the UI
        app.state.db = QDrantStore()

        # Initializing Groq client
        SYSTEM_STATUS["current_step"] = "Initializing Groq client..."
        SYSTEM_STATUS["progress"] = 40
        await asyncio.sleep(.5)
        shared_groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        app.state.processor = QueryProcessor(client=shared_groq_client, model_name="openai/gpt-oss-120b")
        app.state.generator = Generator(client=shared_groq_client, model_name="openai/gpt-oss-120b")

        # Loading heavy embedding model
        SYSTEM_STATUS["current_step"] = "Loading embedding model..."
        SYSTEM_STATUS["progress"] = 80

        # Loading the model is CPU heavy and synchronous, we run it in a thread pool executer so it doesn't freeze the event loop
        loop = asyncio.get_event_loop()
        shared_embedding_model = await loop.run_in_executor(
            None,
            SentenceTransformer,
            "all-MiniLM-L6-v2"
        )
        app.state.embedding_model = shared_embedding_model

        SYSTEM_STATUS['current_step'] = "Optimizing neural pipelines"
        SYSTEM_STATUS['progress'] = 90
        await asyncio.sleep(1)

        # Completion
        SYSTEM_STATUS['current_step'] = "All systems fully operational!"
        SYSTEM_STATUS['progress'] = 100
        SYSTEM_STATUS["ready"] = True
        print(" RAG pipeline is Active......")
    except Exception as e:
        SYSTEM_STATUS['current_step'] = f"CRITICAL CRASH DURING INITIALIZATION: {str(e)}"
        print(f"Initialization Failure: {str(e)}")

# Lifespan: Loading AI models and Connections once
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting Web server Infrastructure")
    asyncio.create_task(load_resources_in_background(app))
    yield
    print("Server Shutdown sequence Initiated.....")

app = FastAPI(title="Research assistant", lifespan=lifespan)

# Security & CORS Configuration
security = HTTPBearer()

def verify_api_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    # Blocks requests that do not have the correct secret token in the header
    expected_token = os.environ.get("APP_SECRET_TOKEN")
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Invalid or missing API token "
        )
    return credentials.credentials

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production for security
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data schemas
class ChatRequest(BaseModel):
    query:str
    chat_history: Optional[str] = ""
    file_types: Optional[List[str]] = None

class SearchResultChunk(BaseModel):
    chunk:str
    score:float
    metadata:dict

class ChatResponse(BaseModel):
    answer:str
    retrieved_chunks: List[SearchResultChunk]

class URLRequest(BaseModel):
    urls: List[str]

class ArxivSearchRequest(BaseModel):
    query: str

class ArxivLoadRequest(BaseModel):
    paper_ids: list[str]

# API Endpoints
@app.get("/api/status")
async def get_system_status():
    # Public endpoint to verify the server is alive
    return SYSTEM_STATUS

@app.post("/api/upload")
async def handle_document_upload(
        background_tasks: BackgroundTasks,
        request: Request,
        files: List[UploadFile] = File(...),
        token:str = Depends(verify_api_token)
):
    if not SYSTEM_STATUS["ready"]:
        raise HTTPException(status_code=503, detail="Unavailable: System models are still spinning up in memory")

    temp_dir = Path('../temp_uploads')
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Save uploads to the staging directory
        for file in files:
            file_path = temp_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        # Ingest documents using your existing modular loader
        documents = load_documents(str(temp_dir))
        if not documents:
            raise HTTPException(status_code=400, detail="No readable text found in uploaded files...")

        # Chunking
        chunker = Chunker()

        raw_chunks = chunker.chunk(documents)

        print(raw_chunks)
        for chunk in raw_chunks:
            if "metadata" not in chunk:
                chunk["metadata"] = {}
            source_path = chunk["metadata"].get("source", "")
            ext = Path(source_path).suffix.lower().replace(".", "")
            chunk["metadata"]["file_type"] = ext if ext else "unknown"

        # Embedding
        embedder = Embedder(
            model_name="all-MiniLM-L6-v2",
            shared_model=request.app.state.embedding_model
        )
        embedded_chunks = embedder.embed_chunks(raw_chunks)

        # Saving to vector store
        db=request.app.state.db
        db.save_chunks(embedded_chunks)

        return{
            "message": "Documents successfully ingested",
            "documents_processed": len(documents),
            "chunks_created": len(embedded_chunks)
        }
    except Exception as e:
        print(f"[ERROR] Upload pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process documents: {str(e)}")
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@app.post("/api/url/load")
async def handle_url_load(
        request_data: URLRequest,
        request: Request,
        token: str = Depends(verify_api_token)
):
    try:
        documents = load_web_urls(request_data.urls)
        if not documents:
            raise HTTPException(status_code=400, detail="Could not extract text from URLs.")

        # Reuse your existing chunking and embedding logic
        chunker = Chunker()
        raw_chunks = chunker.chunk(documents)

        # Tag metadata for filtering
        for chunk in raw_chunks:
            if "metadata" not in chunk: chunk["metadata"] = {}
            chunk["metadata"]["file_type"] = "web"

        embedder = Embedder(model_name="all-MiniLM-L6-v2", shared_model=request.app.state.embedding_model)
        embedded_chunks = embedder.embed_chunks(raw_chunks)

        request.app.state.db.save_chunks(embedded_chunks)
        return {"message": "URLs ingested", "chunks_created": len(embedded_chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/arxiv/search")
async def handle_arxiv_search(
        request_data: ArxivSearchRequest,
        token: str = Depends(verify_api_token)
):
    try:
        # Fetch top 5 results using your existing arxiv function
        results = search_arxiv(request_data.query, max_results=5)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/arxiv/load")
async def handle_arxiv_load(
        request_data: ArxivLoadRequest,
        request: Request,
        token: str = Depends(verify_api_token)
):
    try:
        documents = load_selected_arxivs(request_data.paper_ids)
        if not documents:
            raise HTTPException(status_code=400, detail="Could not load Arxiv PDFs.")

        chunker = Chunker()
        raw_chunks = chunker.chunk(documents)

        for chunk in raw_chunks:
            if "metadata" not in chunk: chunk["metadata"] = {}
            chunk["metadata"]["file_type"] = "pdf"  # Treat Arxiv papers as PDFs for the filter

        embedder = Embedder(model_name="all-MiniLM-L6-v2", shared_model=request.app.state.embedding_model)
        embedded_chunks = embedder.embed_chunks(raw_chunks)

        request.app.state.db.save_chunks(embedded_chunks)
        return {"message": "Arxiv papers ingested", "chunks_created": len(embedded_chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def handle_chat(
        request_data: ChatRequest,
        request: Request,
        token: str = Depends(verify_api_token)
):
    if not SYSTEM_STATUS["ready"]:
        raise HTTPException(status_code=503, detail="Unavailable: System models are still spinning up in memory")
    # THE MAIN RAG PIPELINE...
    db = request.app.state.db
    processor = request.app.state.processor
    generator = request.app.state.generator
    embedding_model = request.app.state.embedding_model

    try:
        # Pre-processing query
        optimized_queries = processor.rewrite_query(
            raw_query=request_data.query,
            chat_history=request_data.chat_history,
        )
        semantic_text = optimized_queries.get("semantic_query", request_data.query)
        bm25_text = optimized_queries.get("bm25_keywords", request_data.query)

        # Embedding the semantic query
        query_vector = embedding_model.encode([semantic_text])[0].tolist()

        # Hybrid search
        retrieved_chunks = db.search(
            query_vector=query_vector,
            bm25_query_text=bm25_text,
            top_k=5,
            file_types=request_data.file_types,
        )

        print("\n" + "=" * 30)
        print(f"QUERY: {request_data.query}")
        for i, chunk in enumerate(retrieved_chunks):
            print(f"\n--- CHUNK {i + 1} (Score: {chunk.get('score', 0):.2f}) ---")
            # Print the first 200 characters of each retrieved chunk
            print(f"{chunk.get('chunk', '')[:200]}...")
        print("=" * 30 + "\n")

        if not retrieved_chunks: # Fallback
            return ChatResponse(
                answer="I couldn't find any relevant documents :(",
                retrieved_chunks=retrieved_chunks
            )

        # Synthesizing LLM Answer
        final_answer = generator.generate(request_data.query, retrieved_chunks=retrieved_chunks)

        # Return response
        return ChatResponse(
            answer=final_answer,
            retrieved_chunks=retrieved_chunks
        )

    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Server Error")