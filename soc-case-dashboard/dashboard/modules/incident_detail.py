import streamlit as st
import pandas as pd


def render(client, incident_id):
    """Render the full incident detail page."""

    if not incident_id:
        st.warning(
            "No incident selected. Go to **Incidents** and pick one."
        )
        return

    # ── Back button ────────────────────────────────────
    if st.button("← Back to Incidents"):
        st.session_state.selected_incident_id = None
        st.rerun()

    # ── Fetch data ─────────────────────────────────────
    try:
        data = client.get_incident_detail(incident_id)
    except Exception as e:
        st.error(f"Failed to load incident: {e}")
        return

    incident = data.get("incident", {})
    detection = data.get("detection")
    logs = data.get("logs", [])

    # ── Header ─────────────────────────────────────────
    st.title(f"Incident {incident.get('id', incident_id)[:16]}…")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = incident.get("status", "UNKNOWN")
        status_icons = {
            "OPEN": "🔴",
            "INVESTIGATING": "🟠",
            "CONTAINED": "🔵",
            "RESOLVED": "✅",
        }
        st.metric("Status", f"{status_icons.get(status, '')} {status}")
    with col2:
        severity = incident.get("severity", "UNKNOWN")
        sev_icons = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }
        st.metric(
            "Severity", f"{sev_icons.get(severity, '')} {severity}"
        )
    with col3:
        created = incident.get("created_at", "N/A")
        if isinstance(created, str):
            created = created[:19].replace("T", " ")
        st.metric("Created", created)
    with col4:
        updated = incident.get("updated_at", "N/A")
        if isinstance(updated, str):
            updated = updated[:19].replace("T", " ")
        st.metric("Updated", updated)

    st.divider()

    # ── Status Actions ─────────────────────────────────
    st.subheader("Actions")
    action_cols = st.columns(4)
    statuses = ["OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"]
    for idx, new_status in enumerate(statuses):
        with action_cols[idx]:
            disabled = incident.get("status") == new_status
            if st.button(
                f"Mark {new_status}",
                disabled=disabled,
                use_container_width=True,
                key=f"status_{new_status}",
            ):
                try:
                    client.update_incident_status(incident_id, new_status)
                    st.success(f"Status updated to {new_status}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()

    # ── Agent Analysis ─────────────────────────────────
    st.subheader("🤖 Agent Analysis")
    agent_summary = incident.get("agent_summary", {})

    agent_labels = {
        "initial_summary": "📝 Initial Summary",
        "triage": "🔍 Triage Agent",
        "analyst": "🧠 Analyst Agent",
        "intel": "🌐 Threat Intel Agent",
        "commander": "🎯 Commander Agent",
    }

    has_analysis = False
    for key, label in agent_labels.items():
        value = agent_summary.get(key)
        if value:
            has_analysis = True
            with st.expander(label, expanded=(key == "initial_summary")):
                if isinstance(value, dict):
                    st.json(value)
                else:
                    st.write(value)

    if not has_analysis:
        st.info("No agent analysis available yet.")

    st.divider()

    # ── Detection Context ──────────────────────────────
    st.subheader("🔎 Detection Context")
    if detection:
        det_cols = [
            "detection_id",
            "rule_id",
            "severity",
            "confidence",
            "triggered_events",
            "entities",
            "evidence",
        ]
        det_display = {
            k: detection.get(k, "N/A")
            for k in det_cols
            if k in detection
        }
        st.json(det_display)
    else:
        st.info(
            "Detection context unavailable (detection service may be offline)."
        )

    st.divider()

    # ── Related Logs ───────────────────────────────────
    st.subheader("📄 Related Logs")
    if logs:
        logs_df = pd.DataFrame(logs)
        display_cols = [
            col
            for col in [
                "timestamp",
                "event_type",
                "actor",
                "resource",
                "action",
                "ip",
                "service_name",
            ]
            if col in logs_df.columns
        ]
        if display_cols:
            st.dataframe(
                logs_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No related logs found.")

    st.divider()

    # ── Human Notes ────────────────────────────────────
    st.subheader("📝 Notes")
    current_notes = incident.get("human_notes", "")
    new_notes = st.text_area(
        "Investigation notes",
        value=current_notes,
        height=150,
        key="incident_notes",
    )

    if st.button("💾 Save Notes", type="primary"):
        try:
            client.update_incident_notes(incident_id, new_notes)
            st.success("Notes saved!")
        except Exception as e:
            st.error(f"Failed to save notes: {e}")
