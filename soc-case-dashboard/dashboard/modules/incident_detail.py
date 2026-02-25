import streamlit as st
import pandas as pd


def render(client, incident_id):
    st.title("Incident Detail")

    if not incident_id:
        st.warning("No incident selected. Go to Incidents tab and select one.")
        return

    try:
        # Fetch full incident with detection and logs
        data = client.get_incident_detail(incident_id)
        incident = data.get("incident", {})
        detection = data.get("detection", {})
        logs = data.get("logs", [])

        # Header section
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("ID", incident.get("id", "N/A")[:12] + "...")
        with col2:
            st.metric("Status", incident.get("status", "N/A"))
        with col3:
            st.metric("Severity", incident.get("severity", "N/A"))
        with col4:
            st.metric("Created", incident.get("created_at", "N/A")[:10])

        # Agent summaries in expanders
        st.subheader("Agent Analysis")
        agent_summary = incident.get("agent_summary", {})
        
        for agent_type in ["triage", "analyst", "intel", "commander"]:
            if agent_type in agent_summary and agent_summary[agent_type]:
                with st.expander(f"{agent_type.title()} Agent"):
                    st.json(agent_summary[agent_type])

        # Detection context
        if detection:
            st.subheader("Detection Context")
            det_cols = ["detection_id", "rule_id", "triggered_events", "entities", "evidence"]
            det_display = {k: detection.get(k, "N/A") for k in det_cols if k in detection}
            st.json(det_display)

        # Logs
        if logs:
            st.subheader("Related Logs")
            logs_df = pd.DataFrame(logs)
            # Select useful columns
            display_cols = [col for col in ["timestamp", "event_type", "actor", "resource", "action", "ip"] if col in logs_df.columns]
            if display_cols:
                st.dataframe(logs_df[display_cols], use_container_width=True)
            else:
                st.dataframe(logs_df, use_container_width=True)

        # Human notes
        st.subheader("Human Notes")
        current_notes = incident.get("human_notes", "")
        new_notes = st.text_area("Update notes", value=current_notes, height=150)
        
        if st.button("Save Notes"):
            try:
                client.update_incident_notes(incident_id, new_notes)
                st.success("Notes updated!")
            except Exception as e:
                st.error(f"Failed to update notes: {str(e)}")

        # Status buttons
        st.subheader("Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Mark as Investigating"):
                st.info("Status update not yet implemented on backend")
        
        with col2:
            if st.button("Mark as Contained"):
                st.info("Status update not yet implemented on backend")
        
        with col3:
            if st.button("Mark as Resolved"):
                st.info("Status update not yet implemented on backend")

    except Exception as e:
        st.error(f"Error loading incident detail: {str(e)}")
