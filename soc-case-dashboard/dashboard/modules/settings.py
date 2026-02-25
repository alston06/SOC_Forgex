import streamlit as st


def render(client, api_key, is_authenticated):
    st.title("Settings")
    
    st.divider()

    # API Key display (masked)
    st.subheader("🔐 Authentication")
    if api_key and is_authenticated:
        masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        st.text_input("API Key (masked)", value=masked_key, disabled=True)
        st.success("✅ Authenticated - All features enabled")
    else:
        st.warning("⚠️ No API key configured")
        st.info("""
        Enter your API key in the **Configuration** section in the sidebar to authenticate.
        Your API key will be stored in the session and used to access the case management service.
        """)

    st.divider()

    # Service URLs
    st.subheader("🔗 Service Endpoints")
    with st.expander("View configured URLs"):
        from app import st as streamlit_module
        st.write("**Case Service:** http://localhost:8004 (default)")
        st.write("**Detection Service:** http://localhost:8005 (default)")
        st.info("These can be customized in the sidebar **Configuration** section.")

    st.divider()

    # Webhook management
    st.subheader("🔔 Webhooks")
    
    if not is_authenticated:
        st.info("📝 Configure your API key to manage webhooks and receive incident notifications.")
        st.write("**Webhook features (when authenticated):**")
        st.write("- Subscribe to incident_open events")
        st.write("- Subscribe to critical_alert events")
        st.write("- Configure custom webhook URLs")
        st.write("- View all active webhooks")
        return
    
    try:
        webhooks = client.get_webhooks()
        
        if webhooks:
            st.write("**Active Webhooks:**")
            for i, webhook in enumerate(webhooks, 1):
                with st.expander(f"{i}. {webhook.get('url')}"):
                    st.write(f"**URL:** {webhook.get('url')}")
                    st.write(f"**Events:** {', '.join(webhook.get('events', []))}")
                    if webhook.get('created_at'):
                        st.write(f"**Created:** {webhook.get('created_at')}")
        else:
            st.info("No webhooks configured yet.")
        
        st.divider()
        
        # Create new webhook
        st.subheader("➕ Add New Webhook")
        col1, col2 = st.columns([2, 1])
        with col1:
            new_url = st.text_input("Webhook URL (where we'll send notifications)")
        with col2:
            if st.button("Test Connection", help="Test if the webhook URL is reachable"):
                st.info("Test endpoint hit (stub - requires backend implementation)")
        
        events = st.multiselect(
            "Events to subscribe to",
            ["incident_open", "incident_closed", "critical_alert", "status_update"],
            default=["incident_open"],
            help="Select which events trigger notifications to this webhook"
        )
        
        if st.button("Create Webhook", type="primary"):
            if new_url:
                try:
                    client.create_webhook(new_url, events)
                    st.success("✅ Webhook created successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create webhook: {str(e)}")
            else:
                st.warning("Please enter a webhook URL.")
    
    except Exception as e:
        st.warning(f"Could not load webhooks: {str(e)}")

    st.divider()

    # SDK Integration Health
    st.subheader("📡 SDK Integration Health")
    st.info("""
    Monitors activity from integrated services and SDKs.
    This data is pulled from the **ingestion_metrics** collection in MongoDB.
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("billing-api", "5m ago", delta="Active", help="Last event received")
    with col2:
        st.metric("user-service", "2m ago", delta="Active", help="Last event received")
    with col3:
        st.metric("auth-service", "15m ago", delta="Active", help="Last event received")
    
    st.caption("*(Stub data - integrate ingestion_metrics collection for real-time data)*")
    
    st.divider()
    
    # Documentation
    st.subheader("📚 Documentation")
    with st.expander("API Key Setup Guide"):
        st.write("""
        **How to get your API key:**
        1. Contact your SOC administrator
        2. Request an API key for your service/team
        3. The key will be hashed (SHA256) and stored in the database
        4. Paste the key in the **Configuration** sidebar
        5. Dashboard will authenticate and enable all features
        
        **API Key Format:**
        - Alphanumeric string, typically 32+ characters
        - Keep it secure - treat it like a password
        - Can be rotated by your administrator
        """)
    
    with st.expander("Webhook Format"):
        st.write("""
        **Webhook Payload Example:**
        ```json
        {
          "event": "incident_open",
          "tenant_id": "tenant123",
          "incident_id": "incident-uuid",
          "severity": "HIGH",
          "timestamp": "2026-02-25T12:34:56Z"
        }
        ```
        
        **Webhook Response Expected:**
        - Status 200-299: Success
        - Any other status: Retry (up to 3 times)
        """)
    
    with st.expander("Troubleshooting"):
        st.write("""
        **Issue: "Invalid API Key"**
        - Double-check the key in the sidebar
        - Ensure no extra spaces or characters
        - Contact your administrator to verify key status
        
        **Issue: "Connection refused" to case service**
        - Verify the Case Service URL is correct
        - Ensure the backend is running
        - Check firewall rules
        
        **Issue: Webhooks not delivering**
        - Verify your webhook URL is publicly accessible
        - Check application logs for 4xx/5xx errors
        - Use the Test Connection button to diagnose
        """)

