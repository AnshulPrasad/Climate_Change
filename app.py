# Import only manage_writable_locations first
from src.setup_env import manage_writable_locations

manage_writable_locations()  # Force Streamlit to use /tmp/.streamlit before it initializes anything

# imports
import logging, ee
import streamlit as st
st.set_option("browser.gatherUsageStats", False)
import geemap.foliumap as geemap
from pathlib import Path
from config import dataset_name
from src.visualization import plot_forest_loss
from src.utils import (
    get_forest_stats,
    init_logging,
    init_gee,
)


init_logging()
init_gee()


# Title
st.title("🌍 Global Forest Change Dashboard")

# Sidebar controls
st.sidebar.header("Controls")
st.sidebar.subheader("Select Year Range")
year_range = st.sidebar.slider(
    "Choose Year Range",
    min_value=2001,
    max_value=2024,
    value=(2010, 2015),
)
start_year, end_year = year_range
logging.info(f"Showing data from {start_year} to {end_year}")
show_treecover = st.sidebar.checkbox("Show Tree Cover 2000", True)
show_loss = st.sidebar.checkbox("Show Forest Loss", True)
show_gain = st.sidebar.checkbox("Show Forest Gain", False)


# Create map
m = geemap.Map(center=[22.0, 79.0], zoom=4)

# Let users draw ROI
st.sidebar.subheader("Draw ROI on Map")
roi = m.draw_features  # interactive drawing

# Hansen dataset
dataset = ee.Image(dataset_name)
treecover2000 = dataset.select("treecover2000")
loss = dataset.select("loss")
gain = dataset.select("gain")
lossyear = dataset.select("lossyear")

# Add layers based on toggle
if show_treecover:
    m.addLayer(
        treecover2000.updateMask(treecover2000),
        {"min": 0, "max": 100, "palette": ["white", "green"]},
        "Tree cover 2000",
    )

if show_loss:
    mask = lossyear.gte(start_year - 2000).And(lossyear.lte(end_year - 2000))
    m.addLayer(
        loss.updateMask(mask),
        {"palette": ["red"]},
        f"Forest Loss {start_year}-{end_year}",
    )

if show_gain:
    m.addLayer(
        gain.updateMask(gain),
        {"palette": ["blue"]},
        "Forest Gain",
    )

# --- Save map into /tmp (writable) and render with Streamlit ---
map_path = "/tmp/map.html"
m.save(map_path)  # forces save into a writable directory
html = Path(map_path).read_text()
st.components.v1.html(html, height=600, scrolling=True)


# If user has drawn ROI, compute stats
# else compute Global Forest Statics
if roi and len(roi.get("features", [])) > 0:
    roi_geom = ee.Geometry.Polygon(roi["features"][0]["geometry"]["coordinates"])
else:
    roi_geom = ee.Geometry.BBox(-180, -90, 180, 90)

stats = get_forest_stats(roi_geom, start_year, end_year, dataset)

st.subheader("📊 Region Of Interest (ROI) Forest Statistics")
st.write(
    f"🌲 Forest area (2000): {stats['forest_area_2000']['treecover2000']/10000:,.2f} ha"
)
st.write(
    f"🔥 Total loss ({start_year}–{end_year}): {stats['loss_area']['loss']/10000:,.2f} ha"
)
st.write(f"🌱 Total gain (2001–2024): {stats['gain_area']['gain']/10000:,.2f} ha")


# Assume loss_dict is already computed somewhere in your app
st.header("Yearly Forest Area Loss")

loss_dict = stats["yearly_loss"]
fig = plot_forest_loss(loss_dict)
st.pyplot(fig)  # Streamlit renders the matplotlib figure
