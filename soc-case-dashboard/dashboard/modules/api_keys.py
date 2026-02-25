import streamlit as st
import pandas as pd


def render(client):
    st.title("🔑 API Keys")
    st.caption(
        "API keys allow your services and SDKs to send activity logs "
        "to SOC Forgex. Keys are shown **only once** upon creation."
    )

    # ── Create new key ─────────────────────────────────
    st.subheader("Create New API Key")

    with st.form("create_api_key", clear_on_submit=True):
        key_name = st.text_input(
            "Key name",
            placeholder="e.g. production-billing-api",
        )
        submitted = st.form_submit_button(
            "Generate Key", type="primary", use_container_width=True
        )

        if submitted:
            if not key_name:
                st.error("Please provide a name for the key.")
            else:
                try:
                    result = client.create_api_key(key_name)
                    raw_key = result.get("key", "")
                    st.success("API key created successfully!")
                    st.warning(
                        "⚠️ Copy this key now — it won't be shown again!"
                    )
                    st.code(raw_key, language=None)
                except Exception as e:
                    st.error(f"Failed to create key: {e}")

    st.divider()

    # ── Existing keys table ────────────────────────────
    st.subheader("Your API Keys")

    try:
        keys = client.get_api_keys()
    except Exception as e:
        st.error(f"Failed to load keys: {e}")
        return

    if not keys:
        st.info("No API keys yet. Create one above to get started.")
        return

    # Build display table
    rows = []
    for k in keys:
        rows.append(
            {
                "Name": k.get("name", "—"),
                "Prefix": k.get("prefix", "***"),
                "Active": "✅ Active" if k.get("active", True) else "❌ Revoked",
                "Created": (
                    k["created_at"][:19].replace("T", " ")
                    if isinstance(k.get("created_at"), str)
                    else str(k.get("created_at", ""))
                ),
                "Last Used": (
                    k["last_used_at"][:19].replace("T", " ")
                    if isinstance(k.get("last_used_at"), str)
                    else "Never"
                ),
                "_id": k.get("id"),
                "_active": k.get("active", True),
            }
        )

    df = pd.DataFrame(rows)
    display_df = df[["Name", "Prefix", "Active", "Created", "Last Used"]]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Revoke key ─────────────────────────────────────
    active_keys = [r for r in rows if r["_active"]]
    if active_keys:
        st.subheader("Revoke a Key")
        revoke_options = {
            f"{k['Name']} ({k['Prefix']}…)": k["_id"]
            for k in active_keys
        }
        selected_label = st.selectbox(
            "Select key to revoke", options=list(revoke_options.keys())
        )
        if st.button("🗑️ Revoke Key", type="secondary"):
            key_id = revoke_options[selected_label]
            try:
                client.revoke_api_key(key_id)
                st.success("Key revoked.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to revoke key: {e}")

    st.divider()

    # ── SDK integration guide ──────────────────────────
    st.subheader("📚 SDK Integration")
    with st.expander("Quick Start Guide", expanded=False):
        st.markdown(
            """
**1. Install the SDK** (or use the REST API directly):
```bash
pip install requests
```

**2. Send activity logs:**
```python
import requests

API_KEY = "sfx_your_key_here"
ENDPOINT = "http://your-soc-forgex-host:8001/v1/ingest"

payload = {
    "event_type": "api_call",
    "actor": "user-123",
    "service_name": "billing-api",
    "resource": "/api/invoices/42",
    "action": "read",
    "ip": "203.0.113.45",
    "timestamp": "2026-02-25T12:00:00Z"
}

resp = requests.post(
    ENDPOINT,
    json=payload,
    headers={"X-API-Key": API_KEY},
)
print(resp.status_code)
```

**3. Events flow through the pipeline:**
- → Normalizer enriches the log
- → Detection engine matches rules
- → AI agents investigate high-severity detections
- → Incidents appear in this dashboard
"""
        )
