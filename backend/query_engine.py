import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

# --- Embeddings & Vector Store ---
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(
    persist_directory="/app/db",
    embedding_function=embeddings,
    collection_name="hospital_audit_v1"
)

# --- LLM ---
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0  # Deterministic output
)


def analyze_query(query: str):
    query_lower = query.lower().strip()


    # SECURITY GUARDRAIL
    
    injection_keywords = [
        "ignore previous instructions",
        "system prompt",
        "reveal your secrets",
        "hidden text",
        "bypass rules"
    ]

    if any(key in query_lower for key in injection_keywords):
        return {
            "raw_llm_response": (
                "⚠️ **Security Alert:** Access Denied.\n\n"
                "I am programmed to follow strict auditing protocols and "
                "cannot reveal internal system configurations or bypass safeguards."
            ),
            "provenance": []
        }

  
    #  CONVERSATIONAL HANDLING
    
    conversational_inputs = [
        "hi", "hello", "hey",
        "how are you", "who are you",
        "what can you do"
    ]

    if any(word == query_lower for word in conversational_inputs):
        return {
            "raw_llm_response": (
                "Hello! 👋 I am your **Hospital Operational Auditor**.\n\n"
                "I analyze Q1 hospital reports, detect conflicting data, "
                "and verify operational metrics like satisfaction, wait times, and staffing.\n\n"
                "What would you like to audit today?"
            ),
            "provenance": []
        }

  
    #  RETRIEVAL (Improved)
    
    results = vector_store.similarity_search_with_relevance_scores(query, k=6)

    # Slightly relaxed threshold for better cross-doc comparison
    relevant_pairs = [(doc, score) for doc, score in results if score > 0.30]

    if not relevant_pairs:
        return {
            "raw_llm_response": (
                "I don't have enough relevant hospital data to answer that question.\n\n"
                "Please ask about Q1 patient satisfaction, emergency wait times, "
                "complaints, or staffing levels."
            ),
            "provenance": []
        }

  
    # STRUCTURED CONTEXT (Critical Improvement)
    
    structured_context_blocks = []

    for doc, score in relevant_pairs:
        doc_name = os.path.basename(doc.metadata.get("source", "Unknown_Document"))
        structured_context_blocks.append(
            f"Document: {doc_name}\n"
            f"Content:\n{doc.page_content}\n"
            f"---"
        )

    context_text = "\n\n".join(structured_context_blocks)

   
    # ENHANCED SYSTEM PROMPT (Analytical + Deterministic)
  
    system_prompt = """
You are a strict, evidence-based Hospital Operational Auditor.

Your job is to analyze Q1 hospital documents and detect factual inconsistencies.

CRITICAL RULES:
1. Use ONLY the provided context.
2. Do NOT use outside knowledge.
3. If insufficient data exists, clearly state it.
4. A conflict exists when:
   - Two documents report opposite trends (increase vs decrease)
   - Two documents report significantly different percentages for the same metric
   - One report shows improvement while another shows deterioration for the same department
5. Compare documents explicitly before concluding.

ANALYSIS STEPS (follow carefully):
Step 1: Extract key metrics from each document.
Step 2: Compare metrics across documents.
Step 3: Identify alignment or contradiction.
Step 4: Provide a balanced conclusion.

OUTPUT FORMAT (strictly follow):

Answer:
[Concise synthesis of all relevant evidence]

Conflicting Evidence:
- If conflicts exist:
  • Theme: [Metric Name]
    - [Document Name] → [Claim]
    - [Document Name] → [Conflicting Claim]
- If no conflict:
  None

Confidence Level:
High → All sources align
Medium → Minor or localized inconsistencies
Low → Strong contradictions or insufficient data

Reasoning:
[Brief explanation of how confidence was determined]
"""

    human_prompt = f"""
CONTEXT DOCUMENTS:
{context_text}

USER QUERY:
{query}

Perform structured audit analysis as instructed.
"""

    
    # LLM INVOCATION
    
    response = llm.invoke([
        ("system", system_prompt),
        ("human", human_prompt)
    ])

    
    # UI ENHANCEMENT (Emoji Injection)
   
    final_output = response.content
    
    # Inject Emojis for Confidence Level
    if "Confidence Level: High" in final_output:
        final_output = final_output.replace("Confidence Level: High", "🟢 **Confidence Level: High**")
    elif "Confidence Level: Medium" in final_output:
        final_output = final_output.replace("Confidence Level: Medium", "🟡 **Confidence Level: Medium**")
    elif "Confidence Level: Low" in final_output:
        final_output = final_output.replace("Confidence Level: Low", "🔴 **Confidence Level: Low**")
    
    # Inject Emojis for Headers
    final_output = final_output.replace("Conflicting Evidence:", "⚠️ **Conflicting Evidence Detected:**")
    final_output = final_output.replace("Reasoning:", "🔍 **Reasoning:**")


    # CLEAN PROVENANCE
   
    provenance = []

    for doc, score in relevant_pairs:
        clean_name = os.path.basename(doc.metadata.get("source", "Unknown_Document"))
        provenance.append({
            "document": clean_name,
            "similarity_score": round(float(score), 3)
        })

    return {
        "raw_llm_response": final_output,
        "provenance": provenance
    }
