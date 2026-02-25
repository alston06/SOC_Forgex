import streamlit as st
import os

from modules.auth_store import save_auth, clear_auth, load_auth, LOADING

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

        /* ── Fixed sidebar: always visible, never collapsible ── */
        /* Hide the collapse / expand toggle */
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* Keep sidebar open even when Streamlit sets aria-expanded=false */
        section[data-testid="stSidebar"] {
            min-width: 260px !important;
            max-width: 280px !important;
            width: 280px !important;
            transform: none !important;
            transition: none !important;
        }

        section[data-testid="stSidebar"] > div {
            width: 280px !important;
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
if "_auth_init" not in st.session_state:
    st.session_state._auth_init = False

# ── Clear localStorage when flagged (after logout) ──────
if st.session_state.get("_clear_storage"):
    clear_auth()
    del st.session_state._clear_storage

# ── Auth gate ───────────────────────────────────────────
if not st.session_state.jwt_token:
    # Try restoring from browser localStorage (once per session)
    if not st.session_state._auth_init:
        restored = load_auth()
        if restored is LOADING:
            # JS hasn't responded yet – show a loading splash and wait
            st.markdown(
                "<div style='text-align:center;margin-top:20vh'>"
                "<h2>🛡️ SOC Forgex</h2></div>",
                unsafe_allow_html=True,
            )
            with st.spinner("Restoring session…"):
                st.stop()

        st.session_state._auth_init = True
        token, user = restored
        if token:
            st.session_state.jwt_token = token
            st.session_state.user = user
            st.rerun()

    # No saved credentials – show login page
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
    st.session_state._auth_init = True  # don't try localStorage again
    st.session_state._clear_storage = True
    st.rerun()

# ── Persist auth to localStorage (once after login / register) ──
if st.session_state.get("_save_auth"):
    save_auth(st.session_state.jwt_token, st.session_state.user)
    del st.session_state._save_auth

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
        st.session_state._clear_storage = True
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
