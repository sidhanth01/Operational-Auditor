from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Added for Docker
from pydantic import BaseModel
import time
import os
from backend.query_engine import analyze_query
from backend.ingestor import run_ingestion

app = FastAPI(title="Hospital RAG API", description="Conflict Detection RAG System")

# 1️⃣ ADD CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

rate_limit_store = {}

@app.middleware("http")
async def rate_limiter_and_timer(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()
    
    if request.url.path.startswith("/api/"):
        if client_ip in rate_limit_store and current_time - rate_limit_store[client_ip] < 1.0:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})
        rate_limit_store[client_ip] = current_time
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.post("/api/query")
async def handle_query(request: QueryRequest):
    try:
        result = analyze_query(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2️⃣ IMPROVED INGEST ENDPOINT FOR n8n
@app.post("/api/ingest")
async def trigger_ingestion(file: UploadFile = File(...)): # Accept file from n8n
    try:
        # Save the incoming file to the data directory
        file_path = os.path.join("data", file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        # Trigger the embedding pipeline
        run_ingestion()
        return {"status": "success", "message": f"Successfully ingested {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))