# Forest Loss Analysis (India)

A small project to analyze forest cover change using Google Earth Engine (GEE) and geospatial tools. It computes forest area, annual loss/gain statistics, and visualizes results using interactive maps and plots.

## Contents
- [Notebooks](notebooks/forest_loss_analysis.ipynb), [forest.ipynb](forest.ipynb) — reproducible analyses and visualizations.
- [src/](src/) — helper modules and scripts (configuration).
- [src/config.py](src/config.py) — project configuration values such as dataset and project identifiers.
- [forest_analysis.log](forest_analysis.log) — example log output from notebook runs.

## Quickstart

1. Install dependencies:
   pip install -r requirements.txt

2. Configure GEE:

Update the project and dataset in the config files if needed. See src.config.project_name and src.config.dataset_name (also mirrored in config/config.py).
3. Run the notebooks:

Open notebooks/forest_loss_analysis.ipynb in JupyterLab / Jupyter Notebook.
The notebooks authenticate with Earth Engine and produce logs saved to forest_analysis.log.

## Important configuration
Dataset used: value in src.config.dataset_name
GEE project: value in src.config.project_name
Adjust these values in src/config.py before running long queries.

## Notable files
notebooks/forest_loss_analysis.ipynb — main analysis notebook (interactive map, yearly loss calculations).

## Logging & outputs
Notebooks configure logging to both stdout and the file forest_analysis.log. Plots and interactive maps are produced by matplotlib and geemap.

## Notes
The notebooks perform large-area GEE reduceRegion operations — expect long runtimes for national-scale queries.
Use maxPixels and bestEffort options in GEE calls as shown in the notebooks to avoid request rejections.