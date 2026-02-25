"""Helpers to persist authentication state in browser localStorage."""

import json

import streamlit.components.v1 as components
from streamlit_js_eval import streamlit_js_eval

_LS_TOKEN_KEY = "soc_forgex_token"
_LS_USER_KEY = "soc_forgex_user"

# Sentinel returned while waiting for the browser JS to respond.
LOADING = object()


def save_auth(token: str, user: dict):
    """Save JWT token and user info to browser localStorage (fire-and-forget)."""
    components.html(
        f"""<script>
        localStorage.setItem("{_LS_TOKEN_KEY}", {json.dumps(token)});
        localStorage.setItem("{_LS_USER_KEY}", {json.dumps(json.dumps(user))});
        </script>""",
        height=0,
    )


def clear_auth():
    """Remove auth data from browser localStorage (fire-and-forget)."""
    components.html(
        f"""<script>
        localStorage.removeItem("{_LS_TOKEN_KEY}");
        localStorage.removeItem("{_LS_USER_KEY}");
        </script>""",
        height=0,
    )


def load_auth():
    """Attempt to load saved auth from browser localStorage.

    Returns
    -------
    LOADING
        JS hasn't responded yet — caller should show a spinner and ``st.stop()``.
    (None, None)
        No saved credentials in localStorage.
    (token: str, user: dict)
        Successfully restored auth data.
    """
    result = streamlit_js_eval(
        js_expressions=(
            "JSON.stringify({"
            f't: localStorage.getItem("{_LS_TOKEN_KEY}") || "",'
            f'u: localStorage.getItem("{_LS_USER_KEY}") || ""'
            "})"
        ),
        key="auth_restore",
    )

    # streamlit_js_eval returns 0 (its default) before JS responds
    if not isinstance(result, str):
        return LOADING

    try:
        data = json.loads(result)
        token = data.get("t", "")
        user_raw = data.get("u", "")
        if token:
            user = json.loads(user_raw) if user_raw else {}
            return (token, user)
    except (json.JSONDecodeError, TypeError):
        pass

    return (None, None)
