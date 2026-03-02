from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import logging
from threading import Thread

from backend.query_engine import analyze_query
from backend.ingestor import initial_sync, start_watcher


# LOGGING


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# APP INITIALIZATION

app = FastAPI(
    title="Hospital Auditor RAG API",
    description="Backend for detecting factual inconsistencies in hospital reports"
)


# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SCHEMA

class QueryRequest(BaseModel):
    query: str


# RATE LIMITING + PROCESS TIMER

rate_limit_store = {}
RATE_LIMIT_SECONDS = 1.0

@app.middleware("http")
async def rate_limiter_and_timer(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()

    if request.url.path.startswith("/api/"):
        last_request_time = rate_limit_store.get(client_ip)

        if last_request_time and (current_time - last_request_time) < RATE_LIMIT_SECONDS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."}
            )

        rate_limit_store[client_ip] = current_time

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response

# ENDPOINTS

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/api/query")
async def handle_query(request: QueryRequest):
    try:
        logger.info(f"Processing query: {request.query}")
        return analyze_query(request.query)
    except Exception as e:
        logger.error(f"Query Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error during analysis."
        )

@app.post("/api/sync")
async def trigger_sync():
    try:
        logger.info("Manual sync triggered.")
        initial_sync()
        return {"status": "success", "message": "Memory refreshed."}
    except Exception as e:
        logger.error(f"Sync Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# STARTUP & SHUTDOWN

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Hospital Auditor Bot is starting up...")

    # 1️⃣ Ensure DB is populated at boot
    initial_sync()

    # 2️⃣ Start Watchdog in background
    Thread(target=start_watcher, daemon=True).start()

@app.on_event("shutdown")
def shutdown_event():
    logger.info("🛑 Application shutting down.")
