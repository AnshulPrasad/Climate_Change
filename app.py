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
    rmv_existing_draw_controls,
)
from streamlit_folium import st_folium
from folium.plugins import Draw

init_logging()
init_gee()

# Hansen dataset
dataset = ee.Image(dataset_name)
treecover2000 = dataset.select("treecover2000")
loss = dataset.select("loss")
gain = dataset.select("gain")
lossyear = dataset.select("lossyear")


# -----------------------------------------------------
# App Sidebar
# -----------------------------------------------------

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


# -------------------------------------------------------
# Map
# -------------------------------------------------------

# Create map
m = geemap.Map(center=[22.0, 79.0], zoom=4)

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

rmv_existing_draw_controls(m)

# Add a Draw control so users can draw polygons/polylines/markers
Draw(
    export=True,
    draw_options={
        "polyline": False,  # disable because we don't want polylines
        "circle": False,
        "circlemarker": False,
    },
    edit_options={
        "edit": False,
        "remove": False,
    },
).add_to(m)

# ensure session state key for forcing map refresh (clearing drawings removed)
if "map_key" not in st.session_state:
    st.session_state["map_key"] = 0

# small UI for clearing existing drawings on the client map
col_clear, _ = st.columns([1, 5])
with col_clear:
    if st.button("Clear drawings"):
        # bump the key so st_folium gets a fresh instance (client-side drawing)
        st.session_state["map_key"] += 1
        st.rerun()

# Render the interactive map with a key tied to session_state to allow resets
map_return = st_folium(
    m,
    height=600,
    width=900,
    key=f"map-{st.session_state['map_key']}",
)
logging.info(f"map_return:\n{map_return}")
drawn_geojson = extract_drawn_geojson(map_return)

# Convert drawn geojson to an ee.Geometry (if present)
roi_geom = None
if drawn_geojson:
    try:
        geometries = []

        # case 1: list of fetures (from "all_drawings")
        if isinstance(drawn_geojson, list):
            # Combine all shapes into one GeometryCollection
            for f in drawn_geojson:
                # if it has a 'geometry' field, use that dict directly
                if "geometry" in f:
                    geometries.append(ee.Geometry(f["geometry"]))

        # case 2: dict (single feature or FeatureCollection)
        elif isinstance(drawn_geojson, dict):
            if drawn_geojson.get("type") == "FeatureCollection":
                for f in drawn_geojson["features"]:
                    if "geometry" in f:
                        geometries.append(ee.Geometry(f["geometry"]))
            elif "geometry" in drawn_geojson:
                geometries.append(ee.Geometry(drawn_geojson["geometry"]))
            else:
                geometries.append(ee.Geometry(drawn_geojson))  # fallback

        # combine all shapes into one union geometries
        if geometries:
            if len(geometries) == 1:
                roi_geom = geometries[0]
            else:
                roi_geom = (
                    ee.FeatureCollection([ee.Feature(g) for g in geometries])
                    .union()
                    .geometry()
                )
    except Exception as e:
        # If parsing fails, keep roi_geom None and show error in UI
        st.error(f"Failed to parse drawn ROI: {e}")
        roi_geom = None

if not roi_geom:
    roi_geom = ee.Geometry.BBox(-180, -90, 180, 90)


stats = get_forest_stats(roi_geom, start_year, end_year, dataset)


# --------------------------------------------------
# Region Of Interest (ROI) Forest Statistics
# --------------------------------------------------

st.subheader("📊 Region Of Interest (ROI) Forest Statistics")
st.write(
    f"🌲 Forest area (2000): {stats['forest_area_2000']['treecover2000']/10000:,.2f} ha"
)
st.write(
    f"🔥 Total loss ({start_year}–{end_year}): {stats['loss_area']['loss']/10000:,.2f} ha"
)
st.write(f"🌱 Total gain (2001–2024): {stats['gain_area']['gain']/10000:,.2f} ha")


# -----------------------------------------
# Yearly Forest Area Loss chart
# ------------------------------------------

# Assume loss_dict is already computed somewhere in your app
st.header("Yearly Forest Area Loss")

loss_dict = stats["yearly_loss"]
fig = plot_forest_loss(loss_dict)
st.pyplot(fig)  # Streamlit renders the matplotlib figure
