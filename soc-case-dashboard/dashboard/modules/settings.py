import streamlit as st


def render(client):
    st.title("⚙️ Settings")

    # ── Account info ───────────────────────────────────
    st.subheader("Account")
    user = st.session_state.get("user", {})
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Username", value=user.get("username", ""), disabled=True)
        st.text_input("Tenant ID", value=user.get("tenant_id", ""), disabled=True)
    with col2:
        st.text_input("Organization", value=user.get("organization", ""), disabled=True)
        st.text_input("Role", value=user.get("role", "admin"), disabled=True)

    st.divider()

    # ── Webhooks ───────────────────────────────────────
    st.subheader("🔔 Webhooks")
    st.caption("Receive real-time notifications when incidents are created or updated.")

    try:
        webhooks = client.get_webhooks()
    except Exception:
        webhooks = []

    if webhooks:
        for i, wh in enumerate(webhooks, 1):
            with st.expander(f"{i}. {wh.get('url', 'Unknown URL')}"):
                st.write(f"**URL:** {wh.get('url')}")
                st.write(f"**Events:** {', '.join(wh.get('events', []))}")
                created = wh.get("created_at", "")
                if created:
                    st.write(f"**Created:** {created[:19].replace('T', ' ') if isinstance(created, str) else created}")
                if st.button(f"Delete webhook", key=f"del_wh_{i}"):
                    try:
                        client.delete_webhook(wh.get("id", ""))
                        st.success("Webhook deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
    else:
        st.info("No webhooks configured.")

    # Create webhook
    st.markdown("**Add Webhook**")
    with st.form("create_webhook", clear_on_submit=True):
        wh_url = st.text_input("Webhook URL", placeholder="https://example.com/webhook")
        wh_events = st.multiselect(
            "Events",
            ["incident_open", "incident_closed", "critical_alert", "status_update"],
            default=["incident_open"],
        )
        wh_submit = st.form_submit_button("Create Webhook", use_container_width=True)
        if wh_submit:
            if not wh_url:
                st.error("Please enter a URL.")
            else:
                try:
                    client.create_webhook(wh_url, wh_events)
                    st.success("Webhook created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()

    # ── Service endpoints ──────────────────────────────
    st.subheader("🔗 Service Endpoints")
    import os

    case_url = os.environ.get("CASE_SERVICE_URL", "http://localhost:8004")
    st.text_input("Case Service", value=case_url, disabled=True)

    st.divider()

    # ── Danger zone ────────────────────────────────────
    st.subheader("🚪 Session")
    if st.button("Logout", use_container_width=True):
        st.session_state.jwt_token = None
        st.session_state.user = None
        st.rerun()
