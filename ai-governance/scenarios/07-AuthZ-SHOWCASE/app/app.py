"""
app.py — AI Auth Showcase: OBO + M2M + UC Functions + MCP + Governance

OBO pattern: Databricks Apps injects the logged-in user's OAuth token as the
'X-Forwarded-Access-Token' request header. We extract it here and pass it to
every Genie REST call, so Unity Catalog enforces the user's row filters and
column masks — not the app's service principal.

To run locally with your own token:
  export DATABRICKS_HOST=https://<workspace>
  export DATABRICKS_TOKEN=<token>
  streamlit run app.py
"""

import ast
import json
import logging
import os
import re
import time
import uuid

import mlflow
import requests
import streamlit as st
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import PermissionDenied as _SdkPermissionDenied
from auth_utils import get_user_context

logger = logging.getLogger(__name__)

# ── Tracing Init (Module B) ──────────────────────────────────────────────────
_TRACING_ENABLED = False
_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "")
if _EXPERIMENT_NAME:
    try:
        os.environ.setdefault("MLFLOW_TRACKING_URI", "databricks")
        os.environ.setdefault("MLFLOW_ENABLE_ASYNC_TRACE_LOGGING", "true")
        os.environ.setdefault("MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS", "10")
        os.environ.setdefault("MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE", "1000")
        os.environ.setdefault("MLFLOW_TRACE_SAMPLING_RATIO", "1.0")
        # mlflow-tracing requires explicit set_destination() — env vars alone
        # are not enough, and set_experiment()/get_experiment_by_name() are not
        # available in the lightweight mlflow-tracing package.
        from mlflow.tracing import set_destination
        from mlflow.tracing.destination import Databricks
        set_destination(Databricks(experiment_name=_EXPERIMENT_NAME))
        _TRACING_ENABLED = True
        logger.info("Tracing enabled: experiment=%s (destination set)", _EXPERIMENT_NAME)
    except Exception as e:
        logger.warning("Tracing init failed: %s — continuing without tracing", e)

# ── Constants ────────────────────────────────────────────────────────────────

GENIE_SPACE_ID  = os.environ.get("GENIE_SPACE_ID",  "01f117ff5bdd167daf9aed6baa32c4c8")
VS_INDEX        = os.environ.get("VS_INDEX",       "authz_showcase.knowledge_base.product_docs_index")
VS_INDEX_PB     = os.environ.get("VS_INDEX_PB",    "authz_showcase.knowledge_base.sales_playbooks_index")
FM_ENDPOINT     = os.environ.get("FM_ENDPOINT",    "databricks-meta-llama-3-3-70b-instruct")
SQL_WAREHOUSE   = os.environ.get("SQL_WAREHOUSE",  "<YOUR_WAREHOUSE_ID>")
UC_FUNCTIONS_CATALOG = os.environ.get("UC_FUNCTIONS_CATALOG", "authz_showcase")
SUPERVISOR_ENDPOINT  = os.environ.get("SUPERVISOR_ENDPOINT",  "")
CUSTOM_MCP_URL       = os.environ.get("CUSTOM_MCP_URL",       "")
GITHUB_CONN          = os.environ.get("GITHUB_CONN",          "authz_showcase_github_conn")
CUSTMCP_CONN         = os.environ.get("CUSTMCP_CONN",         "authz_showcase_custmcp_conn")


# ── OBO: extract user token from request headers ─────────────────────────────

def _get_auth() -> tuple[str, str]:
    """Return (workspace_host, user_token).

    In Databricks Apps (authorization: user), the Apps proxy injects the
    authenticated user's OAuth token as 'X-Forwarded-Access-Token'.
    Falls back to DATABRICKS_TOKEN env var for local development.
    """
    host = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
    if host and not host.startswith("http"):
        host = f"https://{host}"

    # Databricks Apps injects per-request user token in this header
    token = st.context.headers.get("X-Forwarded-Access-Token", "")

    # Local dev fallback: use env var (PAT or OAuth CLI token)
    if not token:
        token = os.environ.get("DATABRICKS_TOKEN", "")

    return host, token


host, user_token = _get_auth()

# ── M2M: App SP client (no user token → uses app SP credentials) ─────────────

@st.cache_resource(show_spinner=False)
def _sp_client() -> WorkspaceClient:
    """App SP client — M2M auth. Explicit OAuth creds to avoid PAT+OAuth conflict."""
    client_id = os.environ.get("DATABRICKS_CLIENT_ID")
    client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")
    if client_id and client_secret:
        return WorkspaceClient(host=host, client_id=client_id, client_secret=client_secret)
    return WorkspaceClient(host=host)  # local dev: no conflict


w_sp = _sp_client()


@st.cache_resource(show_spinner=False)
def _resolve_sp_numeric_id() -> str:
    """Resolve the app SP's numeric SCIM ID from its client_id UUID.
    Used in terminal demo snippets — auto-updates when the app is recreated.
    """
    client_id = os.environ.get("DATABRICKS_CLIENT_ID", "")
    if not client_id:
        return "0"
    try:
        r = requests.get(
            f"{host}/api/2.0/preview/scim/v2/ServicePrincipals",
            headers={**w_sp.config.authenticate()},
            params={"filter": f'applicationId eq "{client_id}"'},
            timeout=10,
        )
        items = r.json().get("Resources", [])
        return str(items[0]["id"]) if items else "0"
    except Exception:
        return "0"


SP_CLIENT_ID  = os.environ.get("DATABRICKS_CLIENT_ID", "")   # UUID (injected by runtime)
SP_NUMERIC_ID = _resolve_sp_numeric_id()                      # numeric SCIM ID


def _sp_headers() -> dict:
    """Headers using the app SP's M2M token (not the user's token)."""
    auth = w_sp.config.authenticate()
    return {**auth, "Content-Type": "application/json"}



def _clean_md(text: str) -> str:
    """Normalize LLM response text for clean st.markdown rendering.
    - Unicode asterisks → ASCII (fixes bold/italic)
    - $ → HTML entity &#36; (prevents Streamlit treating amounts as LaTeX math)
      Backslash escape \\$ shows the backslash literally in Streamlit — entity is safer.
    - Strip any pre-existing \\$ that the LLM added itself
    """
    text = text.replace("\u2217", "*").replace("\u2216", "*")
    text = text.replace(r"\$", "$")   # undo any LLM self-escaping first
    text = text.replace("$", "&#36;") # then convert all $ to HTML entity
    return text


def _suggested_questions(groups: list[str]) -> list[str]:
    """Return suggested questions appropriate for the user's role."""
    elevated = {"authz_showcase_executives", "authz_showcase_managers", "authz_showcase_finance"}
    if any(g in elevated for g in groups):
        return [
            "Show all opportunities by stage and amount",
            "Show all customers by region and tier",
            "What is the total pipeline value by rep?",
            "Which deals are in the PROPOSAL stage?",
        ]
    return [
        "Show my open opportunities by stage",
        "Show my customers by tier",
        "What is my total pipeline value?",
        "Which of my deals are closing this quarter?",
    ]


_PERSONA_CONFIG = {
    "West Rep":  ("2126682257850363", "authz_showcase_west",       None),
    "Manager":   ("2125742562355351", "authz_showcase_managers",   "manager"),
    "Finance":   ("2125440286635069", "authz_showcase_finance",    "finance"),
    "Executive": ("2124109784120434", "authz_showcase_executives", "executive"),
}
_DEMO_USER_ID = "<YOUR_USER_ID>"


# ── VS + FM REST helpers (M2M) ────────────────────────────────────────────────

VS_SUGGESTED = [
    "DataPlatform Core features",
    "Unity Catalog governance",
    "Delta Sharing with partners",
    "Model Serving latency",
    "Enterprise support SLA",
]

PB_SUGGESTED = [
    "Competitive displacement tactics",
    "Champion change management",
    "Security objection handling",
    "Pricing negotiation strategy",
    "Executive sponsor alignment",
]


_VS_COLUMNS = {
    VS_INDEX:    ["title", "content", "category"],
    VS_INDEX_PB: ["title", "content", "audience", "region"],
}

def vs_query(index: str, query: str, n: int = 5) -> list[dict]:
    """Query a VS index using the M2M SP token; return list of row dicts."""
    r = requests.post(
        f"{host}/api/2.0/vector-search/indexes/{index}/query",
        headers=_sp_headers(),
        json={"query_text": query, "num_results": n, "columns": _VS_COLUMNS.get(index, ["title", "content"])},
        timeout=30,
    )
    r.raise_for_status()
    resp = r.json()
    # manifest is at top level, result.data_array holds the rows
    columns = [c["name"] for c in resp.get("manifest", {}).get("columns", [])]
    rows = resp.get("result", {}).get("data_array", [])
    return [dict(zip(columns, row)) for row in rows]


def fm_summarize(context: str, question: str) -> str:
    """Call Foundation Model API (M2M) to summarize VS results."""
    r = requests.post(
        f"{host}/serving-endpoints/{FM_ENDPOINT}/invocations",
        headers=_sp_headers(),
        json={
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful sales assistant. "
                        "Summarize the provided knowledge base results to answer "
                        "the user's question concisely in 2–4 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nKnowledge base results:\n{context}",
                },
            ],
            "max_tokens": 300,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ── UC Functions helpers (M2M via SQL warehouse) ─────────────────────────────

def _run_fn(sql: str) -> any:
    """Execute a UC function call via SQL warehouse using M2M (app SP) credentials.

    Returns the scalar value from the first row/column, or None on error.
    Uses the app SP token — UC enforces is_member() checks inside the function
    using the SP's identity (added to authz_showcase_executives for full access).
    """
    from databricks.sdk.service.sql import StatementState
    resp = w_sp.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE,
        statement=sql,
        wait_timeout="30s",
    )
    if resp.status.state == StatementState.SUCCEEDED:
        rows = resp.result.data_array if resp.result and resp.result.data_array else []
        return rows[0][0] if rows else None
    return None


def uc_get_quota(rep_email: str) -> str | None:
    """Call get_rep_quota via M2M. Returns quota string or None if denied."""
    val = _run_fn(
        f"SELECT {UC_FUNCTIONS_CATALOG}.functions.get_rep_quota('{rep_email}')"
    )
    return f"${float(val):,.0f}" if val is not None else None


def uc_get_attainment(rep_email: str) -> str | None:
    """Call calculate_attainment via M2M."""
    val = _run_fn(
        f"SELECT {UC_FUNCTIONS_CATALOG}.functions.calculate_attainment('{rep_email}')"
    )
    return f"{float(val):.1f}%" if val is not None else None


def uc_get_next_action(opp_id: str) -> str | None:
    """Call recommend_next_action via M2M."""
    return _run_fn(
        f"SELECT {UC_FUNCTIONS_CATALOG}.functions.recommend_next_action('{opp_id}')"
    )


def uc_get_opportunities(rep_email: str) -> list[dict]:
    """Fetch opportunities for a rep via M2M (SP sees all; filtered by rep_email param)."""
    from databricks.sdk.service.sql import StatementState
    resp = w_sp.statement_execution.execute_statement(
        warehouse_id=SQL_WAREHOUSE,
        statement=(
            f"SELECT opp_id, customer_id, stage, amount, close_date "
            f"FROM {UC_FUNCTIONS_CATALOG}.sales.opportunities "
            f"WHERE rep_email = '{rep_email}' "
            f"ORDER BY amount DESC"
        ),
        wait_timeout="30s",
    )
    if resp.status.state != StatementState.SUCCEEDED:
        return []
    schema = resp.manifest.schema.columns if resp.manifest and resp.manifest.schema else []
    col_names = [c.name for c in schema]
    rows = resp.result.data_array if resp.result and resp.result.data_array else []
    return [dict(zip(col_names, row)) for row in rows]


