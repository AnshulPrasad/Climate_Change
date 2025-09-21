import ee, os, logging, json
import streamlit as st
from pathlib import Path
from config import dataset_name, project_name


def init_logging():
    # Reconfigure logging to output both to notebook and to a file
    logging.basicConfig(
        level=logging.INFO,  # Set logging level to INFO
        format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
        handlers=[
            logging.FileHandler("/tmp/app.log", mode="w"),  # Save logs to file
        ],
    )


def init_gee(credentials=None, project=project_name):
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
            logging.info(f"✅ Earth Engine initialized with service account")
        except Exception as e:
            st.error(f"Failed to init Earth Engine: {e}")
            st.stop()
    else:
        logging.error(
            f"❌ No Earth Engine service key found. Please add GEE_SERVICE_KEY in HF secrets."
        )
        # fallback - try to initialize with project (will error if not authenticated)
        ee.Authenticate()
        ee.Initialize(project=project_name)


def get_forest_stats(roi, start_year=2001, end_year=2024, dataset=dataset_name):
    """Compute forest, loss, gain areas + yearly stats."""
    treecover2000 = dataset.select("treecover2000")
    loss = dataset.select("loss")
    gain = dataset.select("gain")
    lossyear = dataset.select("lossyear")

    # forest mask
    forest2000 = treecover2000.gt(30)

    # Total forest area in 2000 (m2)
    forest_area_2000 = forest2000.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=roi, scale=300, maxPixels=1e13
    )

    # Total forest loss area (2001-2024)
    loss_mask = lossyear.gte(start_year - 2000).And(lossyear.lte(end_year - 2000))
    loss_range = loss.updateMask(loss_mask)
    loss_area = loss_range.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=roi, scale=300, maxPixels=1e13
    )

    # Total forest gain area (2001-2024)
    gain_range = gain  # gain has no year band
    gain_area = gain_range.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=roi, scale=300, maxPixels=1e13
    )

    # yearly stats
    def calc_yearly_loss(year):
        """Calculate forest loss area for a given year (2001-2024)"""
        year = ee.Number(year)
        mask = lossyear.eq(year)  # loss pixels for this year
        area = mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi, scale=300, maxPixels=1e13
        )
        return ee.Feature(
            None, {"year": year.add(2000), "loss_area_m2": area.get("lossyear")}
        )

    # Generate yearly stats (2001-2024)
    years = ee.List.sequence(
        start_year - 2000, end_year - 2000
    )  # Hansen encodes loss years as 1=2001, 24=2024
    yearly_loss = ee.FeatureCollection(years.map(calc_yearly_loss))

    return {
        "forest_area_2000": forest_area_2000.getInfo(),
        "loss_area": loss_area.getInfo(),
        "gain_area": gain_area.getInfo(),
        "yearly_loss": yearly_loss.getInfo(),
    }
