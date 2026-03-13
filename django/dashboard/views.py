import json
import logging
import base64
import io
from pathlib import Path

from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def _init_gee():
    """Initialize Google Earth Engine. Returns (ee, dataset) or (None, None) on failure."""
    try:
        import ee
        try:
            ee.Initialize()
        except Exception:
            if settings.GEE_SERVICE_ACCOUNT and settings.GEE_KEY_FILE:
                credentials = ee.ServiceAccountCredentials(
                    settings.GEE_SERVICE_ACCOUNT, settings.GEE_KEY_FILE
                )
                ee.Initialize(credentials)
            else:
                raise
        dataset = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')
        return ee, dataset
    except Exception as exc:
        logger.warning(f"GEE unavailable: {exc}")
        return None, None


def index(request):
    """Main dashboard view."""
    return render(request, 'dashboard/index.html')


@csrf_exempt
@require_http_methods(["POST"])
def forest_stats_api(request):
    """
    POST body JSON:
    {
        "start_year": 2010,
        "end_year": 2015,
        "geojson": null | {...}   // drawn ROI or null for global
    }
    Returns forest stats + base64-encoded loss chart.
    """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    start_year = int(body.get('start_year', 2010))
    end_year = int(body.get('end_year', 2015))
    geojson = body.get('geojson', None)

    ee, dataset = _init_gee()
    if ee is None:
        return JsonResponse({'error': 'Google Earth Engine is not configured or unavailable.'}, status=503)

    try:
        treecover2000 = dataset.select('treecover2000')
        loss = dataset.select('loss')
        gain = dataset.select('gain')
        lossyear = dataset.select('lossyear')

        # Build ROI geometry
        if geojson:
            geometries = []
            if isinstance(geojson, list):
                for f in geojson:
                    if 'geometry' in f:
                        geometries.append(ee.Geometry(f['geometry']))
            elif isinstance(geojson, dict):
                if geojson.get('type') == 'FeatureCollection':
                    for f in geojson['features']:
                        if 'geometry' in f:
                            geometries.append(ee.Geometry(f['geometry']))
                elif 'geometry' in geojson:
                    geometries.append(ee.Geometry(geojson['geometry']))
                else:
                    geometries.append(ee.Geometry(geojson))

            if geometries:
                roi_geom = (
                    geometries[0] if len(geometries) == 1
                    else ee.FeatureCollection([ee.Feature(g) for g in geometries]).union().geometry()
                )
            else:
                roi_geom = ee.Geometry.BBox(-180, -90, 180, 90)
        else:
            roi_geom = ee.Geometry.BBox(-180, -90, 180, 90)

        scale = 30000
        forest_mask = treecover2000.gt(0)
        forest_area = treecover2000.updateMask(forest_mask).multiply(ee.Image.pixelArea())
        forest_area_val = forest_area.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi_geom, scale=scale, maxPixels=1e9
        ).getInfo()

        year_mask = lossyear.gte(start_year - 2000).And(lossyear.lte(end_year - 2000))
        loss_area = loss.updateMask(year_mask).multiply(ee.Image.pixelArea())
        loss_area_val = loss_area.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi_geom, scale=scale, maxPixels=1e9
        ).getInfo()

        gain_area = gain.updateMask(gain).multiply(ee.Image.pixelArea())
        gain_area_val = gain_area.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=roi_geom, scale=scale, maxPixels=1e9
        ).getInfo()

        # Yearly breakdown
        yearly_loss = {}
        for y in range(start_year, end_year + 1):
            ymask = lossyear.eq(y - 2000)
            ya = loss.updateMask(ymask).multiply(ee.Image.pixelArea())
            val = ya.reduceRegion(
                reducer=ee.Reducer.sum(), geometry=roi_geom, scale=scale, maxPixels=1e9
            ).getInfo()
            yearly_loss[str(y)] = (val.get('loss', 0) or 0) / 10000

        # Generate chart as base64 PNG
        chart_b64 = _generate_loss_chart(yearly_loss, start_year, end_year)

        return JsonResponse({
            'forest_area_ha': (forest_area_val.get('treecover2000', 0) or 0) / 10000,
            'loss_area_ha': (loss_area_val.get('loss', 0) or 0) / 10000,
            'gain_area_ha': (gain_area_val.get('gain', 0) or 0) / 10000,
            'yearly_loss': yearly_loss,
            'chart_b64': chart_b64,
        })

    except Exception as exc:
        logger.exception('Error computing forest stats')
        return JsonResponse({'error': str(exc)}, status=500)


def _generate_loss_chart(yearly_loss: dict, start_year: int, end_year: int) -> str:
    """Return a base64-encoded PNG of the yearly forest loss bar chart."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        years = [str(y) for y in range(start_year, end_year + 1)]
        values = [yearly_loss.get(str(y), 0) for y in range(start_year, end_year + 1)]

        fig, ax = plt.subplots(figsize=(9, 4), facecolor='#0f172a')
        ax.set_facecolor('#1e293b')
        bars = ax.bar(years, values, color='#ef4444', width=0.6, zorder=3)
        ax.set_xlabel('Year', color='#94a3b8', fontsize=11)
        ax.set_ylabel('Forest Loss (ha)', color='#94a3b8', fontsize=11)
        ax.set_title(f'Yearly Forest Loss {start_year}–{end_year}', color='#f1f5f9', fontsize=13, pad=12)
        ax.tick_params(colors='#94a3b8')
        ax.spines[:].set_color('#334155')
        ax.yaxis.grid(True, color='#334155', linestyle='--', alpha=0.6, zorder=0)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    except Exception as exc:
        logger.warning(f'Chart generation failed: {exc}')
        return ''


@require_http_methods(["GET"])
def graphs_api(request):
    """
    Returns list of available graph PNGs and HTML files from the output directory.
    ?scope=global_temp_graph  (optional subfolder)
    """
    scope = request.GET.get('scope', '')
    output_root = Path(settings.MEDIA_ROOT)

    scope_dirs = {
        'global_temp': 'global_temp_graph',
        'country_temp': 'countries_temp_graph',
        'state_temp': 'states_temp_graph',
        'city_temp': 'cities_temp_graph',
        'major_city_temp': 'major_cities_temp_graph',
        'global_co2': 'global_co2_concentration_graph',
        'country_co2': 'countries_co2_emission_graph',
    }

    result = {}
    for key, folder in scope_dirs.items():
        graphs_dir = output_root / folder
        if graphs_dir.exists():
            files = sorted(graphs_dir.glob('*.png'))
            result[key] = [
                {'name': f.stem, 'url': f'{settings.MEDIA_URL}{folder}/{f.name}'}
                for f in files
            ]
        else:
            result[key] = []

    # HTML files
    html_files = sorted(output_root.glob('*.html'))
    result['html_files'] = [
        {'name': f.name, 'url': f'{settings.MEDIA_URL}{f.name}'}
        for f in html_files
    ]

    return JsonResponse(result)