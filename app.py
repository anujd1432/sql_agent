"""
Vibrant & Professional AI SQL Database Agent - Streamlit UI
"""

import os
import re
import sys
import time
import base64
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Ensure workspace is in sys.path and load environment variables
workspace_dir = Path(__file__).resolve().parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

load_dotenv(dotenv_path=workspace_dir / ".env")

from agents import ask_agent, fetch_schema
from database import get_db_connection


# ---------------------------------------------------------------------------
# Page Configuration & Metadata
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI SQL Agent | Intelligent Database Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Helper: Base64 Image Encoder for CSS
# ---------------------------------------------------------------------------
def get_image_base64(img_path: Path) -> str:
    if img_path.exists():
        with open(img_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""


hero_banner_path = workspace_dir / "assets" / "hero_banner.jpg"
agent_avatar_path = workspace_dir / "assets" / "agent_avatar.jpg"
hero_banner_b64 = get_image_base64(hero_banner_path)
agent_avatar_b64 = get_image_base64(agent_avatar_path)


# ---------------------------------------------------------------------------
# Custom Vibrant Theme CSS
# ---------------------------------------------------------------------------
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Fira+Code:wght@400;500;600&display=swap');

/* Global Font & Theme */
html, body, [class*="css"] {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Background Gradients */
.stApp {
    background: radial-gradient(circle at 10% 10%, rgba(20, 24, 45, 1) 0%, rgba(10, 12, 24, 1) 100%);
    color: #e2e8f0;
}

/* Custom Header / Hero Banner Card */
.hero-container {
    position: relative;
    border-radius: 20px;
    padding: 30px;
    margin-bottom: 25px;
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.15);
    overflow: hidden;
    backdrop-filter: blur(12px);
}

.hero-title {
    font-size: 2.3rem;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: #94a3b8;
    line-height: 1.5;
    max-width: 800px;
}

/* Status Pill Badges */
.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-right: 8px;
    margin-top: 12px;
}
.status-green {
    background: rgba(34, 197, 94, 0.15);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.3);
}
.status-blue {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
}
.status-purple {
    background: rgba(168, 85, 247, 0.15);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.3);
}

