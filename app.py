import streamlit as st
import os
import io
import base64
import re
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS
import pypdf

load_dotenv()

st.set_page_config(
    page_title="LexiAI Smart Legal Simplifier",
    page_icon="⚖️",
    layout="wide"
)

# ── Credential routing ──────────────────────────────────────────────────────
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GROQ_API_KEY")
    except Exception:
        pass

if not api_key:
    st.error("🔒 Groq API Key missing. Add it to .env (local) or Streamlit Secrets (cloud).")
    st.stop()

client = Groq(api_key=api_key)

# ── Constants ───────────────────────────────────────────────────────────────
# Groq free tier: 6000 TPM safe limit per request (leaves headroom for system prompt)
# ~1 token ≈ 4 chars, so 6000 tokens ≈ 24000 chars
MAX_INPUT_CHARS = 24_000

# ── Styles ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background-color: #0f1015 !important;
    background: radial-gradient(circle at 0% 0%, rgba(79,172,254,0.07) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(161,140,209,0.09) 0%, transparent 50%) !important;
    background-attachment: fixed !important;
}
[data-testid="stMainBlockContainer"] {
    max-width: 95% !important;
    padding-top: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}
.gemini-title {
    background: linear-gradient(90deg,#4facfe 0%,#00f2fe 30%,#a18cd1 70%,#fbc2eb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 3.2rem;
    margin-bottom: 0;
}
.gemini-sub { color:#9aa0a6; font-size:1.2rem; margin-top:-5px; margin-bottom:20px; }
.workspace-card {
    background-color:#161920;
    border:1px solid #232733;
    border-radius:14px;
    padding:30px;
    margin-top:15px;
    box-shadow:0 8px 32px 0 rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown('<h1 class="gemini-title">LexiAI</h1>', unsafe_allow_html=True)
st.markdown('<p class="gemini-sub">Smart Legal Simplifier</p>', unsafe_allow_html=True)
st.info("🛡️ **Data Privacy Protocol:** Assets processed exclusively in volatile memory. Zero logging or storage footprint.")
st.markdown("---")

# ── Input ───────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<h3 style="color:#e8eaed;font-weight:600;">Document Ingestion</h3>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload agreement or contract",
        type=["pdf", "txt"],
        label_visibility="collapsed",
        # FIX 1: key tied to session counter so swapping files clears old state
        key=f"uploader_{st.session_state.get('upload_count', 0)}"
    )
    if uploaded_file:
        st.caption(f"✓ {uploaded_file.name} cached.")

with col2:
    st.markdown('<h3 style="color:#e8eaed;font-weight:600;">Direct Text Ingestion</h3>', unsafe_allow_html=True)
    legal_text = st.text_area(
        "Paste legal text",
        height=72,
        label_visibility="collapsed",
        placeholder="Paste contract text here (supports English, Marathi, Hindi)..."
    )

# ── Analyse button ──────────────────────────────────────────────────────────
if st.button("⚡ Analyze Document", type="primary", use_container_width=True):

    # FIX 2: Clear previous results when a new analysis starts
    for key in ["exec_summary", "detailed_bullets", "risk_matrix", "truncated_warning"]:
        st.session_state.pop(key, None)

    text_to_analyze = ""

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            if not file_bytes:
                st.error("Uploaded file is empty.")
            elif uploaded_file.name.lower().endswith(".pdf"):
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages = [p.extract_text() for p in pdf_reader.pages if p.extract_text()]
                text_to_analyze = "\n".join(pages)
                if not text_to_analyze.strip():
                    st.warning("⚠️ No text extracted — this PDF may be scanned/image-based.")
            else:
                text_to_analyze = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"File read error: {e}")

    elif legal_text.strip():
        text_to_analyze = legal_text

    if not text_to_analyze.strip():
        st.warning("⚠️ Please upload a file or paste text first.")
    else:
        # FIX 3: Truncate oversized documents to avoid TPM rate-limit (Error 413)
        was_truncated = False
        if len(text_to_analyze) > MAX_INPUT_CHARS:
            text_to_analyze = text_to_analyze[:MAX_INPUT_CHARS]
            was_truncated = True

        with st.spinner("Analyzing contract... this may take 10–20 seconds"):
            try:
                system_instruction = (
                    "You are LexiAI, a senior corporate legal specialist fluent in Marathi, Hindi, and English. "
                    "Analyze the submitted contract text. Translate any non-English text and deliver output strictly in English. "
                    "Format your ENTIRE response using these exact headers — no deviation:\n\n"
                    "===EXECUTIVE_SUMMARY===\n"
                    "[Plain-English overview, 3-5 sentences]\n\n"
                    "===DETAILED_BULLETS===\n"
                    "[Bullet list of all key obligations, dates, amounts, and conditions]\n\n"
                    "===RISK_MATRIX===\n"
                    "[Bullet list of legal risks, traps, unfavorable clauses, and recommended actions]"
                )

                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",  # current stable production model
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Analyze this contract:\n\n{text_to_analyze}"}
                    ],
                    temperature=0.1,
                    max_tokens=2048  # FIX 4: Reduced from 4096 — saves output tokens, faster response
                )

                raw = completion.choices[0].message.content

                # ── Parse sections ──────────────────────────────────────────
                exec_summary      = "Could not parse."
                detailed_bullets  = "Could not parse."
                risk_matrix       = "Could not parse."

                try:
                    if "===EXECUTIVE_SUMMARY===" in raw.upper():
                        exec_summary = re.split(r'===EXECUTIVE_SUMMARY===', raw, flags=re.IGNORECASE)[1]
                        exec_summary = re.split(r'===DETAILED_BULLETS===', exec_summary, flags=re.IGNORECASE)[0].strip()

                    if "===DETAILED_BULLETS===" in raw.upper():
                        detailed_bullets = re.split(r'===DETAILED_BULLETS===', raw, flags=re.IGNORECASE)[1]
                        detailed_bullets = re.split(r'===RISK_MATRIX===', detailed_bullets, flags=re.IGNORECASE)[0].strip()

                    if "===RISK_MATRIX===" in raw.upper():
                        risk_matrix = re.split(r'===RISK_MATRIX===', raw, flags=re.IGNORECASE)[1].strip()

                except Exception:
                    exec_summary = raw  # fallback: show raw response

                st.session_state["exec_summary"]     = exec_summary
                st.session_state["detailed_bullets"] = detailed_bullets
                st.session_state["risk_matrix"]      = risk_matrix
                st.session_state["truncated_warning"] = was_truncated

            except Exception as e:
                err = str(e)
                if "413" in err or "rate_limit" in err.lower() or "too large" in err.lower():
                    st.error(
                        "⚠️ Document too large for the free Groq tier (12,000 tokens/min limit). "
                        "Try pasting just the key clauses, or upgrade at console.groq.com/settings/billing."
                    )
                elif "model_decommissioned" in err.lower():
                    st.error("❌ The selected model has been decommissioned. Please update the model ID in app.py.")
                else:
                    st.error(f"Analysis failed: {err}")


