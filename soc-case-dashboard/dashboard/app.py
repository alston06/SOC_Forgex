import streamlit as st
import os

# ── Page config ─────────────────────────────────────────
st.set_page_config(
    page_title="SOC Forgex",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────
st.markdown(
    """
    <style>
        /* Hide default Streamlit chrome */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Tighten padding */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1rem;
        }

        /* Sidebar branding */
        [data-testid="stSidebar"] {
            min-width: 240px;
            max-width: 280px;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border-radius: 8px;
            padding: 12px 16px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Environment ─────────────────────────────────────────
CASE_SERVICE_URL = os.environ.get("CASE_SERVICE_URL", "http://localhost:8004")

# ── Session state ───────────────────────────────────────
if "jwt_token" not in st.session_state:
    st.session_state.jwt_token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_incident_id" not in st.session_state:
    st.session_state.selected_incident_id = None

# ── Auth gate ───────────────────────────────────────────
if not st.session_state.jwt_token:
    from modules.login import render as login_render

    login_render(CASE_SERVICE_URL)
    st.stop()

# ── Authenticated client ────────────────────────────────
from services.dashboard_client import DashboardClient  # noqa: E402

client = DashboardClient(CASE_SERVICE_URL, st.session_state.jwt_token)

# Validate session (token may have expired)
try:
    me = client.get_me()
except Exception:
    st.session_state.jwt_token = None
    st.session_state.user = None
    st.rerun()

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ SOC Forgex")
    org = st.session_state.user.get("organization", "My Org")
    st.caption(f"📁 {org}")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Overview",
            "📋 Incidents",
            "🚨 Alerts",
            "🔑 API Keys",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    username = st.session_state.user.get("username", "")
    st.caption(f"👤 {username}")
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.jwt_token = None
        st.session_state.user = None
        st.rerun()

# ── Page routing ────────────────────────────────────────
from modules import overview, incidents, incident_detail, alerts, api_keys, settings  # noqa: E402

try:
    if "📊 Overview" in page:
        # Clear incident selection when navigating away
        st.session_state.selected_incident_id = None
        overview.render(client)

    elif "📋 Incidents" in page:
        if st.session_state.selected_incident_id:
            incident_detail.render(
                client, st.session_state.selected_incident_id
            )
        else:
            incidents.render(client)

    elif "🚨 Alerts" in page:
        st.session_state.selected_incident_id = None
        alerts.render(client)

    elif "🔑 API Keys" in page:
        st.session_state.selected_incident_id = None
        api_keys.render(client)

    elif "⚙️ Settings" in page:
        st.session_state.selected_incident_id = None
        settings.render(client)

except Exception as e:
    st.error(f"An error occurred: {e}")
