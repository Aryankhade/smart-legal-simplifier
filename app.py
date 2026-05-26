import streamlit as st
import fitz  # PyMuPDF
from dotenv import load_dotenv
from groq import Groq
import os

# 1. Page Configuration (Must be the first Streamlit command)
st.set_page_config(
    page_title="LexiAI | Advanced Legal Analytics",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load environment variables and initialize Groq client
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# 2. Injecting Premium "Gemini/Claude" Style CSS
st.markdown("""
    <style>
    /* Main App Background & Mesh Gradient Grid */
    .stApp {
        background-color: #0d0f14;
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,12%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,11%,1) 0, transparent 50%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Premium Gradient Header */
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(45deg, #4facfe 0%, #00f2fe 50%, #ff0844 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        letter-spacing: -1px;
    }
    
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.15rem;
        font-weight: 400;
        margin-bottom: 2.5rem;
    }
    
    /* Info Card Design */
    .info-card {
        background: rgba(30, 41, 59, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1.25rem;
        border-radius: 12px;
        color: #cbd5e1;
        font-size: 0.95rem;
        margin-bottom: 2rem;
        backdrop-filter: blur(10px);
    }
    
    /* Layout Cards for Uploaders */
    div[data-testid="stBlock"] {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(8px);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre;
        background-color: rgba(255, 255, 255, 0.02);
        border-radius: 8px 8px 0px 0px;
        color: #94a3b8;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 0 20px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: rgba(255, 255, 255, 0.05);
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #00f2fe !important;
        border-bottom: 2px solid #00f2fe !important;
    }
    
    /* Primary Analyze Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .stButton>button:hover {
        background: linear-gradient(90deg, #2563eb 0%, #60a5fa 100%);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
        transform: translateY(-1px);
    }
    </style>
""", unsafe_allow_html=True)


# Core document processing functions
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def ask_groq(prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error communicating with AI analysis engine: {str(e)}"


# 3. Application Interface Layout
st.markdown('<div class="hero-title">LexiAI Smart Simplifier</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Enterprise-grade AI document intelligence engine. Instant analysis without complexity.</div>', unsafe_allow_html=True)

# Privacy Banner Card
st.markdown("""
    <div class="info-card">
        🛡️ <b>Data Privacy Assurance:</b> Documents are processed safely completely in-memory. 
        No physical files are logged, persisted, or used for model training purposes.
    </div>
""", unsafe_allow_html=True)

# Input Partition (Split columns for a cleaner, modern interface layout)
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### Document Ingestion")
    pdf_file = st.file_uploader("Drop PDF document here", type=["pdf"], label_visibility="collapsed")

with col2:
    st.markdown("### Direct Text Ingestion")
    pasted_text = st.text_area("Paste plain document contents here", height=68, label_visibility="collapsed", placeholder="Paste legal clauses or contract text here...")

document_text = ""

# Handle document extraction logic
if pdf_file:
    document_text = extract_text_from_pdf(pdf_file)
elif pasted_text:
    document_text = pasted_text

st.markdown("<br>", unsafe_allow_html=True)

# 4. Processing Execution & Display Structure
if document_text:
    if st.button("Analyze Document Assets"):
        with st.spinner("Executing structural decomposition & safety evaluations..."):

            summary = ask_groq(f"""
            You are an elite corporate legal analyst.
            Summarize this document in 5-6 crisp, impact-driven sentences using simple but elegant English. 
            Avoid all confusing legal jargon.
            Document: {document_text}
            """)

            breakdown = ask_groq(f"""
            You are a senior corporate counsel.
            Break this document down structurally section-by-section.
            For each section, provide a clear, capitalized title and explain its true legal implication in 1-2 simple, direct sentences.
            Document: {document_text}
            """)

            risks = ask_groq(f"""
            You are a consumer protection legal defense expert.
            Audit this text for hidden liabilities, tricky indemnity clauses, unfair terms, or termination traps.
            For each threat identified: Quote it, explain the legal trap clearly, and state your remediation recommendation.
            If entirely safe, state precisely that the contract matches baseline consumer standards.
            Document: {document_text}
            """)

        st.markdown("---")
        st.markdown("### Analysis Matrix Output")
        
        # Tabs for categorized analysis with clean dark layouts
        tab1, tab2, tab3 = st.tabs(["📝 Executive Summary", "🔍 Section Breakdown", "⚠️ Risk Analytics"])
        
        with tab1:
            st.markdown(summary)
        with tab2:
            st.markdown(breakdown)
        with tab3:
            st.markdown(risks)
else:
    st.caption("Waiting for document input data matrix above before triggering engine...")