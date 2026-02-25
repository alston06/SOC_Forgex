import streamlit as st
import pandas as pd


_SEVERITY_COLORS = {
    "CRITICAL": "🔴",
    "HIGH": "🟠",
    "MEDIUM": "🟡",
    "LOW": "🟢",
    "INFO": "🔵",
}

_STATUS_COLORS = {
    "OPEN": "🔴",
    "INVESTIGATING": "🟠",
    "CONTAINED": "🔵",
    "RESOLVED": "✅",
}


def render(client):
    st.title("📋 Incidents")

    # ── Filters ────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        status_filter = st.selectbox(
            "Status",
            ["All", "OPEN", "INVESTIGATING", "CONTAINED", "RESOLVED"],
            index=0,
        )
    with col_f2:
        severity_filter = st.selectbox(
            "Severity",
            ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            index=0,
        )
    with col_f3:
        limit = st.slider("Max results", 10, 200, 50)

    # ── Fetch data ─────────────────────────────────────
    try:
        incidents = client.get_incidents(
            status=status_filter if status_filter != "All" else None,
            severity=severity_filter if severity_filter != "All" else None,
            limit=limit,
        )
    except Exception as e:
        st.error(f"Failed to load incidents: {e}")
        return

    if not incidents:
        st.info("No incidents match the selected filters.")
        return

    st.caption(f"Showing {len(incidents)} incident(s)")

    # ── Build display dataframe ────────────────────────
    df = pd.DataFrame(incidents)

    display_cols = [
        c
        for c in ["id", "status", "severity", "created_at", "summary"]
        if c in df.columns
    ]
    if not display_cols:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    display_df = df[display_cols].copy()

    # Format columns
    if "id" in display_df.columns:
        display_df["id"] = display_df["id"].apply(
            lambda x: x[:12] + "…" if isinstance(x, str) and len(x) > 12 else x
        )
    if "severity" in display_df.columns:
        display_df["severity"] = display_df["severity"].apply(
            lambda x: f"{_SEVERITY_COLORS.get(x, '')} {x}" if x else x
        )
    if "status" in display_df.columns:
        display_df["status"] = display_df["status"].apply(
            lambda x: f"{_STATUS_COLORS.get(x, '')} {x}" if x else x
        )
    if "created_at" in display_df.columns:
        display_df["created_at"] = display_df["created_at"].apply(
            lambda x: x[:19].replace("T", " ") if isinstance(x, str) else x
        )
    if "summary" in display_df.columns:
        display_df["summary"] = display_df["summary"].apply(
            lambda x: (x[:80] + "…") if isinstance(x, str) and len(x) > 80 else (x or "—")
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Select incident for detail view ────────────────
    st.divider()
    st.subheader("View Incident Details")

    raw_ids = df["id"].tolist() if "id" in df.columns else []
    if raw_ids:
        selected_id = st.selectbox(
            "Select an incident",
            options=raw_ids,
            format_func=lambda x: f"{x[:16]}…" if len(x) > 16 else x,
        )

        if st.button("Open Incident →", type="primary"):
            st.session_state.selected_incident_id = selected_id
            st.rerun()
