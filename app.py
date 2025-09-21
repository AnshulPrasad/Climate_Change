# Import only manage_writable_locations first
from src.setup_env import manage_writable_locations

manage_writable_locations()  # Force Streamlit to use /tmp/.streamlit before it initializes anything

# imports
import logging, ee
import streamlit as st
import geemap.foliumap as geemap
from pathlib import Path
from config import dataset_name
from src.visualization import plot_forest_loss
from src.utils import (
    get_forest_stats,
    init_logging,
    init_gee,
    extract_drawn_geojson,
)
from streamlit_folium import st_folium
from folium.plugins import Draw


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

# Add a Draw control so users can draw polygons/polylines/markers
Draw(
    export=True,
    draw_options={
        "polyline": False,  # disable because we don't want polylines
        "circle": False,
        "circlemarker": False,
    },
).add_to(m)

# Display map with streamlit-folium and capture interations (returns as dict)
map_return = st_folium(m, height=600, width=900)
drawn_geojson = extract_drawn_geojson(map_return)

# Convert drawn geojson to an ee.Geometry (if present)
roi_geom = None
if drawn_geojson:
    try:
        # If returned as FeatureCollection-like dict, use as-is
        # Ensure we pass a proper GeoJSON geometry or feature to ee.Geometry
        # The code below handles multiple shapes; we take the first feature polygon
        if isinstance(drawn_geojson, dict):
            # Many returns contain feature collection {"type":"FeatureCollection", "features":[...]}
            if drawn_geojson.get("type") == "FeatureCollection":
                feat = drawn_geojson["features"][0]
                geom_json = feat.get("geometry") if "geometry" in feat else feat
            elif "geometry" in drawn_geojson:
                geom_json = drawn_geojson["geometry"]
            else:
                geom_json = drawn_geojson  # fallback

            # create ee.Geometry directly from the GeoJSON geometry
            roi_geom = ee.Geometry(geom_json)

        else:
            # If it's a list/other, attempt to create polygon with coordinates
            roi_geom = ee.Geometry(drawn_geojson)

    except Exception as e:
        # If parsing fails, keep roi_geom None and show error in UI
        st.error(f"Failed to parse drawn ROI: {e}")
        roi_geom = None

if not roi_geom:
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
