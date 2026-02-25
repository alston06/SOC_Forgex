import streamlit as st
from services.app_client import APIClient
from modules import overview, incidents, alerts, incident_detail, hunting, settings
import sys

st.set_page_config(page_title="SOC Dashboard", layout="wide")

# Initialize session state
if "selected_incident_id" not in st.session_state:
    st.session_state.selected_incident_id = None
if "selected_detection_id" not in st.session_state:
    st.session_state.selected_detection_id = None
if "api_key" not in st.session_state:
    st.session_state.api_key = None
if "base_url" not in st.session_state:
    st.session_state.base_url = "http://localhost:8004"
if "detection_url" not in st.session_state:
    st.session_state.detection_url = "http://localhost:8005"

with st.sidebar:
    st.title("🛡️ SOC Dashboard")
    
    # Collapsible configuration section
    with st.expander("⚙️ Configuration", expanded=False):
        api_key = st.text_input("API Key", type="password", value=st.session_state.api_key or "", key="sidebar_api_key")
        base_url = st.text_input("Case Service URL", value=st.session_state.base_url, key="sidebar_base_url")
        detection_url = st.text_input("Detection Service URL", value=st.session_state.detection_url, key="sidebar_detection_url")
        
        # Store in session state
        st.session_state.api_key = api_key
        st.session_state.base_url = base_url
        st.session_state.detection_url = detection_url
    
    is_authenticated = bool(api_key)
    
    # Status indicator
    if is_authenticated:
        st.success("✓ Authenticated", icon="✅")
    else:
        st.warning("⚠️ Not authenticated")
    
    st.divider()
    
    # Navigation
    st.write("**Navigation**")
    tabs = st.radio(
        "Select page",
        ["Overview", "Alerts", "Incidents", "Incident Detail", "Hunting", "Settings"],
        label_visibility="collapsed",
        key="main_navigation"
    )

# Create client only if authenticated
client = None
if is_authenticated:
    client = APIClient(base_url, api_key, detection_url)

