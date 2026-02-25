import streamlit as st
import pandas as pd


def render(client):
    st.title("Incidents")

    try:
        # Fetch open incidents
        incidents = client.get_incidents(status="OPEN", limit=100)

        if not incidents:
            st.info("No active incidents.")
            return

        # Convert to dataframe
        incidents_df = pd.DataFrame(incidents)
        
        # Select and reorder columns
        display_cols = []
        for col in ["id", "status", "severity", "created_at", "service_name", "summary"]:
            if col in incidents_df.columns:
                display_cols.append(col)
            elif col == "id" and "_id" in incidents_df.columns:
                incidents_df["id"] = incidents_df["_id"]
                display_cols.append("id")
        
        display_df = incidents_df[display_cols] if display_cols else incidents_df
        
        st.dataframe(display_df, use_container_width=True)
        
        # Selection: click to view details
        st.subheader("View Details")
        if len(incidents_df) > 0:
            incident_ids = incidents_df["id"].tolist() if "id" in incidents_df.columns else incidents_df["_id"].tolist()
            selected_id = st.selectbox(
                "Select incident to view",
                options=incident_ids,
                format_func=lambda x: f"{x[:12]}..." if x else "None"
            )
            
            if selected_id and st.button("View Details"):
                st.session_state.selected_incident_id = selected_id
    
    except Exception as e:
        st.error(f"Error loading incidents: {str(e)}")