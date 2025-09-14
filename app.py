import streamlit as st
import geemap.foliumap as geemap
import ee
from config import project_name, dataset_name

# Initialize Earth Engine
ee.Initialize(project= project_name)

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

# Display map in Streamlit
m.to_streamlit(height=600)
