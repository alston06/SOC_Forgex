import streamlit as st
import pandas as pd
import plotly.express as px


def render(client):
    st.title("📊 Overview")

    try:
        stats = client.get_stats()
    except Exception as e:
        st.error(f"Failed to load stats: {e}")
        return

    # ── Key metric cards ───────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔴 Open", stats.get("open_incidents", 0))
    with col2:
        st.metric("🟠 Investigating", stats.get("investigating_incidents", 0))
    with col3:
        st.metric("🔵 Contained", stats.get("contained_incidents", 0))
    with col4:
        st.metric("✅ Resolved", stats.get("resolved_incidents", 0))

    st.divider()

    # ── Summary row ────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Incidents", stats.get("total_incidents", 0))
    with col2:
        st.metric("Active API Keys", stats.get("api_keys_count", 0))
    with col3:
        st.metric("Webhooks", stats.get("webhooks_count", 0))

    st.divider()

    # ── Severity breakdown chart ───────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("Severity Breakdown")
        severity = stats.get("severity_breakdown", {})
        if severity:
            order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            color_map = {
                "CRITICAL": "#dc3545",
                "HIGH": "#fd7e14",
                "MEDIUM": "#ffc107",
                "LOW": "#198754",
                "INFO": "#0d6efd",
            }
            sev_df = pd.DataFrame(
                [
                    {"Severity": k, "Count": v}
                    for k, v in severity.items()
                ]
            )
            # Sort by severity order
            sev_df["Severity"] = pd.Categorical(
                sev_df["Severity"], categories=order, ordered=True
            )
            sev_df = sev_df.sort_values("Severity").dropna(subset=["Severity"])

            fig = px.bar(
                sev_df,
                x="Severity",
                y="Count",
                color="Severity",
                color_discrete_map=color_map,
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active incidents.")

    with right:
        st.subheader("Incident Status")
        status_data = {
            "Open": stats.get("open_incidents", 0),
            "Investigating": stats.get("investigating_incidents", 0),
            "Contained": stats.get("contained_incidents", 0),
            "Resolved": stats.get("resolved_incidents", 0),
        }
        non_zero = {k: v for k, v in status_data.items() if v > 0}
        if non_zero:
            status_df = pd.DataFrame(
                [{"Status": k, "Count": v} for k, v in non_zero.items()]
            )
            fig2 = px.pie(
                status_df,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map={
                    "Open": "#dc3545",
                    "Investigating": "#fd7e14",
                    "Contained": "#0d6efd",
                    "Resolved": "#198754",
                },
            )
            fig2.update_layout(
                margin=dict(l=0, r=0, t=10, b=0), height=300
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No incidents to display.")

    st.divider()

    # ── Recent incidents table ─────────────────────────
    st.subheader("Recent Incidents")
    recent = stats.get("recent_incidents", [])
    if recent:
        df = pd.DataFrame(recent)
        display_cols = [
            c
            for c in ["id", "status", "severity", "created_at", "summary"]
            if c in df.columns
        ]
        if display_cols:
            display_df = df[display_cols].copy()
            # Truncate IDs for readability
            if "id" in display_df.columns:
                display_df["id"] = display_df["id"].apply(
                    lambda x: x[:12] + "…" if isinstance(x, str) and len(x) > 12 else x
                )
            if "created_at" in display_df.columns:
                display_df["created_at"] = display_df["created_at"].apply(
                    lambda x: x[:19].replace("T", " ") if isinstance(x, str) else x
                )
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No incidents yet. Incidents will appear here once detections are processed.")
