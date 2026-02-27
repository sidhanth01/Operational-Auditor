import streamlit as st
import requests

st.set_page_config(page_title="OPERATIONAL AUDITOR", layout="centered")
st.markdown("""
    <style>
    .main-title {
        font-size: 55px !important;
        font-weight: 700 !important;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 0px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .main-caption {
        font-size: 18px !important;
        color: #A0A0A0;
        text-align: center;
        margin-top: -15px;
        margin-bottom: 20px;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# Centered Title and Caption
st.markdown('<p class="main-title">OPERATIONAL AUDITOR</p>', unsafe_allow_html=True)
st.markdown('<p class="main-caption">AI-Powered Audit & Operational Insight Platform</p>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown("<br>", unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about Q1 patient satisfaction or wait times..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing operational records..."):
            try:
                response = requests.post("http://backend:8000/api/query", json={"query": prompt})
                response.raise_for_status()
                data = response.json()
                
                raw_answer = data.get("raw_llm_response", "")
                provenance = data.get("provenance", [])
                
                ui_text = raw_answer.replace("Confidence Level: Low", "🔴 **Confidence Level: Low**")
                ui_text = ui_text.replace("Confidence Level: Medium", "🟡 **Confidence Level: Medium**")
                ui_text = ui_text.replace("Confidence Level: High", "🟢 **Confidence Level: High**")
                ui_text = ui_text.replace("Conflicting Evidence:", "⚠️ **Conflicting Evidence Detected:**")
                
                if provenance:
                    ui_text += "\n\n---\n**📄 Source Provenance:**\n"
                    for doc in provenance:
                        ui_text += f"- *{doc['document']}* (Similarity: `{doc['similarity_score']:.2f}`)\n"

                st.markdown(ui_text)
                st.session_state.messages.append({"role": "assistant", "content": ui_text})
                
            except Exception as e:
                error_msg = f"❌ Connection Error: Ensure FastAPI is running. ({e})"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})