/* Glassmorphism Content Cards */
.glass-card {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 18px;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.glass-card:hover {
    border-color: rgba(56, 189, 248, 0.3);
}

/* Query Box Card */
.query-card {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid rgba(129, 140, 248, 0.3);
    border-left: 4px solid #818cf8;
    border-radius: 14px;
    padding: 16px 20px;
    margin: 15px 0;
}

/* SQL Code Block */
.sql-code {
    font-family: 'Fira Code', monospace;
    font-size: 0.92rem;
    color: #38bdf8;
    background: rgba(15, 23, 42, 0.85);
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid rgba(56, 189, 248, 0.2);
    overflow-x: auto;
    margin-top: 8px;
}

/* Sidebar Customization */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(10, 15, 30, 0.98) 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

/* Streamlit Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    padding: 8px 20px;
    box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
    transition: all 0.2s ease;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
    box-shadow: 0 6px 20px rgba(14, 165, 233, 0.5);
    transform: translateY(-1px);
}

/* Quick prompt chips */
.prompt-chip {
    display: inline-block;
    background: rgba(30, 41, 59, 0.7);
    color: #cbd5e1;
    padding: 8px 14px;
    margin: 4px;
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
}
.prompt-chip:hover {
    background: rgba(56, 189, 248, 0.15);
    border-color: #38bdf8;
    color: #38bdf8;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Database Connectivity Check
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def check_database_status():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        conn.close()
        return True, "Connected to PostgreSQL"
    except Exception as e:
        return False, str(e)


db_connected, db_status_msg = check_database_status()


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "schema_cache" not in st.session_state:
    st.session_state.schema_cache = None


# ---------------------------------------------------------------------------
# Sidebar: Database Schema & Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    # Sidebar Header with Avatar
    if agent_avatar_b64:
        st.markdown(
            f"""
            <div style="text-align: center; margin-bottom: 15px;">
                <img src="data:image/jpeg;base64,{agent_avatar_b64}" 
                     style="width: 100px; height: 100px; border-radius: 50%; border: 2px solid #38bdf8; box-shadow: 0 0 15px rgba(56,189,248,0.4);" />
                <h3 style="margin-top: 10px; font-weight: 700; color: #f8fafc; font-size: 1.25rem;">AI SQL Assistant</h3>
                <p style="font-size: 0.82rem; color: #94a3b8; margin-top: -8px;">Autonomous PostgreSQL Agent</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### 🤖 AI SQL Assistant")

    st.markdown("---")

    # Engine Status
    st.markdown("#### ⚡ Engine Health")
    if db_connected:
        st.success("🟢 PostgreSQL Connected", icon="✅")
    else:
        st.error(f"🔴 DB Offline: {db_status_msg}", icon="⚠️")

    active_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip().strip('"').strip("'")
    st.markdown(
        f"""
        <div style="background: rgba(15, 23, 42, 0.6); padding: 10px 14px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 15px;">
            <div style="font-size: 0.78rem; color: #94a3b8;">Active LLM Model</div>
            <div style="font-size: 0.88rem; font-weight: 600; color: #38bdf8;">{active_model}</div>
            <div style="font-size: 0.78rem; color: #4ade80; margin-top: 4px;">🛡️ Security Validator Active</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Schema Explorer
    st.markdown("#### 🗄️ Database Schema Explorer")

    col_s1, col_s2 = st.columns([3, 1])
    with col_s2:
        if st.button("🔄", help="Refresh schema from database"):
            st.session_state.schema_cache = None

    if st.session_state.schema_cache is None:
        with st.spinner("Inspecting database tables..."):
            st.session_state.schema_cache = fetch_schema.invoke({})

    with st.expander("📋 View Tables & Columns", expanded=True):
        st.code(st.session_state.schema_cache, language="yaml")

    st.markdown("---")

    # Clear Chat & Reset
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Main Content Area
# ---------------------------------------------------------------------------

# Hero Banner
hero_html = f"""
<div class="hero-container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;">
        <div style="flex: 1; min-width: 280px;">
            <div class="hero-title">AI SQL Database Agent</div>
            <div class="hero-subtitle">
                Query your PostgreSQL database using natural language. The autonomous agent inspects schemas, generates safe read-only SQL, self-corrects errors, and provides instant analytics and visual insights.
            </div>
            <div>
                <span class="status-pill status-green">✓ PostgreSQL Active</span>
                <span class="status-pill status-blue">⚡ Groq High-Speed Inference</span>
                <span class="status-pill status-purple">🛡️ Read-Only Guardrails Active</span>
            </div>
        </div>
"""

if hero_banner_b64:
    hero_html += f"""
        <div style="flex-shrink: 0;">
            <img src="data:image/jpeg;base64,{hero_banner_b64}" 
                 style="width: 320px; height: 160px; object-fit: cover; border-radius: 14px; border: 1px solid rgba(56, 189, 248, 0.4); box-shadow: 0 0 25px rgba(56, 189, 248, 0.2);" />
        </div>
    """

hero_html += """
    </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Quick Prompts / Template Chips
# ---------------------------------------------------------------------------
st.markdown("##### 💡 Suggested Questions")
prompt_cols = st.columns(4)

suggested_prompts = [
    ("👥 Top Paid Employees", "Show top 5 highest paid employees along with their department names"),
    ("💰 Department Budgets", "Which departments have a budget greater than 800,000 and where are they located?"),
    ("📦 High Stock Products", "List all products in Electronics category with price and stock quantity"),
    ("🎓 CS Top Students", "Find top students in Computer Science course with marks above 85"),
]

selected_prompt = None
for i, (label, query_text) in enumerate(suggested_prompts):
    with prompt_cols[i]:
        if st.button(label, key=f"chip_{i}", use_container_width=True):
            selected_prompt = query_text


# ---------------------------------------------------------------------------
# Chat & Response Stream
# ---------------------------------------------------------------------------
st.markdown("---")

# Render conversation history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"**{msg['content']}**")
    else:
        with st.chat_message("assistant", avatar=str(agent_avatar_path) if agent_avatar_path.exists() else "🤖"):
            # If SQL query was executed, show SQL card
            if msg.get("sql_query"):
                st.markdown(
                    f"""
                    <div class="query-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: #818cf8; font-size: 0.9rem;">🔍 GENERATED SQL QUERY</span>
                            <span style="font-size: 0.8rem; background: {'rgba(34, 197, 94, 0.2)' if msg.get('validation_passed') else 'rgba(239, 68, 68, 0.2)'}; color: {'#4ade80' if msg.get('validation_passed') else '#f87171'}; padding: 3px 10px; border-radius: 6px; font-weight: 600;">
                                {'✓ Passed Security Checks' if msg.get('validation_passed') else '✗ Security Rejected'}
                            </span>
                        </div>
                        <div class="sql-code">{msg['sql_query']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # AI Natural Language Response
            st.markdown(msg["content"])

            # Data visualizer if tabular output exists
            if msg.get("df_data") is not None and not msg["df_data"].empty:
                df = msg["df_data"]
                st.markdown("###### 📊 Query Results Table")
                st.dataframe(df, use_container_width=True)

                # Automatic chart suggestion
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
                category_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

                if len(numeric_cols) >= 1 and len(df) > 1:
                    with st.expander("📈 Visual Analytics Chart", expanded=False):
                        chart_tab1, chart_tab2 = st.tabs(["Bar Chart", "Line Chart"])
                        x_axis = category_cols[0] if category_cols else df.columns[0]
                        y_axis = numeric_cols[0]

                        with chart_tab1:
                            st.bar_chart(data=df, x=x_axis, y=y_axis)
                        with chart_tab2:
                            st.line_chart(data=df, x=x_axis, y=y_axis)


# ---------------------------------------------------------------------------
# Handle New User Input
# ---------------------------------------------------------------------------
user_query = st.chat_input("Ask any question about your database in natural language...")

# If user clicked a suggested chip, use it
if selected_prompt:
    user_query = selected_prompt

if user_query:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"**{user_query}**")

    # 2. Invoke SQL Agent
    with st.chat_message("assistant", avatar=str(agent_avatar_path) if agent_avatar_path.exists() else "🤖"):
        status_placeholder = st.empty()
        with status_placeholder.container():
            with st.spinner("🤖 Analyzing schema, synthesizing SQL query, and fetching data..."):
                t_start = time.time()
                result = ask_agent(user_query)
                t_duration = time.time() - t_start

        status_placeholder.empty()

        sql_query = result.get("sql_query")
        validation_passed = result.get("validation_passed", True)
        answer = result.get("answer", "")

        # Display SQL Card
        if sql_query:
            st.markdown(
                f"""
                <div class="query-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; color: #818cf8; font-size: 0.9rem;">🔍 GENERATED SQL QUERY</span>
                        <span style="font-size: 0.8rem; background: {'rgba(34, 197, 94, 0.2)' if validation_passed else 'rgba(239, 68, 68, 0.2)'}; color: {'#4ade80' if validation_passed else '#f87171'}; padding: 3px 10px; border-radius: 6px; font-weight: 600;">
                            {'✓ Passed Security Checks' if validation_passed else '✗ Security Rejected'}
                        </span>
                    </div>
                    <div class="sql-code">{sql_query}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Display Agent Answer
        st.markdown(answer)

        # Parse Data Table from tool output if possible
        df_result = None
        tool_out = result.get("tool_output", "")
        if tool_out and "Columns: [" in tool_out or " | " in tool_out:
            try:
                # Attempt to extract table lines
                table_lines = [l for l in tool_out.splitlines() if " | " in l and not l.startswith("-+-")]
                if len(table_lines) >= 2:
                    headers = [c.strip() for c in table_lines[0].split(" | ")]
                    rows = []
                    for line in table_lines[1:]:
                        vals = [v.strip() for v in line.split(" | ")]
                        if len(vals) == len(headers):
                            rows.append(vals)
                    if rows:
                        df_result = pd.DataFrame(rows, columns=headers)
                        # Try convert numeric columns
                        for col in df_result.columns:
                            try:
                                df_result[col] = pd.to_numeric(df_result[col])
                            except Exception:
                                pass
            except Exception:
                df_result = None

        if df_result is not None and not df_result.empty:
            st.markdown("###### 📊 Query Results Table")
            st.dataframe(df_result, use_container_width=True)

            numeric_cols = df_result.select_dtypes(include=["number"]).columns.tolist()
            category_cols = df_result.select_dtypes(include=["object", "string", "category"]).columns.tolist()

            if len(numeric_cols) >= 1 and len(df_result) > 1:
                with st.expander("📈 Visual Analytics Chart", expanded=True):
                    chart_tab1, chart_tab2 = st.tabs(["Bar Chart", "Line Chart"])
                    x_axis = category_cols[0] if category_cols else df_result.columns[0]
                    y_axis = numeric_cols[0]

                    with chart_tab1:
                        st.bar_chart(data=df_result, x=x_axis, y=y_axis)
                    with chart_tab2:
                        st.line_chart(data=df_result, x=x_axis, y=y_axis)

        # Save to session history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sql_query": sql_query,
            "validation_passed": validation_passed,
            "df_data": df_result,
        })

        # Save to query history
        st.session_state.query_history.append({
            "timestamp": time.strftime("%H:%M:%S"),
            "question": user_query,
            "sql": sql_query,
            "duration": f"{t_duration:.2f}s",
            "passed": validation_passed,
        })
