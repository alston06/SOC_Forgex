import streamlit as st
from services.dashboard_client import DashboardClient


def render(base_url: str):
    """Render the login / register page."""

    # Center the form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            """
            <div style="text-align:center; margin-bottom: 2rem;">
                <h1>🛡️ SOC Forgex</h1>
                <p style="color:#888; font-size:1.1rem;">
                    Security Operations Dashboard
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        # ── Login ──────────────────────────────────────────
        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Sign In", use_container_width=True, type="primary"
                )

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        try:
                            result = DashboardClient.login(
                                base_url, username, password
                            )
                            st.session_state.jwt_token = result["token"]
                            st.session_state.user = result["user"]
                            st.rerun()
                        except Exception as exc:
                            detail = ""
                            try:
                                detail = exc.response.json().get("detail", "")
                            except Exception:
                                detail = str(exc)
                            st.error(f"Login failed: {detail}")

        # ── Register ───────────────────────────────────────
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                new_username = st.text_input("Username", key="reg_user")
                new_password = st.text_input(
                    "Password", type="password", key="reg_pass"
                )
                confirm_password = st.text_input(
                    "Confirm Password", type="password", key="reg_confirm"
                )
                organization = st.text_input(
                    "Organization Name", key="reg_org"
                )
                registered = st.form_submit_button(
                    "Create Account",
                    use_container_width=True,
                    type="primary",
                )

                if registered:
                    if not all(
                        [
                            new_username,
                            new_password,
                            confirm_password,
                            organization,
                        ]
                    ):
                        st.error("Please fill in all fields.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 4:
                        st.error(
                            "Password must be at least 4 characters."
                        )
                    else:
                        try:
                            result = DashboardClient.register(
                                base_url,
                                new_username,
                                new_password,
                                organization,
                            )
                            st.session_state.jwt_token = result["token"]
                            st.session_state.user = result["user"]
                            st.success("Account created successfully!")
                            st.rerun()
                        except Exception as exc:
                            detail = ""
                            try:
                                detail = exc.response.json().get(
                                    "detail", ""
                                )
                            except Exception:
                                detail = str(exc)
                            st.error(f"Registration failed: {detail}")

        st.divider()
        st.caption("Default credentials: **admin** / **admin**")
