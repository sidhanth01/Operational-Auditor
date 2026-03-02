import os
import logging
import time
from threading import Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# CONFIG

DATA_DIR = "/app/data"
CHROMA_DIR = "/app/db"
COLLECTION_NAME = "hospital_audit_v1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread safety lock
ingestion_lock = Lock()

# Debounce protection
last_trigger_time = 0
DEBOUNCE_SECONDS = 2

observer = Observer()

# CORE INGESTION LOGIC

def initial_sync():
    """Full re-index of all .txt files with upsert (no duplicates)."""
    global ingestion_lock

    with ingestion_lock:
        logger.info("🚀 Performing full memory sync...")

        if not os.path.exists(DATA_DIR) or not os.listdir(DATA_DIR):
            logger.warning("⚠️ No files found in data directory.")
            return

        loader = DirectoryLoader(DATA_DIR, glob="**/*.txt", loader_cls=TextLoader)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120
        )

        final_chunks = []
        final_ids = []

        for doc in documents:
            file_name = os.path.basename(doc.metadata.get("source", "unknown"))
            sub_chunks = text_splitter.split_documents([doc])

            for i, chunk in enumerate(sub_chunks):
                chunk_id = f"{file_name}_chunk_{i}"
                final_chunks.append(chunk)
                final_ids.append(chunk_id)

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        vector_store = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )

        # UPSERT behavior
        vector_store.add_documents(documents=final_chunks, ids=final_ids)

        logger.info(f"✅ Sync complete. {len(final_ids)} unique chunks indexed.")



# WATCHDOG HANDLER


class DataChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        self.handle_event(event)

    def on_modified(self, event):
        self.handle_event(event)

    def handle_event(self, event):
        global last_trigger_time

        if event.is_directory:
            return

        if not event.src_path.endswith(".txt"):
            return

        current_time = time.time()

        # Debounce protection
        if current_time - last_trigger_time < DEBOUNCE_SECONDS:
            return

        last_trigger_time = current_time

        logger.info(f"🔄 File change detected: {event.src_path}")
        initial_sync()



# WATCHER START FUNCTION

def start_watcher():
    """Starts file monitoring in background thread (non-blocking)."""

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    event_handler = DataChangeHandler()
    observer.schedule(event_handler, DATA_DIR, recursive=False)
    observer.start()

    logger.info("👀 Watchdog started. Monitoring /app/data...")
