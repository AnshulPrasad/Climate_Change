import os

def manage_writable_locations():
    """Set environment variables so Streamlit and other libs write to /tmp"""

    os.environ["HOME"] = "/tmp"
    os.environ["XDG_CONFIG_HOME"] = "/tmp/.config"
    os.environ["XDG_CACHE_HOME"] = "/tmp/.cache"
    os.environ["STREAMLIT_CONFIG_DIR"] = "/tmp/.streamlit"
