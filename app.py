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

st.set_page_config(page_title="Climate Change Dashboard", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --page-max-width: 1200px;
        --light-border: #e5e7eb;
        --text-dark: #0f172a;
        --text-muted: #64748b;
    }
    .block-container {
        max-width: var(--page-max-width);
        padding-top: 1.75rem;
        padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] { display: none; }
    .tab-sidebar {
        background: #f8fafc;
        border: 1px solid var(--light-border);
        border-radius: 12px;
        padding: 1rem;
    }
    .tab-sidebar h4 {
        color: var(--text-dark);
        margin-bottom: 0.75rem;
    }
    .tab-sidebar p {
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

init_logging()
init_gee()

# Hansen dataset
dataset = ee.Image(dataset_name)
treecover2000 = dataset.select("treecover2000")
loss = dataset.select("loss")
gain = dataset.select("gain")
lossyear = dataset.select("lossyear")

st.markdown("## Climate Change Dashboard")
st.caption("Explore key climate signals by category.")

tab_forest, tab_temp, tab_emissions, tab_about = st.tabs(
    ["Forest Loss", "Temperature", "Emissions", "About"]
)

with tab_forest:
    left, right = st.columns([1, 3], gap="large")
    with left:
        st.markdown('<div class="tab-sidebar">', unsafe_allow_html=True)
        st.markdown("#### Forest Loss Controls")
        year_range = st.slider(
            "Year Range",
            min_value=2001,
            max_value=2024,
            value=(2010, 2015),
        )
        start_year, end_year = year_range
        logging.info(f"Showing data from {start_year} to {end_year}")
        show_treecover = st.checkbox("Show Tree Cover 2000", True)
        show_loss = st.checkbox("Show Forest Loss", True)
        show_gain = st.checkbox("Show Forest Gain", False)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.subheader("Forest Loss Explorer")
        st.write("Draw a region on the map to compute stats.")
        m = geemap.Map(center=[22.0, 79.0], zoom=4)

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
        Draw(
            export=True,
            draw_options={
                "polyline": False,
                "circle": False,
                "circlemarker": False,
            },
            edit_options={
                "edit": False,
                "remove": False,
            },
        ).add_to(m)

        if "map_key" not in st.session_state:
            st.session_state["map_key"] = 0

        col_clear, _ = st.columns([1, 5])
        with col_clear:
            if st.button("Clear drawings"):
                st.session_state["map_key"] += 1
                st.rerun()

        map_return = st_folium(
            m,
            height=600,
            width=950,
            key=f"map-{st.session_state['map_key']}",
        )
        logging.info(f"map_return:\n{map_return}")
        drawn_geojson = extract_drawn_geojson(map_return)

        roi_geom = None
        if drawn_geojson:
            try:
                geometries = []
                if isinstance(drawn_geojson, list):
                    for f in drawn_geojson:
                        if "geometry" in f:
                            geometries.append(ee.Geometry(f["geometry"]))
                elif isinstance(drawn_geojson, dict):
                    if drawn_geojson.get("type") == "FeatureCollection":
                        for f in drawn_geojson["features"]:
                            if "geometry" in f:
                                geometries.append(ee.Geometry(f["geometry"]))
                    elif "geometry" in drawn_geojson:
                        geometries.append(ee.Geometry(drawn_geojson["geometry"]))
                    else:
                        geometries.append(ee.Geometry(drawn_geojson))

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

        st.header("Yearly Forest Area Loss")
        loss_dict = stats["yearly_loss"]
        fig = plot_forest_loss(loss_dict)
        st.pyplot(fig)

with tab_temp:
    left, right = st.columns([1, 3], gap="large")
    with left:
        st.markdown('<div class="tab-sidebar">', unsafe_allow_html=True)
        st.markdown("#### Temperature Controls")
        temp_scope = st.selectbox(
            "Scope",
            ["Global", "Country", "State", "City", "Major City"],
            index=0,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    scope_to_dir = {
        "Global": "global_temp_graph",
        "Country": "countries_temp_graph",
        "State": "states_temp_graph",
        "City": "cities_temp_graph",
        "Major City": "major_cities_temp_graph",
    }
    graphs_dir = Path("output") / scope_to_dir[temp_scope]
    with right:
        st.subheader("Temperature")
        if graphs_dir.exists():
            graph_files = sorted(graphs_dir.glob("*.png"))
            if graph_files:
                file_names = [p.stem for p in graph_files]
                selected_name = st.selectbox("Graph", file_names, index=0)
                selected_path = graphs_dir / f"{selected_name}.png"
                st.image(str(selected_path), use_container_width=True)
            else:
                st.info(f"No PNG graphs found in `{graphs_dir}`.")
        else:
            st.info(f"Missing graphs folder: `{graphs_dir}`.")

with tab_emissions:
    left, right = st.columns([1, 3], gap="large")
    with left:
        st.markdown('<div class="tab-sidebar">', unsafe_allow_html=True)
        st.markdown("#### Emissions Controls")
        st.selectbox("Metric", ["CO2", "CH4", "N2O"], index=0)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.subheader("Emissions")
        st.write("Add emissions time series and country comparisons here.")

with tab_about:
    left, right = st.columns([1, 3], gap="large")
    with left:
        st.markdown('<div class="tab-sidebar">', unsafe_allow_html=True)
        st.markdown("#### About")
        st.markdown('<p>Project info and data sources.</p>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.subheader("About")
        st.write("This dashboard uses Google Earth Engine for geospatial analysis.")
