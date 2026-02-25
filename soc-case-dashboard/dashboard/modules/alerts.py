import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def render(client):
    st.title("Alerts")

    try:
        # Fetch alerts from last 24 hours
        one_day_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
        alerts = client.get_alerts(since=one_day_ago, limit=200)

        if not alerts:
            st.info("No alerts found.")
            return

        # Convert to dataframe and select/format relevant columns
        alerts_df = pd.DataFrame(alerts)
        
        # Select key columns if they exist
        display_cols = []
        for col in ["timestamp", "rule_id", "severity", "confidence", "actor", "ip", "service_name"]:
            if col in alerts_df.columns:
                display_cols.append(col)
        
        if display_cols:
            display_df = alerts_df[display_cols].copy()
            
            # Format confidence as percentage if present
            if "confidence" in display_df.columns:
                display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x*100:.0f}%" if isinstance(x, (int, float)) else x)
            
            # Show as interactive dataframe
            st.dataframe(display_df, use_container_width=True)
            
            # Selection logic: if row clicked, store detection_id in session
            st.subheader("Alert Details")
            if "detection_id" in alerts_df.columns:
                selected_detection = st.selectbox(
                    "Select alert for details",
                    options=alerts_df["detection_id"].tolist() if len(alerts_df) > 0 else [],
                    format_func=lambda x: f"{x[:8]}..." if x else "None"
                )
                if selected_detection:
                    st.session_state.selected_detection_id = selected_detection
                    detail = alerts_df[alerts_df["detection_id"] == selected_detection].iloc[0].to_dict()
                    st.json(detail)
        else:
            st.dataframe(alerts_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error loading alerts: {str(e)}")