try:
    if not is_authenticated and tabs != "Settings":
        st.info("ℹ️ Configure your API key in the **Settings** tab to enable data fetching")
    
    if tabs == "Overview":
        if is_authenticated and client:
            overview.render(client)
        else:
            st.title("Overview")
            st.subheader("📊 Dashboard Summary")
            st.write("""
            This tab provides a real-time overview of your security posture with key metrics including:
            - **Active Incidents**: Count of open incidents requiring attention
            - **Alerts (Last Hour)**: Recent security detections
            - **MTTA**: Mean time to acknowledge incidents
            - **MTTR**: Mean time to resolve incidents
            - **Severity Distribution**: Breakdown of incidents by severity level
            - **Alerts Trend**: Hourly alert volume over the last 24 hours
            """)
            st.divider()
            st.write("**To view live data:**")
            st.write("1. Go to the **Settings** tab")
            st.write("2. Enter your API key in the sidebar")
            st.write("3. Return to this tab to see metrics")
            
            # Show sample layout
            st.subheader("Sample Layout (with data)")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Active Incidents", "—", delta=None, help="Number of OPEN incidents")
            with col2:
                st.metric("Alerts (Last Hour)", "—", help="Detections in the last 60 minutes")
            with col3:
                st.metric("MTTA (min)", "—", help="Mean time to acknowledge")
            with col4:
                st.metric("MTTR (min)", "—", help="Mean time to resolve")

    elif tabs == "Alerts":
        if is_authenticated and client:
            alerts.render(client)
        else:
            st.title("Alerts")
            st.subheader("🚨 Security Detections")
            st.write("""
            This tab displays security detections from your organization, including:
            - **Rule ID**: Which detection rule triggered
            - **Severity**: Alert severity level (LOW, MEDIUM, HIGH, CRITICAL)
            - **Confidence**: Detection confidence score (0.0-1.0)
            - **Actor**: User or service that triggered the alert
            - **IP**: Source IP address
            - **Service**: Application or service involved
            - **Timestamp**: When the detection occurred
            """)
            st.divider()
            st.write("**Features:**")
            st.write("- ✓ Real-time detection list (last 24 hours by default)")
            st.write("- ✓ Select individual alerts for detailed analysis")
            st.write("- ✓ JSON export of full detection context")
            st.divider()
            st.info("Enter your API key in the sidebar to view live alerts from the detection service.")

    elif tabs == "Incidents":
        if is_authenticated and client:
            incidents.render(client)
        else:
            st.title("Incidents")
            st.subheader("📋 Incident Management")
            st.write("""
            This tab shows all open security incidents with the following information:
            - **ID**: Unique incident identifier
            - **Status**: Current incident status (OPEN, INVESTIGATING, CONTAINED, RESOLVED)
            - **Severity**: Incident severity rating
            - **Created**: Timestamp when the incident was created
            - **Service**: Affected service or application
            - **Summary**: Brief description of the incident
            """)
            st.divider()
            st.write("**How to use:**")
            st.write("1. Enter your API key in the sidebar to see incidents")
            st.write("2. Browse the incident table")
            st.write("3. Select an incident from the dropdown")
            st.write("4. Click **View Details** to see full context")
            st.divider()
            
            # Show sample table structure
            st.subheader("Sample Table Structure (with data)")
            import pandas as pd
            sample_df = pd.DataFrame({
                "id": ["incident-xxx...", "incident-yyy...", "incident-zzz..."],
                "status": ["OPEN", "INVESTIGATING", "CONTAINED"],
                "severity": ["HIGH", "CRITICAL", "MEDIUM"],
                "created_at": ["2026-02-25", "2026-02-24", "2026-02-23"],
                "service_name": ["billing-api", "auth-service", "user-db"]
            })
            st.dataframe(sample_df, use_container_width=True, hide_index=True)

    elif tabs == "Incident Detail":
        if is_authenticated and client:
            incident_detail.render(client, st.session_state.selected_incident_id)
        else:
            st.title("Incident Detail")
            st.subheader("🔍 Deep Dive Analysis")
            st.write("""
            This tab provides comprehensive incident investigation with:
            - **Incident Metadata**: ID, status, severity, timestamps
            - **Agent Analysis**: Triage, analyst, intelligence, and commander AI findings
            - **Detection Context**: Rule information, triggered events, entities involved
            - **Related Logs**: Activity logs related to the incident
            - **Human Notes**: Editable notes for team collaboration
            - **Status Actions**: Update incident status through the UI
            """)
            st.divider()
            st.write("**Workflow:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**Step 1: Authenticate**")
                st.write("Enter API key in sidebar")
            with col2:
                st.write("**Step 2: Select**")
                st.write("Go to Incidents tab, pick one")
            with col3:
                st.write("**Step 3: Analyze**")
                st.write("Return here for full details")
            st.divider()
            st.info("No incident selected. Go to the **Incidents** tab to select one.")

    elif tabs == "Hunting":
        if is_authenticated and client:
            hunting.render(client)
        else:
            st.title("Hunting")
            st.subheader("🔎 Log Query & Investigation")
            st.write("""
            Hunt for security events across your logs using flexible filters:
            - **Actor**: User ID or service account
            - **Service Name**: Application or microservice
            - **Resource Path**: Normalized API path (e.g., /api/users/{id})
            - **Time Range**: Custom date/time windows
            - **Limit**: Results per query (up to 1000)
            """)
            st.divider()
            st.write("**Sample Query Results Include:**")
            st.write("- Timestamp and event type")
            st.write("- Source IP and user agent")
            st.write("- HTTP method and status code")
            st.write("- Geolocation data (country, city)")
            st.write("- Risk score and anomaly indicators")
            st.divider()
            st.write("**Export Options:**")
            st.write("- Download results as CSV")
            st.write("- Share query parameters with team")
            st.divider()
            st.info("Enter your API key in the sidebar to enable log hunting.")

    elif tabs == "Settings":
        settings.render(client, api_key if is_authenticated else None, is_authenticated)

except Exception as e:
    st.error(f"Application error: {str(e)}")