# ── Voice helper ────────────────────────────────────────────────────────────
def play_voice(text: str):
    try:
        clean = re.sub(r'[*\-#`]', '', text).replace('<br>', ' ')
        tts = gTTS(text=clean, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        st.markdown(
            f'<audio autoplay controls src="data:audio/mp3;base64,{b64}" style="width:100%;margin-top:15px;"></audio>',
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Voice playback failed: {e}")


# ── Results ─────────────────────────────────────────────────────────────────
if "exec_summary" in st.session_state:
    st.markdown("---")

    # FIX 5: Warn user if document was silently truncated
    if st.session_state.get("truncated_warning"):
        st.warning(
            f"⚠️ Document exceeded {MAX_INPUT_CHARS:,} characters and was trimmed to fit "
            "the free-tier token limit. Analysis covers the first portion only. "
            "For full analysis, upgrade your Groq plan or paste only the key clauses."
        )

    st.markdown('<h2 style="font-weight:700;color:#f5f7fa;margin-bottom:10px;">Analysis Workspace</h2>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📝 Executive Overview", "📋 Core Summary", "⚠️ Risk Assessment"])

    with tab1:
        st.markdown(f"""<div class="workspace-card">
            <h3 style="color:#4facfe;margin-top:0;">Executive Overview</h3>
            <div style="color:#e8eaed;font-size:1.05rem;line-height:1.7;">{st.session_state['exec_summary'].replace(chr(10),'<br>')}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔊 Play Overview Audio", key="play_overview", use_container_width=True):
            play_voice(st.session_state["exec_summary"])

    with tab2:
        st.markdown(f"""<div class="workspace-card">
            <h3 style="color:#00f2fe;margin-top:0;">Core Summary Details</h3>
            <div style="color:#e8eaed;font-size:1.05rem;line-height:1.7;">{st.session_state['detailed_bullets'].replace(chr(10),'<br>')}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔊 Play Details Audio", key="play_details", use_container_width=True):
            play_voice(st.session_state["detailed_bullets"])

    with tab3:
        st.markdown(f"""<div class="workspace-card">
            <h3 style="color:#fbc2eb;margin-top:0;">Risk Profiling Assessment</h3>
            <div style="color:#e8eaed;font-size:1.05rem;line-height:1.7;">{st.session_state['risk_matrix'].replace(chr(10),'<br>')}</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔊 Play Risks Audio", key="play_risks", use_container_width=True):
            play_voice(st.session_state["risk_matrix"])

    # FIX 6: Clear results button so swapping docs doesn't show stale output
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Results & Analyze New Document", use_container_width=True):
        for key in ["exec_summary", "detailed_bullets", "risk_matrix", "truncated_warning"]:
            st.session_state.pop(key, None)
        st.session_state["upload_count"] = st.session_state.get("upload_count", 0) + 1
        st.rerun()