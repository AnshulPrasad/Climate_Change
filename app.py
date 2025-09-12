import streamlit as st
import geemap.foliumap as geemap
import ee
import json, os

import ee, os, json

# Initialize Earth Engine with service account if running on HF
key_json = os.environ.get("GEE_SERVICE_KEY")

if key_json:
    # Parse the JSON key from secret
    key_data = json.loads(key_json)
    service_account = key_data["client_email"]
    credentials = ee.ServiceAccountCredentials(service_account, key_data=key_json)
    ee.Initialize(credentials)
else:
    # Local dev fallback (requires manual ee.Authenticate())
    try:
        ee.Initialize()
        st.write("✅ Initialized Earth Engine (local dev)")
    except Exception as e:
        st.error(f"Local Earth Engine init failed: {e}")
        st.stop()

# Title
st.title("🌍 Hansen Global Forest Change Dashboard")

# Sidebar controls
st.sidebar.header("Controls")

year = st.sidebar.slider("Select Year of Loss", 2001, 2022, 2015)
show_treecover = st.sidebar.checkbox("Show Tree Cover 2000", True)
show_loss = st.sidebar.checkbox("Show Forest Loss", True)
show_gain = st.sidebar.checkbox("Show Forest Gain", False)

# Hansen dataset
dataset = ee.Image("UMD/hansen/global_forest_change_2022_v1_10")

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

# Display map in Streamlit
m.to_streamlit(height=600, filepath="/tmp/map.html")