# ── Supervisor Agent (OBO) ────────────────────────────────────────────────────

def supervisor_ask(question: str, user_token: str, history: list[dict]) -> str:
    """Call Agent Bricks supervisor with the user's OBO token.

    The supervisor routes to sub-agents (Genie space + UC Functions). Each
    sub-agent enforces the calling user's UC permissions — the user's token
    travels end-to-end, so row filters and is_member() checks run as the user.

    Agent Bricks uses the MLflow ResponsesAgent format:
      request:  {"input": [{"role": ..., "content": ...}, ...]}
      response: {"output": [{"role": "assistant", "content": ...}]}
    """
    span_ctx = mlflow.start_span(name="app_a.supervisor_ask") if _TRACING_ENABLED else None
    try:
        if span_ctx:
            span = span_ctx.__enter__()
            span.set_inputs({"question": question, "user_token": "[REDACTED]", "history": f"{len(history)} messages"})
            client_request_id = str(uuid.uuid4())
            mlflow.update_current_trace(
                client_request_id=client_request_id,
                tags={"service_name": "app-a-frontend", "entry_point": "tab5_supervisor"},
            )

        system = {
            "role": "system",
            "content": (
                "Format all responses using clean markdown. "
                "Show deal/opportunity lists as a markdown table with columns: Opp ID, Customer, Stage, Amount, Close Date. "
                "Use **bold** for key values. Keep responses concise — avoid nested bullet trees. "
                "For single-value answers (quota, attainment) show the value prominently then a one-line explanation."
            ),
        }
        messages = [system] + [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": question})

        req_headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}

        r = requests.post(
            f"{host}/serving-endpoints/{SUPERVISOR_ENDPOINT}/invocations",
            headers=req_headers,
            json={"input": messages},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        # Agent Bricks ResponsesAgent format.
        # output is a list of mixed items: {"type":"message","content":[{"type":"output_text","text":"..."}]}
        # and {"type":"function_call",...}. We want the text from the last "message" item.
        output = data.get("output", [])
        result = None
        if isinstance(output, list):
            for item in reversed(output):
                if item.get("type") == "message":
                    content = item.get("content", [])
                    if isinstance(content, list) and content:
                        result = content[-1].get("text", str(content[-1]))
                        break
                    if isinstance(content, str):
                        result = content
                        break
        if result is None and isinstance(output, str):
            result = output
        if result is None:
            choices = data.get("choices", [])
            result = choices[0]["message"]["content"] if choices else str(data)

        if span_ctx:
            span.set_outputs({"response": result[:500] if result else None})
        return result
    except Exception:
        if span_ctx:
            span.set_status("ERROR")
        raise
    finally:
        if span_ctx:
            span_ctx.__exit__(None, None, None)


# ── User context (identity + active UC policies) ─────────────────────────────

@st.cache_data(ttl=10, show_spinner=False)
def _load_ctx(token: str) -> dict:  # token param ensures per-user cache keying
    return get_user_context(host, token)


ctx = _load_ctx(user_token)

# ── Genie REST API helpers ────────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}


def _poll(conv_id: str, msg_id: str, timeout: int = 120) -> dict:
    """Poll until Genie message status is terminal or timeout is reached."""
    deadline = time.time() + timeout
    delay = 2
    while time.time() < deadline:
        r = requests.get(
            f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"
            f"/conversations/{conv_id}/messages/{msg_id}",
            headers=_headers(),
            timeout=30,
        )
        r.raise_for_status()
        msg = r.json()
        if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            return msg
        time.sleep(delay)
        delay = min(delay * 2, 30)
    return {"status": "TIMEOUT", "attachments": []}


def _extract(msg: dict) -> tuple[str, str]:
    """Return (text_response, sql) from a completed Genie message."""
    text = sql = ""
    for att in msg.get("attachments", []):
        if "query" in att:
            if att["query"].get("query"):
                sql = att["query"]["query"]
            if att["query"].get("description"):
                text = att["query"]["description"]
        if "text" in att and att["text"].get("content"):
            text = att["text"]["content"]
    return text, sql


def genie_ask(question: str, conv_id: str | None = None) -> dict:
    """Start a new conversation or continue an existing one."""
    if conv_id:
        r = requests.post(
            f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}"
            f"/conversations/{conv_id}/messages",
            headers=_headers(),
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        new_conv_id = conv_id
        msg_id = data["message"]["id"]
    else:
        r = requests.post(
            f"{host}/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation",
            headers=_headers(),
            json={"content": question},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        new_conv_id = data["conversation"]["id"]
        msg_id = data["message"]["id"]

    msg = _poll(new_conv_id, msg_id)
    text, sql = _extract(msg)
    return {
        "conversation_id": new_conv_id,
        "status":          msg.get("status"),
        "text":            text,
        "sql":             sql,
    }


# ── Page layout ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="AI Auth Showcase", page_icon="🔐", layout="wide")

# ── Global CSS — Dark Premium Enterprise Dashboard ────────────────────────────
st.markdown("""
<style>
/* ── Base & Background — Swiss Modern ── */
.stApp {
    background-color: #ffffff;
    color: #111111;
}
.stApp > header {
    background-color: #ffffff;
}
section[data-testid="stSidebar"] {
    background-color: #f4f3f0;
    border-right: 1px solid #e0ddd8;
}
section[data-testid="stSidebar"] > div {
    background-color: #f4f3f0;
}

/* ── Typography ── */
body, .stApp, .stMarkdown, p, li, span {
    color: #111111;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif;
}
h1, h2, h3, h4, h5, h6 {
    color: #111111 !important;
    font-weight: 600;
}
code {
    background-color: #eae9e5 !important;
    color: #1d4ed8 !important;
    border-radius: 4px;
    padding: 1px 5px;
}
pre {
    background-color: #f4f3f0 !important;
    border: 1px solid #e0ddd8 !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #f4f3f0;
    border-bottom: 1px solid #e0ddd8;
    gap: 4px;
    padding: 0 4px;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #787878;
    border-radius: 6px 6px 0 0;
    padding: 10px 20px;
    font-weight: 500;
    font-size: 0.85rem;
    border: none;
    transition: color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #111111;
    background-color: #eae9e5;
}
.stTabs [aria-selected="true"] {
    background-color: #ffffff !important;
    color: #cc3311 !important;
    border-bottom: 2px solid #cc3311 !important;
    font-weight: 600;
}
.stTabs [data-baseweb="tab-panel"] {
    background-color: #ffffff;
    padding-top: 24px;
}

/* ── Buttons ── */
.stButton > button {
    background-color: #f4f3f0;
    color: #111111;
    border: 1px solid #e0ddd8;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.15s;
}
.stButton > button:hover {
    background-color: #eae9e5;
    border-color: #c0bdb8;
    color: #111111;
}
.stButton > button[kind="primary"] {
    background-color: #cc3311;
    color: #fff;
    border: none;
    font-weight: 600;
}
.stButton > button[kind="primary"]:hover {
    background-color: #b02d0e;
    color: #fff;
}

/* ── Input Fields ── */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stRadio > div {
    background-color: #f4f3f0 !important;
    color: #111111 !important;
    border-color: #e0ddd8 !important;
    border-radius: 8px;
}
.stTextInput > div > div > input:focus {
    border-color: #cc3311 !important;
    box-shadow: 0 0 0 1px #cc3311 !important;
}
.stTextInput label, .stSelectbox label, .stRadio label {
    color: #787878 !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #f4f3f0;
    border: 1px solid #e0ddd8;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] {
    color: #787878 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 500;
}
[data-testid="stMetricValue"] {
    color: #111111 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    line-height: 1.2;
}
[data-testid="stMetricDelta"] {
    color: #16a34a !important;
}

/* ── Alerts / Info boxes ── */
.stAlert {
    border-radius: 8px !important;
    border-width: 1px !important;
}
div[data-testid="stNotification"] {
    border-radius: 8px;
}
.stAlert[data-baseweb="notification"][kind="info"],
div[data-baseweb="notification"][kind="info"] {
    background-color: #eff6ff !important;
    border-color: #bfdbfe !important;
    color: #1d4ed8 !important;
}
.stAlert[data-baseweb="notification"][kind="success"],
div[data-baseweb="notification"][kind="success"] {
    background-color: #f0fdf4 !important;
    border-color: #bbf7d0 !important;
    color: #166534 !important;
}
.stAlert[data-baseweb="notification"][kind="warning"],
div[data-baseweb="notification"][kind="warning"] {
    background-color: #fffbeb !important;
    border-color: #fde68a !important;
    color: #92400e !important;
}
.stAlert[data-baseweb="notification"][kind="error"],
div[data-baseweb="notification"][kind="error"] {
    background-color: #fef2f2 !important;
    border-color: #fecaca !important;
    color: #991b1b !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background-color: #f4f3f0 !important;
    border: 1px solid #e0ddd8 !important;
    border-radius: 8px !important;
    color: #787878 !important;
    font-weight: 500;
}
.streamlit-expanderContent {
    background-color: #ffffff !important;
    border: 1px solid #e0ddd8 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ── Containers with border ── */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #f4f3f0;
    border: 1px solid #e0ddd8 !important;
    border-radius: 10px;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background-color: #f4f3f0;
    border: 1px solid #e0ddd8;
    border-radius: 10px;
    padding: 12px 16px;
}

/* ── Divider ── */
hr {
    border-color: #e0ddd8 !important;
}

/* ── Sidebar text ── */
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] .stMarkdown span {
    color: #787878;
    font-size: 0.85rem;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {
    color: #111111 !important;
}

/* ── Caption text ── */
.stCaptionContainer, [data-testid="stCaptionContainer"] {
    color: #787878 !important;
    font-size: 0.75rem !important;
}

/* ── Tab header accent border ── */
.tab-section-header {
    border-left: 3px solid #cc3311;
    padding-left: 12px;
    margin-bottom: 4px;
}

/* ── Result card ── */
.result-card {
    background: #f4f3f0;
    border: 1px solid #e0ddd8;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 8px 0;
    transition: border-color 0.15s;
}
.result-card:hover {
    border-color: #c0bdb8;
}

/* ── Auth badge — Swiss flat ── */
.badge-obo {
    background: #cc3311;
    color: #fff;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: inline-block;
}
.badge-m2m {
    background: #1d4ed8;
    color: #fff;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: inline-block;
}

/* ── Radio buttons ── */
.stRadio > label {
    color: #111111 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f4f3f0; }
::-webkit-scrollbar-thumb { background: #c0bdb8; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a0a09a; }
</style>
""", unsafe_allow_html=True)

# ── App Header — Swiss Modern ─────────────────────────────────────────────────
st.markdown("""
<div style="
    background: #ffffff;
    border-bottom: 3px solid #cc3311;
    border-radius: 0;
    padding: 18px 28px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
">
    <div style="
        width: 40px; height: 40px;
        background: #cc3311;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 20px; line-height: 1; color: white;
    ">🔐</div>
    <div>
        <div style="
            font-size: 22px;
            font-weight: 700;
            color: #111111;
            line-height: 1.2;
            letter-spacing: -0.3px;
        ">AI Auth Showcase</div>
        <div style="font-size: 12px; color: #787878; margin-top: 3px; letter-spacing: 0.5px;">
            Databricks Apps &nbsp;·&nbsp; Unity Catalog &nbsp;·&nbsp; MCP &nbsp;·&nbsp; Governance
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar — Identity Panel
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px;">
        <span style="font-size:28px;">🔐</span>
        <div style="font-size:16px; font-weight:700; color:#111111; margin-top:4px;">AI Auth Showcase</div>
        <div style="font-size:11px; color:#787878; margin-top:2px;">OBO · M2M · UC · MCP · Governance</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Identity card
    _email_display = ctx.get("email", "Unknown")
    _persona_display = ctx.get("persona", "Unknown")
    _groups_display = ctx.get("authz_groups", [])

    _group_chips = "".join([
        f'<span style="background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;'
        f'padding:2px 8px;border-radius:6px;font-size:11px;margin:2px 2px;display:inline-block;">'
        f'{g}</span>'
        for g in _groups_display
    ]) if _groups_display else '<span style="color:#787878;font-size:12px;">No authz_showcase_* groups</span>'

    st.markdown(f"""
    <div style="
        background: #ffffff;
        border: 1px solid #e0ddd8;
        border-left: 3px solid #cc3311;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    ">
        <div style="font-size:10px; color:#787878; text-transform:uppercase; letter-spacing:1.2px; margin-bottom:6px;">Authenticated As</div>
        <div style="font-size:15px; font-weight:600; color:#111111; margin-bottom:4px; word-break:break-all;">{_email_display}</div>
        <div style="font-size:11px; color:#555555; margin-bottom:10px;">Persona: <span style="color:#111111; font-weight:500;">{_persona_display}</span></div>
        <div style="font-size:10px; color:#787878; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Groups</div>
        <div style="line-height:1.8;">{_group_chips}</div>
    </div>
    """, unsafe_allow_html=True)

    if not _groups_display:
        st.warning("Not in any `authz_showcase_*` group")

    st.markdown("""
    <div style="font-size:10px; color:#787878; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">Auth Method</div>
    """, unsafe_allow_html=True)
    st.markdown(
        '<span class="badge-obo">OBO</span> <span style="color:#555555;font-size:12px;">On-Behalf-Of</span>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Genie queries execute **as you**. "
        "Unity Catalog applies your row filters and column masks."
    )

    st.divider()

    # UC Security status
    _row_filters = ctx.get("row_filters", [])
    _masked_cols = ctx.get("masked_cols", [])

    _rf_items = "".join([f'<li style="color:#555555;font-size:12px;">{f}</li>' for f in _row_filters]) if _row_filters else '<li style="color:#787878;font-size:12px;">none</li>'
    _mc_items = "".join([f'<li style="color:#555555;font-size:12px;">{c}</li>' for c in _masked_cols]) if _masked_cols else '<li style="color:#787878;font-size:12px;">none</li>'

    st.markdown(f"""
    <div style="
        background: #f4f3f0;
        border: 1px solid #e0ddd8;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
    ">
        <div style="font-size:10px; color:#787878; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">UC Security Policies</div>
        <div style="font-size:11px; color:#555555; font-weight:600; margin-bottom:4px;">Active Row Filters</div>
        <ul style="margin:0 0 10px 0; padding-left:16px;">{_rf_items}</ul>
        <div style="font-size:11px; color:#555555; font-weight:600; margin-bottom:4px;">Masked Columns</div>
        <ul style="margin:0; padding-left:16px;">{_mc_items}</ul>
    </div>
    """, unsafe_allow_html=True)

    # ── Demo Controls — Persona Switcher ─────────────────────────────────────
    st.divider()
    st.markdown("""
    <div style="font-size:11px; color:#787878; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Demo Controls</div>
    """, unsafe_allow_html=True)
    st.caption("Run in your terminal, then reload this page.")

    _me = ctx.get("email", "")
    _SCIM_RM  = '{{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{{"op":"remove","path":"members","value":[{{"value":"{uid}"}}]}}]}}'
    _SCIM_ADD = '{{"schemas":["urn:ietf:params:scim:api:messages:2.0:PatchOp"],"Operations":[{{"op":"add","path":"members","value":[{{"value":"{uid}"}}]}}]}}'

    _QUOTA_SQL = {
        "West Rep":  f"DELETE FROM authz_showcase.sales.quota_viewers WHERE user_email = '{_me}';",
        "Manager":   f"INSERT INTO authz_showcase.sales.quota_viewers (user_email, role) SELECT '{_me}', 'manager' WHERE NOT EXISTS (SELECT 1 FROM authz_showcase.sales.quota_viewers WHERE user_email = '{_me}');",
        "Finance":   f"INSERT INTO authz_showcase.sales.quota_viewers (user_email, role) SELECT '{_me}', 'finance' WHERE NOT EXISTS (SELECT 1 FROM authz_showcase.sales.quota_viewers WHERE user_email = '{_me}');",
        "Executive": f"INSERT INTO authz_showcase.sales.quota_viewers (user_email, role) SELECT '{_me}', 'executive' WHERE NOT EXISTS (SELECT 1 FROM authz_showcase.sales.quota_viewers WHERE user_email = '{_me}');",
    }

    for label, (gid, gname, _) in _PERSONA_CONFIG.items():
        is_current = gname in ctx.get("authz_groups", [])
        with st.expander(f"{'✅' if is_current else '▶'} {label}", expanded=False):
            removes = "; \\\n".join(
                f'databricks groups patch {ogid} --profile <YOUR_CLI_PROFILE> --json \'{_SCIM_RM.format(uid=_DEMO_USER_ID)}\' 2>/dev/null || true'
                for ogid, _, _ in _PERSONA_CONFIG.values() if ogid != gid
            )
            add = f'databricks groups patch {gid} --profile <YOUR_CLI_PROFILE> --json \'{_SCIM_ADD.format(uid=_DEMO_USER_ID)}\''
            st.caption("Step 1 — Terminal:")
            st.code(f"{removes}; \\\n{add}", language="bash")
            st.caption(f"Step 2 — [SQL Editor]({host}/sql/editor):")
            st.code(_QUOTA_SQL[label], language="sql")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "💬 Ask Genie", "🔍 Search Knowledge", "⚙️ Business Logic",
    "🔧 Deal Tools", "🤖 Ask Agent", "🌐 External Intel", "🔐 Governance"
])

with tab1:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">Sales Intelligence Assistant</h2></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin-top:8px;margin-bottom:16px;">'
        f'Genie Space <code>{GENIE_SPACE_ID}</code>&nbsp;&nbsp;'
        f'<span class="badge-obo">OBO</span>&nbsp;&nbsp;'
        f'<span style="color:#64748b;font-size:13px;">Answers reflect <strong style="color:#555555;">your</strong> data access, not the app\'s</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conv_id" not in st.session_state:
        st.session_state.conv_id = None

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("SQL generated by Genie"):
                    st.code(msg["sql"], language="sql")

    # Suggested questions (shown only when chat is empty)
    if not st.session_state.messages:
        st.markdown('<div style="color:#555555;font-size:13px;font-weight:600;margin-bottom:10px;">Try asking:</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, q in enumerate(_suggested_questions(ctx.get("authz_groups", []))):
            if cols[i % 2].button(q, key=f"sug_{i}", use_container_width=True):
                st.session_state._pending = q
                st.rerun()

    # Absorb a pending question from suggestion buttons
    question = st.session_state.pop("_pending", None) or st.chat_input(
        "Ask about your sales pipeline..."
    )

    if question:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Genie is thinking…"):
                try:
                    result = genie_ask(question, st.session_state.conv_id)
                    st.session_state.conv_id = result["conversation_id"]

                    if result["status"] == "FAILED":
                        answer = "Sorry, Genie couldn't answer that. Try rephrasing your question."
                        sql = ""
                        st.error(answer)
                    elif result["status"] == "TIMEOUT":
                        answer = "Genie timed out. The warehouse may be starting — please retry."
                        sql = ""
                        st.warning(answer)
                    else:
                        answer = _clean_md(result["text"] or "I found data — see the SQL below for details.")
                        sql = result["sql"]
                        st.markdown(answer)
                        if sql:
                            with st.expander("SQL generated by Genie"):
                                st.code(sql, language="sql")

                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sql": sql}
                    )

                except requests.HTTPError as e:
                    st.error(f"Genie API error: {e.response.status_code} — {e.response.text[:200]}")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

    # Reset conversation
    if st.session_state.messages:
        st.divider()
        if st.button("🔄 New conversation", key="reset"):
            st.session_state.messages = []
            st.session_state.conv_id = None
            st.rerun()

# ── Tab 2: Vector Search (M2M) ────────────────────────────────────────────────

with tab2:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">Knowledge Base Search</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        '<span class="badge-m2m">M2M</span>&nbsp;&nbsp;'
        '<span style="color:#64748b;font-size:13px;">App SP — shared knowledge base, same content for all users</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── SP grant fix (copy-paste if you get a 403) ───────────────────────────
    _sp = os.environ.get("DATABRICKS_CLIENT_ID", "run: databricks apps get authz-showcase | grep service_principal_client_id")
    _grant_sql = f"""-- Run in any SQL editor or notebook if Tab 2 returns 403
GRANT USE CATALOG ON CATALOG authz_showcase        TO `{_sp}`;
GRANT USE SCHEMA  ON SCHEMA  authz_showcase.knowledge_base TO `{_sp}`;
GRANT SELECT      ON TABLE   authz_showcase.knowledge_base.product_docs          TO `{_sp}`;
GRANT SELECT      ON TABLE   authz_showcase.knowledge_base.product_docs_index    TO `{_sp}`;
GRANT SELECT      ON TABLE   authz_showcase.knowledge_base.sales_playbooks       TO `{_sp}`;
GRANT SELECT      ON TABLE   authz_showcase.knowledge_base.sales_playbooks_index TO `{_sp}`;"""
    with st.expander("🔑 SP grants — copy-paste if you get a 403", expanded=False):
        st.code(_grant_sql, language="sql")

    # ── Session state init ────────────────────────────────────────────────────
    for _k, _v in [
        ("vs_query_input", ""),
        ("vs_results", []),
        ("vs_summary", ""),
        ("vs_last_query", ""),
        ("vs_last_kb", "Product Docs"),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # Knowledge base selector
    kb_choice = st.radio(
        "Knowledge base:",
        options=["Product Docs", "Sales Playbooks"],
        horizontal=True,
        key="kb_choice",
    )
    # Clear results when KB changes
    if st.session_state.vs_last_kb != kb_choice:
        st.session_state.vs_results = []
        st.session_state.vs_summary = ""
        st.session_state.vs_last_query = ""
        st.session_state.vs_last_kb = kb_choice

    active_index     = VS_INDEX if kb_choice == "Product Docs" else VS_INDEX_PB
    active_suggested = VS_SUGGESTED if kb_choice == "Product Docs" else PB_SUGGESTED

    # Suggested queries — use on_click callbacks to avoid st.rerun() tab-jump
    st.markdown('<div style="color:#555555;font-size:13px;font-weight:600;margin-bottom:10px;">Suggested searches:</div>', unsafe_allow_html=True)
    sug_cols = st.columns(len(active_suggested))
    for i, sq in enumerate(active_suggested):
        sug_cols[i].button(
            sq,
            key=f"vs_sug_{kb_choice}_{i}",
            use_container_width=True,
            on_click=lambda q=sq: st.session_state.update({"vs_query_input": q}),
        )

    # Search input bound directly to session state key
    search_query = st.text_input(
        "Search query:",
        placeholder="Type a question or topic …",
        key="vs_query_input",
    )

    col_search, col_clear = st.columns([4, 1])
    run_search = col_search.button("🔍 Search", type="primary", use_container_width=True)
    col_clear.button(
        "✕ Clear",
        use_container_width=True,
        on_click=lambda: st.session_state.update({
            "vs_query_input": "", "vs_results": [],
            "vs_summary": "", "vs_last_query": "",
        }),
    )

    # Run search — store results in session state
    if run_search and search_query.strip():
        with st.spinner("Searching knowledge base …"):
            try:
                st.session_state.vs_results = vs_query(active_index, search_query.strip())
                st.session_state.vs_last_query = search_query.strip()
                st.session_state.vs_summary = ""
            except requests.HTTPError as e:
                st.error(f"Vector Search error: {e.response.status_code} — {e.response.text[:300]}")
                if e.response.status_code == 403:
                    st.warning("App SP is missing UC grants. Run the SQL below, then retry:")
                    st.code(_grant_sql, language="sql")
                st.session_state.vs_results = []
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.session_state.vs_results = []

    # Display results from session state (persists across reruns)
    if st.session_state.vs_results:
        results = st.session_state.vs_results
        st.markdown(f'<div style="color:#555555;font-size:13px;margin:16px 0 8px;"><strong style="color:#111111;">{len(results)}</strong> result(s) for: <code>{st.session_state.vs_last_query}</code></div>', unsafe_allow_html=True)
        st.divider()

        for row in results:
            title   = row.get("title", "—")
            badge   = row.get("category") or row.get("audience", "")
            content = row.get("content", "")
            snippet = (content[:350] + " …") if len(content) > 350 else content
            with st.container(border=True):
                header_cols = st.columns([5, 1])
                header_cols[0].markdown(f"**{title}**")
                if badge:
                    header_cols[1].markdown(
                        f"<span style='background:#1d4ed8;color:white;padding:2px 8px;"
                        f"border-radius:4px;font-size:0.75rem'>{badge}</span>",
                        unsafe_allow_html=True,
                    )
                st.markdown(snippet)

        # FM Summarization — only run once per search, cache in session state
        st.divider()
        if not st.session_state.vs_summary:
            with st.spinner("Generating AI summary …"):
                try:
                    context_text = "\n\n".join(
                        f"[{r.get('title', '')}]\n{r.get('content', '')}"
                        for r in results
                    )
                    st.session_state.vs_summary = fm_summarize(
                        context_text, st.session_state.vs_last_query
                    )
                except requests.HTTPError as e:
                    st.session_state.vs_summary = f"_FM unavailable: {e.response.status_code}_"
                except Exception as e:
                    st.session_state.vs_summary = f"_FM error: {e}_"

        st.markdown("""
        <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">AI Summary</div>
        """, unsafe_allow_html=True)
        st.info(st.session_state.vs_summary)
        st.caption(
            f"Summarized via `{FM_ENDPOINT}` using **M2M** auth "
            "(app SP token — no user context passed to FM API)"
        )
    elif run_search:
        st.warning("No results found. Try a different query.")

# ── Tab 3: UC Functions (M2M) ─────────────────────────────────────────────────

with tab3:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">Business Logic Functions</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        '<span class="badge-m2m">M2M</span>&nbsp;&nbsp;'
        '<span style="color:#64748b;font-size:13px;">App SP · quota enforced by <code>mask_quota</code> column mask via <code>current_user()</code> → <code>quota_viewers</code> lookup</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    user_email = ctx.get("email", "")
    persona    = ctx.get("persona", "Unknown")
    is_manager = any(g in ("authz_showcase_managers", "authz_showcase_finance",
                            "authz_showcase_executives")
                     for g in ctx.get("authz_groups", []))

    # ── SP permission fix (copy-paste if you see PermissionDenied) ────────────
    _sp3 = os.environ.get("DATABRICKS_CLIENT_ID", "<SP_UUID>")
    _wh_grant = (
        f"# Run once after any app deploy/reset if you see\n"
        f"# 'PermissionDenied: You do not have permission to use the SQL Warehouse'\n"
        f"databricks permissions update warehouses {SQL_WAREHOUSE} \\\n"
        f"  --profile <YOUR_CLI_PROFILE> \\\n"
        f"  --json '{{\"access_control_list\": [{{\"service_principal_name\": \"{_sp3}\", \"permission_level\": \"CAN_USE\"}}]}}'"
    )
    _uc_grant3 = (
        f"-- Run in SQL editor if UC function calls fail\n"
        f"GRANT USE CATALOG ON CATALOG authz_showcase               TO `{_sp3}`;\n"
        f"GRANT USE SCHEMA  ON SCHEMA  authz_showcase.functions      TO `{_sp3}`;\n"
        f"GRANT USE SCHEMA  ON SCHEMA  authz_showcase.sales          TO `{_sp3}`;\n"
        f"GRANT EXECUTE ON FUNCTION authz_showcase.functions.get_rep_quota         TO `{_sp3}`;\n"
        f"GRANT EXECUTE ON FUNCTION authz_showcase.functions.calculate_attainment  TO `{_sp3}`;\n"
        f"GRANT EXECUTE ON FUNCTION authz_showcase.functions.recommend_next_action TO `{_sp3}`;\n"
        f"GRANT SELECT ON TABLE authz_showcase.sales.opportunities   TO `{_sp3}`;\n"
        f"GRANT SELECT ON TABLE authz_showcase.sales.sales_reps      TO `{_sp3}`;"
    )
    with st.expander("🔑 SP permissions — copy-paste if you see PermissionDenied", expanded=False):
        st.markdown("**Step 1 — Warehouse access** (CLI — run after any app deploy/reset):")
        st.code(_wh_grant, language="bash")
        st.markdown("**Step 2 — UC object grants** (run in any SQL editor or notebook):")
        st.code(_uc_grant3, language="sql")

    # ── Session state init ────────────────────────────────────────────────────
    for _k, _v in [
        ("fn_quota",       None),
        ("fn_attainment",  None),
        ("fn_opps",        []),
        ("fn_next_action", None),
        ("fn_opp_id",      ""),
        ("fn_loaded",      False),
    ]:
        if _k not in st.session_state:
            st.session_state[_k] = _v

    # ── Story ─────────────────────────────────────────────────────────────────
    st.markdown("""
A sales manager opens a dashboard and wants to see **quota, attainment, and a recommended
next action** for every rep on their team. A rep opens the same app and should only see
their own numbers — and should never be able to look up a peer's quota.

You could enforce this in the app layer. But then every app, notebook, and API call needs
its own access control logic. The Databricks approach: **register the business logic as
Unity Catalog functions**. The rules live in the data layer — once — and apply everywhere.

Three functions, three different access patterns:
- **`get_rep_quota`** — quota is privileged. A **column mask** on `sales_reps.quota`
  (enforced by the UC engine) returns NULL for reps at every access path — this function,
  Genie, direct SQL, Agent Bricks. The function body is just `SELECT quota FROM sales_reps`.
- **`calculate_attainment`** — open to all callers, but the **row filter** on `opportunities`
  ensures a rep can only compute attainment over rows they can see.
- **`recommend_next_action`** — pure business logic, no sensitive data, available to everyone.

The app calls all three as the **app SP (M2M)** — not as you. The SP is a member of
`authz_showcase_executives`, so `mask_quota`'s `is_member()` check passes and quota values are
visible. Your role as a viewer only affects what the SP is *asked to compute for* (your email),
not what the SP is *allowed to see*.
The quota restriction is enforced by the `mask_quota` column mask — which uses `is_member()` —
making it ideal for M2M contexts where the executing SP's group membership is explicitly controlled.
    """)
    st.divider()

    # ── Auth explanation box ──────────────────────────────────────────────────
    with st.expander("🔑 How auth works on this tab", expanded=False):
        st.markdown(f"""
**The app calls all three UC functions as the app SP (M2M) — not as you.**

The SP's `current_user()` identity in SQL is its application UUID (`{SP_CLIENT_ID}`).
The SP is in `authz_showcase_executives` → `mask_quota`'s `is_member()` check passes → quota visible.

| Function | SP sees | You (OBO) would see | Why the difference |
|---|---|---|---|
| `get_rep_quota` | ✅ quota value | ❌ `null` | `mask_quota` uses `is_member('authz_showcase_executives')`. SP is in the group; you ({persona}) are not → NULL. Enforced at every UC access path. |
| `calculate_attainment` | ✅ your attainment | ✅ same value | Same data — row filter + WHERE both resolve to your own opps |
| `recommend_next_action` | ✅ recommendation | ✅ same value | No access gate — open to all |

**Why does attainment look the same for OBO vs M2M (when it's your own email)?**

The row filter on `opportunities` passes via two different paths but reaches the same rows:
- SP (exec): `is_member('authz_showcase_executives')` = ✅ → all rows visible → `WHERE rep_email = '{user_email}'`
- You (rep): `is_member(...)` = ❌ → falls through to `opp_rep_email = current_user()` = '{user_email}' → same rows

**The real M2M advantage shows when the SP computes a peer's attainment** — a rep calling OBO
gets `0.00%` (row filter blocks the peer's rows), the SP gets the real number.
See the terminal demo below.
        """)

    # ── Terminal demo commands ────────────────────────────────────────────────
    with st.expander("🖥️ Try it from your terminal", expanded=False):
        st.markdown(
            "Compare **OBO** vs **M2M** — same UC function, different identity, different result. "
            "Open two terminal windows and run:"
        )

        st.markdown(f"**Window 1 — As yourself (`{user_email}`) · OBO · your CLI credentials:**")
        st.code(
            f"python3 - << 'EOF'\n"
            f"from databricks.sdk import WorkspaceClient\n"
            f"\n"
            f"w = WorkspaceClient(profile='<YOUR_CLI_PROFILE>')  # your user credentials\n"
            f"\n"
            f"# Auto-discover a serverless SQL warehouse\n"
            f"wh = next((w.id for w in w.warehouses.list() if w.enable_serverless_compute),\n"
            f"          next((wh.id for wh in w.warehouses.list()), None))\n"
            f"\n"
            f"resp = w.statement_execution.execute_statement(\n"
            f"    warehouse_id=wh,\n"
            f"    statement=\"SELECT {UC_FUNCTIONS_CATALOG}.functions.get_rep_quota('{user_email}')\",\n"
            f"    wait_timeout='30s',\n"
            f")\n"
            f"rows = resp.result.data_array if resp.result and resp.result.data_array else []\n"
            f"print('Result:', rows[0][0] if rows else 'null')\n"
            f"EOF",
            language="bash",
        )
        st.caption(
            f"Expected: `null` — you are `{persona}`, not listed in `quota_viewers` → mask returns NULL"
        )

        st.divider()
        st.markdown("**Window 2 — As the app SP · M2M · self-contained (no env vars):**")
        st.caption(
            "Uses your CLI profile to generate an SP secret inline — secret is used directly "
            "and never stored in env. Run `seed/cleanup_sp_secrets.py` after the demo."
        )
        st.code(
            f"python3 - << 'EOF'\n"
            f"import requests\n"
            f"from databricks.sdk import WorkspaceClient\n"
            f"\n"
            f"# Bootstrap: use your CLI credentials to generate a fresh SP secret\n"
            f"me = WorkspaceClient(profile='<YOUR_CLI_PROFILE>')\n"
            f"r  = requests.post(\n"
            f"    f\"{{me.config.host}}/api/2.0/accounts/servicePrincipals/{SP_NUMERIC_ID}/credentials/secrets\",\n"
            f"    headers={{**me.config.authenticate(), 'Content-Type': 'application/json'}},\n"
            f")\n"
            f"if r.status_code != 200:\n"
            f"    print('Secret generation failed:', r.json())\n"
            f"    print('Quota hit? Run: python3 seed/cleanup_sp_secrets.py --profile <YOUR_CLI_PROFILE>')\n"
            f"    exit(1)\n"
            f"sp_secret = r.json()['secret']\n"
            f"\n"
            f"# Create SP client directly — no env vars needed\n"
            f"sp = WorkspaceClient(\n"
            f"    host=me.config.host,\n"
            f"    client_id='{SP_CLIENT_ID}',\n"
            f"    client_secret=sp_secret,\n"
            f")\n"
            f"\n"
            f"# Auto-discover a serverless SQL warehouse\n"
            f"wh = next((w.id for w in sp.warehouses.list() if w.enable_serverless_compute),\n"
            f"          next((w.id for w in sp.warehouses.list()), None))\n"
            f"\n"
            f"def run(sql):\n"
            f"    r = sp.statement_execution.execute_statement(\n"
            f"        warehouse_id=wh, statement=sql, wait_timeout='30s')\n"
            f"    rows = r.result.data_array if r.result and r.result.data_array else []\n"
            f"    return rows[0][0] if rows else 'null'\n"
            f"\n"
            f"email = '{user_email}'\n"
            f"print('quota:      $', run(f\"SELECT {UC_FUNCTIONS_CATALOG}.functions.get_rep_quota('{{email}}')\" ))\n"
            f"print('attainment:  ', str(run(f\"SELECT {UC_FUNCTIONS_CATALOG}.functions.calculate_attainment('{{email}}')\" )) + '%')\n"
            f"EOF",
            language="bash",
        )
        st.caption(
            f"Expected: quota = `150000.00` (SP is exec) · attainment = same as Window 1 "
            f"(both resolve to `{user_email}`'s own opps — difference shows with a peer below)"
        )

        st.divider()
        st.markdown("**The aha moment — peer attainment (only M2M gets the real number):**")
        st.info(
            "A West Rep calling `calculate_attainment('alice.chen@showcase.demo')` as OBO "
            "gets `0.00%` — the row filter blocks alice's opportunities. "
            "The SP (exec) gets alice's real attainment."
        )
        st.code(
            f"python3 - << 'EOF'\n"
            f"import requests\n"
            f"from databricks.sdk import WorkspaceClient\n"
            f"\n"
            f"me  = WorkspaceClient(profile='<YOUR_CLI_PROFILE>')\n"
            f"obo = me  # your credentials (OBO)\n"
            f"\n"
            f"# Generate SP secret inline\n"
            f"r = requests.post(\n"
            f"    f\"{{me.config.host}}/api/2.0/accounts/servicePrincipals/{SP_NUMERIC_ID}/credentials/secrets\",\n"
            f"    headers={{**me.config.authenticate(), 'Content-Type': 'application/json'}},\n"
            f")\n"
            f"if r.status_code != 200:\n"
            f"    print('Secret generation failed:', r.json())\n"
            f"    print('Quota hit? Run: python3 seed/cleanup_sp_secrets.py --profile <YOUR_CLI_PROFILE>')\n"
            f"    exit(1)\n"
            f"sp = WorkspaceClient(host=me.config.host,\n"
            f"                     client_id='{SP_CLIENT_ID}',\n"
            f"                     client_secret=r.json()['secret'])\n"
            f"\n"
            f"wh = next((w.id for w in sp.warehouses.list() if w.enable_serverless_compute),\n"
            f"          next((w.id for w in sp.warehouses.list()), None))\n"
            f"\n"
            f"def run(client, email):\n"
            f"    resp = client.statement_execution.execute_statement(\n"
            f"        warehouse_id=wh,\n"
            f"        statement=f\"SELECT {UC_FUNCTIONS_CATALOG}.functions.calculate_attainment('{{email}}') \",\n"
            f"        wait_timeout='30s')\n"
            f"    rows = resp.result.data_array if resp.result and resp.result.data_array else []\n"
            f"    return rows[0][0] if rows else 'null'\n"
            f"\n"
            f"peer = 'alice.chen@showcase.demo'\n"
            f"print('OBO (West Rep):', str(run(obo, peer)) + '%')  # → 0.00%  (row filter blocks peer)\n"
            f"print('M2M (SP exec): ', str(run(sp,  peer)) + '%')  # → 76.67% (exec bypasses row filter)\n"
            f"EOF",
            language="bash",
        )

    # ── Load data button ──────────────────────────────────────────────────────
    col_load, col_reset = st.columns([3, 1])
    if col_load.button("⚙️ Load my business metrics", type="primary",
                       use_container_width=True, key="fn_load_btn"):
        with st.spinner("Calling UC functions …"):
            try:
                st.session_state.fn_quota      = uc_get_quota(user_email)
                st.session_state.fn_attainment = uc_get_attainment(user_email)
                st.session_state.fn_opps       = uc_get_opportunities(user_email)
                st.session_state.fn_next_action = None
                st.session_state.fn_opp_id     = ""
                st.session_state.fn_loaded     = True
            except _SdkPermissionDenied as e:
                st.error(f"PermissionDenied: {e}")
                st.warning("App SP is missing warehouse or UC permissions. Run the grants below, then retry:")
                st.markdown("**Warehouse access** (CLI):")
                st.code(_wh_grant, language="bash")
                st.markdown("**UC grants** (SQL editor):")
                st.code(_uc_grant3, language="sql")

    col_reset.button("↺ Reset", use_container_width=True, key="fn_reset_btn",
                     on_click=lambda: st.session_state.update({
                         "fn_quota": None, "fn_attainment": None,
                         "fn_opps": [], "fn_next_action": None,
                         "fn_opp_id": "", "fn_loaded": False,
                     }))

    # ── Results ───────────────────────────────────────────────────────────────
    if st.session_state.fn_loaded:
        st.divider()

        # Metric row
        m1, m2, m3 = st.columns(3)
        m1.metric(
            label="Q1 Quota",
            value=st.session_state.fn_quota or "N/A (rep)",
            help="`get_rep_quota` — NULL for reps; visible to managers/finance/exec",
        )
        m2.metric(
            label="Attainment",
            value=st.session_state.fn_attainment or "—",
            help="`calculate_attainment` — closed-won / quota × 100",
        )
        m3.metric(
            label="Open Opportunities",
            value=len([o for o in st.session_state.fn_opps
                       if o.get("stage") not in ("CLOSED_WON", "CLOSED_LOST")]),
            help="Live count from `opportunities` table (row filter applied)",
        )

        # Auth label under metrics
        if is_manager:
            st.success(
                f"✅ You are **{persona}** — `mask_quota` passes because your role is in `authz_showcase_managers`, "
                f"`authz_showcase_finance`, or `authz_showcase_executives`. The app SP also gets the value "
                f"because it is explicitly added to `authz_showcase_executives`."
            )
        else:
            st.warning(
                f"⚠️ You are **{persona}** — `mask_quota` returns NULL for you because you are not in "
                f"`authz_showcase_managers`, `authz_showcase_finance`, or `authz_showcase_executives`.\n\n"
                f"The app SP **does** get the quota value (it is in `authz_showcase_executives`), which is why "
                f"quota appears above. This is the M2M pattern: the SP's group membership is explicitly "
                f"controlled so it can fetch privileged data on behalf of the app — your personal access is separate."
            )

        # Opportunities table + next action
        if st.session_state.fn_opps:
            st.divider()
            st.markdown(f'<div style="color:#555555;font-size:13px;font-weight:600;margin-bottom:8px;">Your Opportunities <span style="color:#64748b;">({len(st.session_state.fn_opps)} rows)</span></div>', unsafe_allow_html=True)

            for opp in st.session_state.fn_opps:
                opp_id    = opp.get("opp_id", "")
                stage     = opp.get("stage", "—")
                amount    = opp.get("amount", "—")
                cust      = opp.get("customer_id", "—")
                close_dt  = opp.get("close_date", "—")

                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 2, 1, 2])
                    c1.markdown(f"**{opp_id}** · {cust}")
                    c2.markdown(f"`{stage}`")
                    c3.markdown(f"${float(amount):,.0f}" if amount and amount != "—" else "—")
                    if c4.button("💡 Next action", key=f"na_{opp_id}",
                                 use_container_width=True):
                        with st.spinner(f"Calling recommend_next_action('{opp_id}') …"):
                            st.session_state.fn_next_action = uc_get_next_action(opp_id)
                            st.session_state.fn_opp_id = opp_id

            # Show next action result
            if st.session_state.fn_next_action:
                st.divider()
                st.markdown(f"#### 💡 Recommended next action for `{st.session_state.fn_opp_id}`")
                st.info(st.session_state.fn_next_action)
                st.markdown(
                    f'<span style="color:#64748b;font-size:12px;"><code>{UC_FUNCTIONS_CATALOG}.functions.recommend_next_action</code>&nbsp;&nbsp;</span>'
                    f'<span class="badge-m2m">M2M</span>',
                    unsafe_allow_html=True,
                )

# ── Tab 4: Custom MCP — Deal Approval Tools ───────────────────────────────────

import json as _json


def _parse_mcp_response(r) -> dict:
    """Parse an MCP response that may be plain JSON or an SSE stream.

    FastMCP streamable-http returns text/event-stream when the Accept header
    includes it.  Each SSE message is a 'data: <json>' line; we extract the
    first complete JSON-RPC envelope from that stream.
    """
    ct = r.headers.get("Content-Type", "")
    if "text/event-stream" in ct:
        for line in r.text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload and payload != "[DONE]":
                    try:
                        return _json.loads(payload)
                    except Exception:
                        continue
        return {}
    return r.json()


def _mcp_call(tool: str, args: dict, token: str | None, mcp_url: str) -> dict:
    """Single JSON-RPC tool call to the custom MCP server (streamable-http).

    Sends an MCP initialize + tools/call sequence.  The bearer token
    determines the execution identity at the custom MCP layer:
      - user OBO token  → tools execute as the calling user (row filters fire)
      - SP M2M token    → tools execute as the app SP (sees all data)
    """
    span_ctx = mlflow.start_span(name="app_a.mcp_call") if _TRACING_ENABLED else None
    try:
        if span_ctx:
            span = span_ctx.__enter__()
            span.set_inputs({"tool": tool, "args": args, "token": "[REDACTED]" if token else None, "mcp_url": mcp_url})
            client_request_id = str(uuid.uuid4())
            mlflow.update_current_trace(
                client_request_id=client_request_id,
                tags={"service_name": "app-a-frontend", "tool": tool,
                      "entry_point": "tab4_custom_mcp"},
            )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        init_payload = {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "authz-showcase-app", "version": "1.0"},
            },
        }
        init_r = requests.post(mcp_url, json=init_payload, headers=headers, timeout=15)
        # FastMCP streamable-http returns Mcp-Session-Id; subsequent calls must echo it back
        session_id = init_r.headers.get("Mcp-Session-Id", "")
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        call_payload = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }
        r = requests.post(mcp_url, json=call_payload, headers=headers, timeout=30)
        r.raise_for_status()
        resp = _parse_mcp_response(r)
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message", str(resp["error"])))
        content = resp.get("result", {}).get("content", [])
        result = {}
        if content and isinstance(content, list) and content[0].get("type") == "text":
            import json as _json
            try:
                result = _json.loads(content[0]["text"])
            except Exception:
                result = {"raw": content[0]["text"]}
        else:
            result = resp.get("result", {})

        if span_ctx:
            span.set_outputs(result)
        return result
    except Exception:
        if span_ctx:
            span.set_status("ERROR")
        raise
    finally:
        if span_ctx:
            span_ctx.__exit__(None, None, None)


with tab4:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">Deal Approval Tools</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        'Custom MCP server <code>authz-showcase-custom-mcp</code>&nbsp;&nbsp;'
        '<span class="badge-obo">OBO</span> <span style="color:#64748b;font-size:12px;">tools run as you</span>&nbsp;&nbsp;'
        '<span class="badge-m2m">M2M</span> <span style="color:#64748b;font-size:12px;">tool runs as app SP</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    email4  = ctx.get("email", "")
    groups4 = ", ".join(ctx.get("authz_groups", [])) or "none"
    st.info(f"👤 {email4} · Groups: {groups4}")

    with st.expander("🔑 How auth works on this tab", expanded=False):
        st.markdown("""
| Tool | Auth | Access scope |
|---|---|---|
| `get_deal_approval_status` | **OBO identity + M2M SQL** | Only your deals (reps) / all deals (managers+) |
| `submit_deal_for_approval` | **OBO identity + M2M SQL** | Approval record stamped with your verified identity |
| `get_crm_sync_status` | **M2M** | All customers (SP has full access) |

**OBO identity + M2M SQL pattern**: The `X-Forwarded-Access-Token` injected by Databricks Apps is an OIDC
identity token — it does not carry the `sql` scope required by the Statement Execution API. Instead:
1. **OBO** calls `current_user.me()` on the identity token → verified caller email (unforgeable)
2. **M2M** executes SQL with an explicit `WHERE rep_email = '{caller}'` clause, mirroring the UC row filter
3. Approval records are permanently **stamped with the OBO-verified identity** for full auditability

**Why the split?** Deal approval is an audited action — the record must carry the submitter's identity.
CRM sync is a system query — user identity is irrelevant.

The custom MCP server at `authz-showcase-custom-mcp` reads the user token from
`X-Forwarded-Access-Token` (injected by the Databricks Apps proxy) for OBO tools, and uses
`WorkspaceClient()` (M2M app SP) for system tools. The user's identity travels end-to-end:
app → MCP server → Unity Catalog row filters.
""")

    if not CUSTOM_MCP_URL:
        st.warning(
            "⚠️ `CUSTOM_MCP_URL` is not configured. "
            "Add `CUSTOM_MCP_URL=https://authz-showcase-custom-mcp-*.azuredatabricksapps.com/mcp` "
            "to `app.yaml` env section."
        )
    else:
        mcp_base = CUSTOM_MCP_URL.rstrip("/")

        st.markdown('<div class="tab-section-header" style="border-color:#00A4EF;margin-top:16px;"><h3 style="margin:0;font-size:1.1rem;">Tool 1 & 2 — Deal Approval</h3></div>', unsafe_allow_html=True)
        st.markdown('<span class="badge-obo">OBO</span>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            t4_opp = st.text_input("Opportunity ID", value="opp_001", key="t4_opp")
        with col_b:
            t4_justification = st.text_input(
                "Justification (for submit)", value="Strategic enterprise deal — Q1 close",
                key="t4_just"
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔍 Check Approval Status", key="t4_check"):
                with st.spinner("Calling get_deal_approval_status …"):
                    try:
                        result = _mcp_call(
                            "get_deal_approval_status", {"opp_id": t4_opp},
                            user_token, mcp_base
                        )
                        st.code(json.dumps(result, indent=2), language="json")
                    except Exception as e:
                        st.error(f"Error: {e}")
        with c2:
            if st.button("📤 Submit for Approval", key="t4_submit"):
                with st.spinner("Calling submit_deal_for_approval …"):
                    try:
                        result = _mcp_call(
                            "submit_deal_for_approval",
                            {"opp_id": t4_opp, "justification": t4_justification},
                            user_token, mcp_base
                        )
                        st.code(json.dumps(result, indent=2), language="json")
                    except Exception as e:
                        st.error(f"Error: {e}")

        st.divider()
        st.markdown('<div class="tab-section-header" style="border-color:#00A4EF;margin-top:4px;"><h3 style="margin:0;font-size:1.1rem;">Tool 3 — CRM Sync Status</h3></div>', unsafe_allow_html=True)
        st.markdown('<span class="badge-m2m">M2M</span>', unsafe_allow_html=True)
        t4_cust = st.text_input("Customer ID", value="cust_001", key="t4_cust")
        if st.button("📡 Get CRM Sync Status", key="t4_crm"):
            # M2M tool: proxy still requires a valid token; pass user_token to
            # authenticate the request. The MCP server ignores caller identity
            # for this tool and uses the app SP (M2M) credentials directly.
            with st.spinner("Calling get_crm_sync_status …"):
                try:
                    result = _mcp_call(
                        "get_crm_sync_status", {"customer_id": t4_cust},
                        user_token, mcp_base
                    )
                    st.code(json.dumps(result, indent=2), language="json")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        st.markdown('<div class="tab-section-header" style="border-color:#14b8a6;margin-top:4px;"><h3 style="margin:0;font-size:1.1rem;">Auth Trace — How did this request get here?</h3></div>', unsafe_allow_html=True)
        st.markdown(
            '<span style="color:#64748b;font-size:12px;">Calls <code>debug_auth_context</code> on the MCP server to trace the full proxy chain, '
            'identity headers, and SQL execution path. Great for demos.</span>',
            unsafe_allow_html=True,
        )
        if st.button("🔍 Trace Auth Chain (direct call)", key="t4_auth_trace"):
            with st.spinner("Tracing auth chain via direct MCP call …"):
                try:
                    result = _mcp_call(
                        "debug_auth_context", {"call_source": "direct"},
                        user_token, mcp_base
                    )
                    st.code(json.dumps(result, indent=2), language="json")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        with st.expander("🔎 Debug: token scopes (troubleshooting OBO)", expanded=False):
            st.markdown(
                "Compares the **main app token** (what `app.py` holds) vs the "
                "**custom MCP token** (what the MCP server's proxy injects). "
                "If the main app token has `sql` but the MCP token doesn't, "
                "the platform is stripping scopes during app-to-app forwarding."
            )
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown("**Main app token** (decoded locally)")
                if user_token:
                    import base64 as _b64, json as _json2
                    try:
                        _parts = user_token.split(".")
                        _claims = _json2.loads(_b64.urlsafe_b64decode(_parts[1] + "=="))
                        st.code(json.dumps({
                            "scope": _claims.get("scp", _claims.get("scope", "NOT_FOUND")),
                            "sub":   _claims.get("sub", ""),
                            "aud":   _claims.get("aud", ""),
                            "token_prefix": user_token[:30],
                        }, indent=2), language="json")
                    except Exception as _e:
                        st.error(f"Decode error: {_e}")
                else:
                    st.warning("No user token available")
            with col_d2:
                st.markdown("**Custom MCP token** (via `debug_token_scopes` tool)")
                if st.button("Call debug_token_scopes", key="t4_debug"):
                    with st.spinner("Calling MCP server …"):
                        try:
                            result = _mcp_call(
                                "debug_token_scopes", {},
                                user_token, mcp_base
                            )
                            st.code(json.dumps(result, indent=2), language="json")
                        except Exception as e:
                            st.error(f"Error: {e}")


# ── Tab 5: Supervisor Agent (OBO) ─────────────────────────────────────────────

with tab5:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">Multi-Agent Supervisor</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        '<span class="badge-obo">OBO</span>&nbsp;&nbsp;'
        '<span style="color:#64748b;font-size:13px;">Supervisor routes to sub-agents, each enforces your permissions</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    email  = ctx.get("email", "")
    groups = ", ".join(ctx.get("authz_groups", [])) or "none"

    st.info(f"👤 {email} · Groups: {groups}")

    # Auth explanation expander
    with st.expander("🔑 How auth works — supervisor + sub-agents", expanded=False):
        st.markdown(f"""
The **Agent Bricks supervisor** is a Model Serving endpoint. The app calls it with your
OBO token (`X-Forwarded-Access-Token`). The supervisor routes your question to one or more
sub-agents — and **your token travels with each sub-agent call**.

| Sub-agent | Control type | Behavior via supervisor OBO |
|---|---|---|
| `genie_sales` (Genie space) | SQL row filter → `current_user()` | ✅ **Enforced** — user sees only their deals, every time |
| `get_quota` (UC Function) | `quota_viewers` table → `current_user()` | ✅ **Enforced** — West Rep gets NULL; Executive gets value (add email to `quota_viewers`) |
| `get_attainment` (UC Function) | SQL row filter → `current_user()` | ✅ **Enforced** — returns only the caller's own attainment |
| `next_action` (UC Function) | None — open to all | ✅ Returns recommendation for any opp ID |

**Why this works end-to-end — the `current_user()` principle:**

All three enforced controls above use `current_user()` in their logic — not `is_member()`.
The Agent Bricks supervisor correctly injects the OBO caller's identity as `current_user()` throughout.

`is_member()` in contrast evaluates against the **SQL execution runtime's group membership**, not the OBO caller's workspace groups. This is why `mask_quota` was redesigned to use a `quota_viewers` table lookup via `current_user()` — so it works everywhere, including here.

**The unified lesson**: Design UC policies around `current_user()` (row filters, `quota_viewers` lookup) — they propagate through all OBO contexts. Keep `is_member()` checks only in M2M contexts (Tab 3) where the executing identity is a known SP with the right group membership.

**Try these to see it in action:**
- `"What deals are in my pipeline?"` → row filter enforced ✅ (switch persona, results change)
- `"What's my Q1 attainment?"` → row filter enforced ✅ (West Rep vs Executive: different rows counted)
- `"What's my Q1 quota?"` → ✅ now works: NULL for West Rep, value for Executive (use Demo Controls to switch)
        """)

    if not SUPERVISOR_ENDPOINT:
        st.warning(
            "⚠️ `SUPERVISOR_ENDPOINT` is not configured. "
            "Create a supervisor agent in the Databricks UI, "
            "then set the endpoint name in `app.yaml` and redeploy."
        )
    else:
        # Suggested queries
        SUPERVISOR_SUGGESTED = [
            "What deals are in my pipeline?",
            "What's my Q1 attainment?",
            "Recommend next action for my biggest deal",
            "What's my Q1 quota?",   # NULL for West Rep, value for Executive (quota_viewers controls this)
        ]

        st.markdown('<div style="color:#555555;font-size:13px;font-weight:600;margin-bottom:10px;">Try asking:</div>', unsafe_allow_html=True)
        sug_cols = st.columns(2)
        for i, sq in enumerate(SUPERVISOR_SUGGESTED):
            sug_cols[i % 2].button(
                sq,
                key=f"sup_sug_{i}",
                use_container_width=True,
                on_click=lambda q=sq: st.session_state.update({"_sup_pending": q}),
            )

        # Session state
        if "supervisor_messages" not in st.session_state:
            st.session_state.supervisor_messages = []

        msgs = st.session_state.supervisor_messages

        # Render history: older exchanges collapsed, latest Q&A always visible
        if len(msgs) > 2:
            older = msgs[:-2]
            with st.expander(f"💬 Previous messages ({len(older)})", expanded=False):
                for msg in older:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

        # Always show the latest exchange (last user + assistant pair)
        for msg in (msgs[-2:] if len(msgs) >= 2 else msgs):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input — absorb pending suggestion or typed question
        question = st.session_state.pop("_sup_pending", None) or st.chat_input(
            "Ask the supervisor agent …", key="sup_chat_input"
        )

        if question:
            st.session_state.supervisor_messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Supervisor is routing your question …"):
                    try:
                        history = st.session_state.supervisor_messages[:-1]
                        answer = _clean_md(supervisor_ask(question, user_token, history))
                        st.markdown(answer)
                        st.session_state.supervisor_messages.append(
                            {"role": "assistant", "content": answer}
                        )
                    except requests.HTTPError as e:
                        err = f"Supervisor API error: {e.response.status_code} — {e.response.text[:300]}"
                        st.error(err)
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")

        # New conversation button
        if msgs:
            st.divider()
            if st.button("🔄 New conversation", key="sup_reset"):
                st.session_state.supervisor_messages = []
                st.rerun()


# ── Tab 6: External MCP via UC HTTP Connection ────────────────────────────────

def _mcp_tool_call(conn_name: str, tool: str, args: dict, token: str | None = None) -> dict:
    """Call an external MCP tool via the UC HTTP Connection proxy.

    token: caller's Databricks token for proxy auth.
      - None (default) → app SP M2M credentials (w_sp) — shared identity
      - user_token     → calling user's token — for per-user OAuth connections (e.g. GitHub)
    The proxy injects the stored credential before forwarding to the external service.
    """
    proxy_url = f"{host}/api/2.0/mcp/external/{conn_name}"
    # Spread all auth headers — on Azure, SP auth may include extra headers beyond Authorization
    auth_headers = {"Authorization": f"Bearer {token}"} if token else w_sp.config.authenticate()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **auth_headers,
    }
    # MCP initialize → get session ID
    init_r = requests.post(
        proxy_url,
        json={
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "authz-showcase-app", "version": "1.0"},
            },
        },
        headers=headers, timeout=15, allow_redirects=False,
    )
    if init_r.status_code in (301, 302, 307, 308):
        # UC proxy redirects to OAuth consent when target is a Databricks App
        consent_url = init_r.headers.get("Location", "")
        raise PermissionError(
            f"OAuth consent required for this connection's target app. "
            f"[Complete consent here]({consent_url}), then retry."
        )
    if not init_r.ok:
        # Include response details for debugging
        auth_type = "SP M2M" if token is None else "user OBO"
        raise RuntimeError(
            f"{init_r.status_code} calling proxy ({auth_type}): "
            f"{init_r.text[:300]}"
        )
    session_id = init_r.headers.get("Mcp-Session-Id", "")
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    # MCP tools/call
    r = requests.post(
        proxy_url,
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        },
        headers=headers, timeout=30, allow_redirects=False,
    )
    r.raise_for_status()
    resp = _parse_mcp_response(r)
    if "error" in resp:
        raise RuntimeError(resp["error"].get("message", str(resp["error"])))
    content = resp.get("result", {}).get("content", [])
    if content and isinstance(content, list) and content[0].get("type") == "text":
        try:
            return _json.loads(content[0]["text"])
        except Exception:
            return {"raw": content[0]["text"]}
    return resp.get("result", {})


def _show_github_error(exc: Exception) -> None:
    """Display a GitHub MCP error with a clickable consent link if credentials are missing."""
    import re
    msg = str(exc)
    # Proxy returns: "Credential for user identity(...) is not found ... visiting https://None/..."
    # Fix the broken consent URL (proxy emits `None` as the host) and surface it as a link.
    if "not found" in msg and ("login" in msg.lower() or "credential" in msg.lower()):
        fixed = re.sub(r"https?://None/", f"{host}/", msg)
        url_match = re.search(r"https?://[^\s\"']+", fixed)
        consent_url = url_match.group(0) if url_match else f"{host}/explore/connections/{GITHUB_CONN}"
        st.warning(
            f"GitHub OAuth consent required for your account. "
            f"[Click here to authorize GitHub access]({consent_url}), then retry."
        )
    else:
        st.error(f"Error: {exc}")


with tab6:
    st.markdown('<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">External Intelligence</h2></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        '<span style="color:#64748b;font-size:13px;">UC HTTP Connections — credentials stored in Unity Catalog, never in app code or env vars</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.expander("🔑 How auth works on this tab", expanded=False):
        st.markdown(f"""
**The UC HTTP Connection is the governance boundary.**
`USE CONNECTION` privilege is the on/off switch — revoke it from the app SP and the tools vanish.

| Connection | Type | Credential stored | Who executes at external service |
|---|---|---|---|
| `{GITHUB_CONN}` | **Managed OAuth** | Per-user GitHub OAuth token (Databricks manages) | Calling user's GitHub identity |
| `{CUSTMCP_CONN}` | **Custom HTTP Bearer** | Shared SP bearer token (stored in UC) | Stored credential authenticates to external service; UC proxy injects calling user's email |

**Why two patterns?**
- GitHub: per-user access — each user's repos, issues, and PRs via Managed OAuth.
- Custom bearer: the stored credential authenticates to the external service, but the UC proxy
  still injects `x-forwarded-email` with the calling user's identity. The MCP server uses M2M
  SQL (because the OBO token via proxy lacks `sql` scope) but reports the real caller's email.

Proxy URL pattern: `{{workspace_host}}/api/2.0/mcp/external/{{connection_name}}`
""")

    # ── Section A: GitHub MCP (Managed OAuth) ────────────────────────────────
    st.markdown('<div class="tab-section-header" style="border-color:#00A4EF;margin-top:8px;"><h3 style="margin:0;font-size:1.1rem;">GitHub MCP</h3></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin:6px 0 12px;">'
        f'<span style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;">Managed OAuth</span>'
        f'&nbsp;&nbsp;<span style="color:#64748b;font-size:12px;">Connection: <code>{GITHUB_CONN}</code> · per-user OAuth — you see your own GitHub repos, issues, PRs</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Setup — Install from Databricks Marketplace", expanded=False):
        st.markdown("""
1. **Workspace → Marketplace → Agents → MCP Servers → GitHub → Install**
2. Connection name: `authz_showcase_github_conn`
3. Credential type: **Managed OAuth** (Databricks handles the PKCE flow per user)
4. First call: if not yet authorized, you'll get a link to complete GitHub OAuth
5. Grant `USE CONNECTION` to the app SP:
   ```sql
   GRANT USE CONNECTION ON CONNECTION authz_showcase_github_conn
     TO `2cbaa395-c62f-4700-8d7d-f61f70238ebb`;
   ```
""")

    gh_subtab1, gh_subtab2 = st.tabs(["List Issues", "Search Repos"])

    with gh_subtab1:
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            gh_owner = st.text_input("Owner", value="databricks", key="gh_owner")
        with col_g2:
            gh_repo  = st.text_input("Repo", value="databricks-sdk-py", key="gh_repo")
        with col_g3:
            gh_state = st.selectbox("State", ["open", "closed", "all"], key="gh_state")
        if st.button("📋 List Issues", key="gh_issues"):
            with st.spinner(f"Calling GitHub list_issues via UC proxy …"):
                try:
                    result = _mcp_tool_call(
                        GITHUB_CONN, "list_issues",
                        {"owner": gh_owner, "repo": gh_repo, "state": gh_state},
                        token=user_token,
                    )
                    with st.expander("📄 Result", expanded=True):
                        st.code(json.dumps(result, indent=2), language="json")
                except Exception as e:
                    _show_github_error(e)

    with gh_subtab2:
        gh_query = st.text_input("Search query", value="databricks mcp", key="gh_search")
        if st.button("🔎 Search GitHub", key="gh_search_btn"):
            with st.spinner("Searching GitHub via UC proxy …"):
                try:
                    result = _mcp_tool_call(
                        GITHUB_CONN, "search_repositories", {"query": gh_query},
                        token=user_token,
                    )
                    with st.expander("📄 Result", expanded=True):
                        st.code(json.dumps(result, indent=2), language="json")
                except Exception as e:
                    _show_github_error(e)

    st.divider()

    # ── Section B: Custom MCP via Bearer Token ────────────────────────────────
    st.markdown('<div class="tab-section-header" style="border-color:#00A4EF;margin-top:4px;"><h3 style="margin:0;font-size:1.1rem;">Custom MCP via Bearer Token</h3></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="margin:6px 0 12px;">'
        f'<span style="background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;">Stored Bearer</span>'
        f'&nbsp;&nbsp;<span style="color:#64748b;font-size:12px;">Connection: <code>{CUSTMCP_CONN}</code> · UC proxy forwards user identity, MCP server uses M2M fallback for SQL</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Setup — Create UC HTTP Connection (bearer token)", expanded=False):
        custom_mcp_host = CUSTOM_MCP_URL.replace("https://", "").split("/")[0] if CUSTOM_MCP_URL else "<app-host>"
        st.markdown(f"""
The same `authz-showcase-custom-mcp` app is connected here as an **external** MCP server
using a UC HTTP Connection with a stored bearer token — demonstrating the Custom HTTP pattern.

```python
# seed/08_create_external_mcp_conn.py
from databricks.sdk.service.catalog import ConnectionType

w.connections.create(
    name="authz_showcase_custmcp_conn",
    connection_type=ConnectionType.HTTP,
    comment="Custom HTTP Bearer — all callers operate as SP through this connection",
    options={{
        "host": "https://{custom_mcp_host}",   # must include https://
        "base_path": "/mcp",
        "bearer_token": "<sp-oauth-m2m-token>",   # stored encrypted in UC
        "is_mcp_connection": "true",
    }},
)
```

**Key contrast with Tab 4 (direct custom MCP call)**:
- Tab 4: app calls custom MCP **directly** with the user's OBO token → tools execute as the user
- Tab 6 (this section): app calls the **UC proxy** → proxy injects stored SP bearer token →
  custom MCP executes as the SP for all callers

`USE CONNECTION` privilege on `authz_showcase_custmcp_conn` is the only access control needed.

> **Note**: When the target external service is a Databricks App, the proxy performs per-user
> OAuth consent before proxying (the App's own OAuth layer takes precedence over the stored
> bearer token). This pattern works without OAuth for truly external APIs (e.g., Jira, GitHub
> Enterprise, internal REST services that accept bearer tokens directly).
""")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        b_opp = st.text_input("Opportunity ID", value="opp_001", key="b_opp")
    with col_b2:
        b_cust = st.text_input("Customer ID", value="cust_001", key="b_cust")

    c_b1, c_b2 = st.columns(2)
    with c_b1:
        if st.button("🔍 Approval Status (via UC proxy)", key="b_check"):
            with st.spinner("Calling via UC HTTP Connection …"):
                try:
                    result = _mcp_tool_call(
                        CUSTMCP_CONN, "get_deal_approval_status", {"opp_id": b_opp},
                        token=user_token,
                    )
                    with st.expander("📄 Result", expanded=True):
                        st.code(json.dumps(result, indent=2), language="json")
                        st.caption(
                            "The UC proxy injects `x-forwarded-email` with the calling user's identity. "
                            "The MCP server uses M2M fallback for SQL (OBO token lacks `sql` scope via proxy) "
                            "but `caller_identity` still shows **your email** from the forwarded headers."
                        )
                except PermissionError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Error: {e}")
    with c_b2:
        if st.button("📡 CRM Status (via UC proxy)", key="b_crm"):
            with st.spinner("Calling via UC HTTP Connection …"):
                try:
                    result = _mcp_tool_call(
                        CUSTMCP_CONN, "get_crm_sync_status", {"customer_id": b_cust},
                        token=user_token,
                    )
                    with st.expander("📄 Result", expanded=True):
                        st.code(json.dumps(result, indent=2), language="json")
                except PermissionError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown(
        '<div class="tab-section-header" style="border-color:#14b8a6;margin-top:16px;">'
        '<h3 style="margin:0;font-size:1.1rem;">Auth Trace — How did this request get here?</h3></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span style="color:#64748b;font-size:12px;">Calls <code>debug_auth_context</code> via the UC External MCP Proxy to trace the full '
        "multi-proxy chain. Compare with Tab 4's trace to see the extra UC proxy hop.</span>",
        unsafe_allow_html=True,
    )
    if st.button("🔍 Trace Auth Chain (via UC proxy)", key="b_auth_trace"):
        with st.spinner("Tracing auth chain via UC External MCP Proxy …"):
            try:
                result = _mcp_tool_call(
                    CUSTMCP_CONN, "debug_auth_context", {"call_source": "uc_proxy"},
                    token=user_token,
                )
                with st.expander("📄 Auth Trace Result", expanded=True):
                    st.code(json.dumps(result, indent=2), language="json")
            except PermissionError as e:
                st.warning(str(e))
            except Exception as e:
                st.error(f"Error: {e}")


# ── Tab 7: UC Connection Governance ───────────────────────────────────────────

with tab7:
    st.markdown(
        '<div class="tab-section-header"><h2 style="margin:0;font-size:1.4rem;">'
        'UC Connection Governance</h2></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="margin-top:8px;margin-bottom:16px;">'
        '<span style="color:#64748b;font-size:13px;">'
        '<code>USE CONNECTION</code> is the on/off switch — '
        'the MCP server needs <strong>zero</strong> scopes or data permissions. '
        'Unity Catalog holds the key to the kingdom.</span></div>',
        unsafe_allow_html=True,
    )

    with st.expander("🔑 How this demo works", expanded=True):
        st.markdown(f"""
**The architecture is simple:**

```
You (admin) ──GRANT/REVOKE──> UC Connection ──USE CONNECTION check──> External Service
```

The Streamlit app's service principal (`{SP_CLIENT_ID[:8]}…`) calls external services
through **UC HTTP Connections**. Before any request reaches the target service, the
UC External MCP Proxy checks whether the **calling identity** has `USE CONNECTION`
on that connection. If not → **403 — the request never leaves the platform.**

**Why this matters for agent security:**

| Concern | How UC addresses it |
|---|---|
| **Confused deputy** | The MCP server is a pure proxy — it doesn't need data grants or elevated scopes to handle proxied calls. Only the *caller* needs `USE CONNECTION`. |
| **Blast radius** | Revoking one `USE CONNECTION` cuts off *all* access through that connection — no per-endpoint or per-tool configuration needed. |
| **Audit trail** | Every call through a UC connection is logged in `system.access.audit` with the caller's identity. |

> **Note:** The custom MCP server's SP *does* have minimal data grants (`SELECT` on two tables,
> warehouse access) — but those exist solely for the M2M SQL tools in Tabs 4 & 6.
> For this governance demo, those grants are irrelevant. The UC proxy path doesn't
> use or inherit the MCP server's data permissions.

**Demo flow for each connection:**
1. Start with no `USE CONNECTION` grant → call fails with 403
2. Run the `GRANT` command → call succeeds
3. Run the `REVOKE` command → call fails again
""")

    app_sp_display = SP_CLIENT_ID or "(SP_CLIENT_ID not set)"

    st.divider()

    # ── Section A: Bearer Token Connection ────────────────────────────────────
    st.markdown(
        '<div class="tab-section-header" style="border-color:#00A4EF;margin-top:4px;">'
        '<h3 style="margin:0;font-size:1.1rem;">Bearer Token Connection</h3></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span style="background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;'
        f'padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;">Bearer</span>'
        f'&nbsp;&nbsp;<span style="color:#64748b;font-size:12px;">'
        f'Connection: <code>{CUSTMCP_CONN}</code> · Custom MCP server</span>',
        unsafe_allow_html=True,
    )

    st.markdown("**Step 1 — Verify no access** (revoke first if needed):")
    st.code(
        f"-- Run in a notebook or SQL editor (as metastore admin / connection owner)\n"
        f"REVOKE USE CONNECTION ON CONNECTION {CUSTMCP_CONN}\n"
        f"  FROM `{app_sp_display}`;",
        language="sql",
    )

    st.markdown("**Step 2 — Test the call** (should fail with 403):")
    if st.button("🔍 Test Bearer MCP (as app SP)", key="t7_bearer_test"):
        with st.spinner("Calling via UC proxy as app SP …"):
            try:
                result = _mcp_tool_call(
                    CUSTMCP_CONN, "debug_auth_context", {"call_source": "uc_proxy"},
                )
                st.success("Call succeeded — app SP has USE CONNECTION")
                st.code(json.dumps(result, indent=2), language="json")
            except PermissionError as e:
                st.warning(str(e))
            except Exception as e:
                err_str = str(e)
                if "401" in err_str:
                    st.error(f"Stored bearer token expired on `{CUSTMCP_CONN}` (~1h TTL)")
                    st.caption(
                        "The UC connection's stored credential has expired. "
                        "Refresh it with: `python3 seed/demo.py --before`"
                    )
                    st.caption(f"Raw error: {err_str[:300]}")
                elif "403" in err_str or "PERMISSION" in err_str.upper():
                    st.error(f"Access denied — app SP lacks USE CONNECTION on `{CUSTMCP_CONN}`")
                    st.caption(f"Raw error: {err_str[:300]}")
                else:
                    st.error(f"Error: {err_str}")

    st.markdown("**Step 2a — If you see 'token expired':**")
    st.code("python3 seed/demo.py --before --profile <YOUR_CLI_PROFILE>", language="bash")
    st.caption("The stored bearer token in the UC connection expires in ~1h. This refreshes it.")

    st.markdown("**Step 3 — Grant access** (if you see 'lacks USE CONNECTION'):")
    st.code(
        f"-- Grant USE CONNECTION to the app SP\n"
        f"GRANT USE CONNECTION ON CONNECTION {CUSTMCP_CONN}\n"
        f"  TO `{app_sp_display}`;",
        language="sql",
    )
    st.markdown("**Step 4 — Test again** (should succeed now). Click the test button above.")

    st.divider()

    # ── Section B: OAuth U2M Per User Connection (GitHub) ─────────────────────
    st.markdown(
        '<div class="tab-section-header" style="border-color:#00A4EF;margin-top:4px;">'
        '<h3 style="margin:0;font-size:1.1rem;">OAuth U2M Per User Connection</h3></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span style="background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;'
        f'padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;">OAuth Per User</span>'
        f'&nbsp;&nbsp;<span style="color:#64748b;font-size:12px;">'
        f'Connection: <code>{GITHUB_CONN}</code> · GitHub (per-user identity)</span>',
        unsafe_allow_html=True,
    )

    user_email_display = ctx.get("email", "(unknown)")

    st.markdown(
        "Unlike Bearer Token connections (shared credential), **Managed OAuth** connections "
        "maintain per-user credentials. Each user must complete OAuth consent with GitHub, "
        "and USE CONNECTION controls who can call through the proxy."
    )

    st.markdown("**Step 1 — Complete GitHub OAuth consent** (one-time):")
    # Extract org ID from workspace host URL (e.g. adb-1234567.3.azuredatabricks.net → 1234567)
    _org_match = re.search(r'adb-(\d+)', host)
    _org_id = _org_match.group(1) if _org_match else ""
    consent_url = f"{host}/explore/connections/{GITHUB_CONN}?o={_org_id}"
    st.markdown(
        f"Visit the [connection page]({consent_url}) and click **Sign in** to authorize "
        f"your GitHub identity. This is a one-time step per user."
    )

    st.markdown(f"**Step 2 — Verify no access** (revoke from `{user_email_display}`):")
    st.code(
        f"-- Revoke from the logged-in user (not the app SP)\n"
        f"REVOKE USE CONNECTION ON CONNECTION {GITHUB_CONN}\n"
        f"  FROM `{user_email_display}`;",
        language="sql",
    )

    st.markdown("**Step 3 — Test the call** (as your user identity via OBO — should fail with 403):")
    if st.button("🔍 Test GitHub MCP (as you)", key="t7_github_test"):
        with st.spinner("Calling GitHub via UC proxy as your identity …"):
            try:
                result = _mcp_tool_call(
                    GITHUB_CONN, "list_issues",
                    {"owner": "databricks", "repo": "databricks-sdk-py", "state": "open"},
                    token=user_token,
                )
                st.success("Call succeeded — your GitHub OAuth consent is active")
                with st.expander("📄 Result", expanded=True):
                    st.code(json.dumps(result, indent=2), language="json")
            except PermissionError as e:
                st.warning(str(e))
            except Exception as e:
                err_str = str(e)
                if "Credential" in err_str and "not found" in err_str:
                    st.error("GitHub OAuth consent not completed for your identity")
                    st.markdown(
                        f"Visit the [connection page]({consent_url}) and click **Sign in** "
                        f"to authorize your GitHub account, then retry."
                    )
                    st.caption(f"Raw error: {err_str[:300]}")
                elif "403" in err_str or "PERMISSION" in err_str.upper():
                    st.error(f"Access denied — you lack USE CONNECTION on `{GITHUB_CONN}`")
                    st.caption(f"Raw error: {err_str[:300]}")
                else:
                    st.error(f"Error: {err_str}")

    st.markdown(f"**Step 4 — Grant access** (to `{user_email_display}`):")
    st.code(
        f"-- Grant to the logged-in user\n"
        f"GRANT USE CONNECTION ON CONNECTION {GITHUB_CONN}\n"
        f"  TO `{user_email_display}`;",
        language="sql",
    )
    st.markdown("**Step 5 — Test again** (should succeed now). Click the test button above.")

    st.markdown(
        "**Key difference**: Bearer Token connections use a single stored credential for all callers. "
        "Managed OAuth connections maintain per-user credentials — the proxy knows *who* is calling GitHub."
    )

    st.divider()

    # ── Key takeaway ──────────────────────────────────────────────────────────
    with st.expander("📌 Key takeaway", expanded=False):
        st.markdown(f"""
**Same governance model, different credentials:**

| Connection | Auth Method | Who authenticates to external service | Governed by |
|---|---|---|---|
| `{CUSTMCP_CONN}` | **Bearer Token** | Stored token (shared identity) | `USE CONNECTION` |
| `{GITHUB_CONN}` | **OAuth U2M Per User** | Each user's GitHub identity | `USE CONNECTION` |

**For UC-proxied calls, the MCP server needs zero data permissions.**
The UC connection governance layer sits *in front of* the MCP server — if `USE CONNECTION`
is revoked, the request never reaches it.

**What controls access:** `USE CONNECTION` on the UC HTTP Connection.
- Revoke it → 403, the request never reaches the external service
- Grant it → the call goes through, using the connection's stored credentials

**The auth method** (Bearer, OAuth M2M, U2M Shared, U2M Per User) determines
*how* the connection authenticates to the external service.
**`USE CONNECTION`** determines *whether* the call is allowed at all.

**Preventing the confused deputy problem:**
The MCP server SP should hold only the minimum grants needed for its own tools
(e.g., `SELECT` on specific tables for M2M SQL in Tabs 4 & 6). For UC-proxied
external calls (this tab), the server acts as a stateless proxy — it inherits
no caller permissions and grants none of its own.
""")
