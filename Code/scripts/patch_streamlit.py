import sys
from pathlib import Path
import re

st_file = Path("c:/Users/guru2/Downloads/techpulsde/autosar_hld_assistant/app/streamlit_app.py")
content = st_file.read_text(encoding="utf-8")

# Insert 'requests' if not already there
if "import requests" not in content:
    content = re.sub(r"import streamlit as st", "import streamlit as st\nimport requests", content)

# 1. Update tabs list
content = re.sub(
    r"tab_qa, tab_explorer, tab_eval, tab_status, tab_reports = st.tabs\(\[",
    r"tab_ingest, tab_qa, tab_explorer, tab_eval, tab_status, tab_reports = st.tabs([\n    \"📥 HLD Document Ingestion\",",
    content
)

# 2. Add the ingestion tab content right before tab_qa
ingestion_tab_code = """
# ----------------- TAB 0: Ingestion -----------------
with tab_ingest:
    st.markdown("### 📥 HLD Document Ingestion")
    st.caption("Upload a new AUTOSAR HLD PDF document, parse architecture, and index it into the knowledge base.")

    with st.form("ingestion_form"):
        uploaded_file = st.file_uploader("Select HLD PDF", type=["pdf"])
        doc_version = st.text_input("Document Version (e.g., 1.0, 2.0)", value="1.0")
        gov_status = st.selectbox("Governance Status", ["DRAFT", "APPROVED", "ARCHIVED"], index=0)
        
        submit_btn = st.form_submit_button("Upload & Index", type="primary")

    if submit_btn:
        if uploaded_file is None:
            st.error("❌ Please select a PDF file first.")
        elif not doc_version.strip():
            st.error("❌ Please enter a document version.")
        else:
            with st.spinner("Uploading and processing document... This may take a minute."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    data = {"version": doc_version.strip(), "governance_status": gov_status}
                    
                    response = requests.post(f"{API_URL}/documents/upload", files=files, data=data, timeout=120)
                    if response.status_code == 200:
                        res_data = response.json()
                        st.success("✅ Document indexed successfully")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Pages", res_data.get("pages", 0))
                        col2.metric("Chunks", res_data.get("chunks", 0))
                        col3.metric("OCR Pages", res_data.get("ocr_pages", 0))
                        col4.metric("Tables", res_data.get("tables", 0))
                        
                        st.info(f"**Document**: {res_data.get('document')}\\n"
                                f"**Version**: {res_data.get('version')}\\n"
                                f"**Governance**: {gov_status}\\n"
                                f"**Embeddings**: {res_data.get('embedding_status')}\\n"
                                f"**FAISS**: {res_data.get('faiss_status')}")
                                
                        if res_data.get("ocr_pages", 0) > 0:
                            st.warning("⚠️ OCR fallback was used for some pages.")
                    else:
                        st.error(f"❌ Indexing failed: {response.text}")
                except Exception as e:
                    st.error(f"❌ Failed to upload document: {str(e)}")

    st.markdown("---")
    st.markdown("### Document Library")
    
    if st.button("Refresh Library"):
        pass # Streamlit reruns on button click anyway
        
    try:
        docs_res = requests.get(f"{API_URL}/documents", timeout=10)
        if docs_res.status_code == 200:
            docs_data = docs_res.json().get("documents", [])
            if docs_data:
                import pandas as pd
                df = pd.DataFrame(docs_data)
                if "indexed_at" in df.columns:
                    df["indexed_at"] = pd.to_datetime(df["indexed_at"]).dt.strftime('%Y-%m-%d %H:%M:%S')
                # ensure columns exist
                cols_to_show = [c for c in ["document_id", "version", "status", "pages", "chunks", "indexed_at"] if c in df.columns]
                st.dataframe(df[cols_to_show], use_container_width=True)
            else:
                st.info("No documents indexed yet.")
    except Exception as e:
        st.warning(f"Could not load document library: {e}")

# ----------------- TAB 1: Grounded Q&A -----------------
"""

content = re.sub(
    r"# ----------------- TAB 1: Grounded Q&A -----------------",
    ingestion_tab_code,
    content
)

st_file.write_text(content, encoding="utf-8")
print("Updated app/streamlit_app.py successfully.")
