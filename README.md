# Operational Auditor (RAG & Automation)

An intelligent auditing platform designed to analyze hospital reports, detect operational discrepancies, and provide data-driven insights. This system implements **Retrieval-Augmented Generation (RAG)** to verify claims across heterogeneous data sources like executive reports, night-shift logs, and patient registries.

---
## 🛠️ Technology Choices

| Component | Choice | Why I chose it |
| :--- | :--- | :--- |
| **LLM Inference** | **Groq (Llama 3)** | For lightning-fast reasoning. It detects conflicts in sub-seconds. |
| **Framework** | **LangChain** | Best for building RAG pipelines and handling complex audit reasoning. |
| **Database** | **ChromaDB** | Simple, persistent, and stays local. Perfect for keeping data private. |
| **Automation** | **Watchdog** | To automate document ingestion without writing extra backend code. |
| **Backend** | **FastAPI** | Fast, modern, and provides automatic API documentation (Swagger). |



---

## 📋 Assumptions

* **File Format**: The system expects documents in `.txt` format for this version.
* **Conflicts**: It is assumed the data contains some direct or indirect contradictions to test the detection engine.
* **Connectivity**: An internet connection is needed to talk to the Groq API.
* **Docker**: The system assumes it is being run via Docker to ensure all ports and libraries work correctly.
* **Data Integrity**: I assume any highly sensitive patient names have been removed, as this is an operational audit tool.

---


## 🏗️ System Architecture

The project is built as a multi-service containerized ecosystem:
1. **Frontend (Streamlit)**: Centered, humanized UI for auditor interaction.
2. **Backend (FastAPI)**: Orchestrates LangChain for retrieval and conflict detection logic.
3. **Vector Database (ChromaDB)**: Stores embeddings of the hospital corpus for semantic retrieval.
4. **Automation**: Handles real-time document ingestion.

---

## 🚀 Key Features

* **Conflict Detection Engine**: Identifies contradictions (e.g., 42-minute vs. 55-minute wait times) and flags them in the UI.
* **Source Provenance**: Every response includes document IDs, snippets, and **Similarity Scores** for auditability.
* **Confidence Calibration**: Provides a "Confidence Level" (High/Medium/Low) based on data consistency.
* **Automated Ingestion**: n8n monitors local directories to update the Vector DB without manual code changes.
* **Hallucination Control**: Uses strict context grounding and temperature control.

---

## ⚙️ Step-by-Step Setup Guide

### 1. Prerequisites
- **Docker Desktop** installed and running.
- **Groq API Key** (or Gemini) for the LLM and Embedding models.

---

### 2. Prepare Environment
Create a `.env` file in the root directory and add your key:
```env
Groq_API_KEY="your_Groq_api_key_here"
```
---

### 3. Run the following command to initialize all services:
* For the first-time setup on a new machine, use the --build flag to compile images specifically for your CPU.
* First-Time Setup:
```
docker-compose up --build
```
---

### 4. Subsequent Starts:
```
docker-compose up
```
---

### 5. Local Access Points
* Auditor UI: http://localhost:8501
* Backend Docs: http://localhost:8000/docs

---

### Project structure

```
hospital-rag-project/
├── data/               # 10+ hospital .txt files (intentional conflicts)
├── backend/            
│   ├── main.py         # FastAPI app (API, Concurrency, Rate Limiting)
│   ├── ingestor.py      # Text chunking and ChromaDB saving
│   ├── query_engine.py  # Groq-powered reasoning, conflict detection, and scoring
│   └── requirements.txt # Dependencies (FastAPI, LangChain, Groq, Chroma)
├── chroma_db/           # Local storage for Vector Database
├── docs/               
│   └── design_doc.md   # Scalability, bottlenecks, and cost trade-offs
├── docker-compose.yml   # Multi-service deployment
├── .env                 # API Key storage (Ignored by Git)
├── .gitignore           # Excludes .env, venv, and local DB files
└── README.md            # Instructions and Architecture Diagram
```
---

### Audit Test Cases (Conflict Detection)

* Case 1: The Wait Time Discrepancy
* Query: "What were the average emergency department wait times for Q1?"

* Case 2: The Staffing Reality Gap
* Query: "Was the emergency department adequately staffed during night shifts?"

---

## 🛠️ Prompting & LLM Control

