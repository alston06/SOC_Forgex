import streamlit as st
from datetime import datetime, timedelta
import pandas as pd


def render(client):
    st.title("Overview")

    try:
        # Fetch active incidents
        active_incidents = client.get_incidents(status="OPEN", limit=100)
        
        # Fetch all recent incidents for MTTA/MTTR calculation
        all_incidents = client.get_incidents(status="OPEN", limit=100)  # Could also fetch closed/investigating
        
        # Fetch alerts from last hour
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        alerts_last_hour = client.get_alerts(since=one_hour_ago, limit=200)
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Incidents", len(active_incidents))
        
        with col2:
            st.metric("Alerts (Last Hour)", len(alerts_last_hour))
        
        with col3:
            # MTTA stub (mean time to acknowledge) - would come from case status history
            st.metric("MTTA (min)", "N/A")
        
        with col4:
            # MTTR stub (mean time to resolve)
            st.metric("MTTR (min)", "N/A")
        
        # Severity distribution
        st.subheader("Severity Distribution")
        if active_incidents:
            severity_counts = {}
            for i in active_incidents:
                sev = i.get("severity", "UNKNOWN")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            severity_df = pd.DataFrame({
                "Severity": list(severity_counts.keys()),
                "Count": list(severity_counts.values())
            })
            st.bar_chart(severity_df.set_index("Severity"))
        else:
            st.info("No incidents to display.")
        
        # Alerts trend (simple hourly breakdown)
        st.subheader("Alerts Trend (Last 24 Hours)")
        if alerts_last_hour:
            alerts_df = pd.DataFrame(alerts_last_hour)
            if "timestamp" in alerts_df.columns:
                alerts_df["timestamp"] = pd.to_datetime(alerts_df["timestamp"])
                alerts_df["hour"] = alerts_df["timestamp"].dt.floor("H")
                hourly = alerts_df.groupby("hour").size()
                st.line_chart(hourly)
            else:
                st.info("No timestamp data available for trend.")
        else:
            st.info("No alerts in the last hour.")
    
    except Exception as e:
        st.error(f"Error loading overview: {str(e)}")