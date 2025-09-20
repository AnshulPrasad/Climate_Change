import os

# Force writable locations BEFORE importing any libs that write files
os.environ["HOME"] = "/tmp"                    # important: expanduser() uses HOME
os.environ["XDG_CONFIG_HOME"] = "/tmp/.config"
os.environ["XDG_CACHE_HOME"] = "/tmp/.cache"
os.environ["STREAMLIT_CONFIG_DIR"] = "/tmp/.streamlit"

# Now imports (safe)
import streamlit as st
import geemap.foliumap as geemap
import ee
import os, json
from pathlib import Path

dataset_name, project_name = "UMD/hansen/global_forest_change_2024_v1_12", 'climate-change-472103'

# ------ Earth Engine service account handling ------
# If user sets GEE_SERVICE_KEY in HF secrets as JSON string, write it to a temporary file
key_json = os.environ.get("GEE_SERVICE_KEY")
if key_json:
    try:
        key_data = json.loads(key_json)
        sa_email = key_data.get("client_email")
        tmp_key_path = "/tmp/gee_service_account.json"
        # write JSON to file (overwrite if exists)
        Path(tmp_key_path).write_text(json.dumps(key_data))
        credentials = ee.ServiceAccountCredentials(sa_email, tmp_key_path)
        ee.Initialize(credentials, project=key_data.get("project_id"))
        st.write("✅ Earth Engine initialized with service account")
    except Exception as e:
        st.error(f"Failed to init Earth Engine: {e}")
        st.stop()
else:
    st.error("❌ No Earth Engine service key found. Please add GEE_SERVICE_KEY in HF secrets.")
    # fallback - try to initialize with project (will error if not authenticated)
    ee.Authenticate()
    ee.Initialize(project=project_name)


# Title
st.title("🌍 Hansen Global Forest Change Dashboard")

# Sidebar controls
st.sidebar.header("Controls")
year = st.sidebar.slider("Select Year of Loss", 2001, 2022, 2015)
show_treecover = st.sidebar.checkbox("Show Tree Cover 2000", True)
show_loss = st.sidebar.checkbox("Show Forest Loss", True)
show_gain = st.sidebar.checkbox("Show Forest Gain", False)

# Hansen dataset
dataset = ee.Image(dataset_name)
treecover2000 = dataset.select('treecover2000')
loss = dataset.select('loss')
gain = dataset.select('gain')
lossyear = dataset.select('lossyear')

# Mask to selected year
loss_selected = lossyear.eq(year - 2000)

# Create map
m = geemap.Map(center=[20, 0], zoom=3)

# Add layers based on toggle
if show_treecover:
    m.addLayer(treecover2000.updateMask(treecover2000),
               {'min': 0, 'max': 100, 'palette': ['white', 'green']},
               "Tree cover 2000")

if show_loss:
    m.addLayer(loss_selected.updateMask(loss_selected),
               {'palette': ['red']},
               f"Forest Loss {year}")

if show_gain:
    m.addLayer(gain.updateMask(gain),
               {'palette': ['blue']},
               "Forest Gain")

# --- Save map into /tmp (writable) and render with Streamlit ---
map_path = "/tmp/map.html"
m.save(map_path)           # forces save into a writable directory
html = Path(map_path).read_text()
st.components.v1.html(html, height=600, scrolling=True)