To ensure response safety and accuracy, the system implements:
* **System Guardrails**: Strict refusal cases if no context is found in the Vector DB.
* **Chain-of-Thought (CoT)**: The `query_engine.py` uses iterative prompting to reason through conflicting documents before generating a final answer.
* **Hallucination Reduction**: Temperature is set to `0.0` with evidence filtering to minimize non-factual output.

---

## 📈 Scalability & Production Roadmap

For a production-grade deployment handling 10,000+ documents, the following transitions are planned:
1.  **Vector Store**: Migrate from local ChromaDB to a managed, distributed cluster like **Pinecone** or **Weaviate**.
2.  **Monitoring**: Implement **Prometheus** and **Grafana** to track retrieval latency, error rates, and embedding drift.
3.  **Ingestion**: Move from local file-watching to a cloud-native **S3 Trigger -> Lambda/Worker -> Vector DB** pipeline.

---

## 1. Scalability Plan (10,000+ Documents)
To transition from a prototype to a production-grade system handling 10k+ documents, the following architectural shifts are required:

* **Distributed Vector Database**: Replace local ChromaDB with a managed cluster like **Weaviate** or **Pinecone** to handle high-concurrency retrieval and sharding.
* **Asynchronous Processing**: Implement a task queue (e.g., **Celery + Redis**) for document ingestion. n8n will trigger a worker instead of calling the API directly to prevent timeouts.
* **Load Balancing**: Deploy multiple instances of the FastAPI backend behind an **NGINX** or **AWS ALB** load balancer.

---

## 2. Potential Bottlenecks
* **Embedding Latency**: Generating embeddings for large batches can slow down ingestion. **Solution**: Use batch processing and parallelize embedding calls.
* **LLM Rate Limits**: High-frequency auditing may hit Groq/OpenAI rate limits. **Solution**: Implement a Tiered LLM Gateway with fallback logic and request queuing.
* **Context Window Constraints**: 100+ documents might exceed the LLM's token limit. **Solution**: Use **Reranking (Cross-Encoders)** to select only the top 5 most relevant snippets before sending to the LLM.

---

## 3. Monitoring & Observability
To ensure system health, we will implement the following metrics:
* **Retrieval Latency**: Tracking how long it takes to fetch vectors from ChromaDB.
* **Embedding Drift**: Monitoring if new data is significantly different from the training/original set.
* **Error Rates**: Tracking 4xx and 5xx responses from the FastAPI backend.
* **Cost Tracking**: Real-time dashboard for API credit consumption per audit session.

---

## ⚖️ Critical Architectural Trade-offs

### 1. Semantic Search vs. Keyword Precision
* **Trade-off**: The system uses **ChromaDB (Vector-only)** for semantic retrieval.
* **Impact**: While excellent at finding conceptual matches (e.g., "staffing issues" matching "nurse shortage"), it may struggle with exact alphanumeric matches like specific Patient IDs or medical codes. 
* **Production Pivot**: For high-scale auditing, a **Hybrid Search** (BM25 + Vector) would be required to ensure 100% recall on specific identifiers.

### 2. Reasoning Depth vs. Latency
* **Trade-off**: Implementation of **Chain-of-Thought (CoT)** reasoning in the query engine.
* **Impact**: To accurately detect conflicts between 10+ documents, the LLM must "think" step-by-step. This increases accuracy and reduces hallucinations but adds 2–4 seconds of latency per query compared to direct answering.
* **Production Pivot**: Implement **Parallel Reranking** to narrow the context window before reasoning to recover speed.



### 3. Consistency vs. Availability (CAP Theorem)
* **Trade-off**: Using **n8n for Asynchronous Ingestion**.
* **Impact**: When a new document is added to the `/data` folder, there is a slight delay (Eventual Consistency) before it is searchable in the UI. This prevents the API from locking up during large file uploads, ensuring the Auditor UI remains responsive.

### 4. Local Persistence vs. Horizontal Scaling
* **Trade-off**: Storage via **Docker Volumes (ChromaDB)**.
* **Impact**: Provides 100% data privacy and zero hosting costs for local audits. However, it limits the system to a single-node deployment.
* **Production Pivot**: Transition to a **Serverless Vector DB (Pinecone)** to support horizontal scaling across multiple geographic regions.
