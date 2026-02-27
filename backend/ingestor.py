import os
import logging
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Configure basic logging for production visibility
logging.basicConfig(level=logging.INFO)

# Dynamically resolve absolute paths to avoid directory errors
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "./data"
CHROMA_DIR = "./chroma_db"

def run_ingestion():
    """Reads TXT files, chunks them, and stores embeddings in ChromaDB."""
    logging.info(f"Starting ingestion from {DATA_DIR}...")
    
    # Load all text documents from the data directory
    loader = DirectoryLoader(DATA_DIR, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    if not documents:
        logging.warning("No documents found. Please check the data folder.")
        return

    # Split text into 500-character chunks with 50-character overlap for context
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    # Initialize the local, open-source embedding model
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Create and persist the vector database
    vector_store = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=CHROMA_DIR
    )
    
    logging.info(f"Successfully ingested {len(chunks)} chunks into ChromaDB.")

if __name__ == "__main__":
    run_ingestion()