import os
import pycountry
import pygadm
import osmnx as ox
import time

def log(msg, start_time):
    """Print message with elapsed time since start."""
    elapsed = time.time() - start_time
    print(f"[{elapsed:6.1f} sec] {msg}")

def get_specs(country):
  os.makedirs(f'Data/{country}/Specs', exist_ok=True)
  country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
  !wget 'https://geospatialsdk.s3.amazonaws.com/OnSSET_specs/{country}_data.yaml' -O 'Data/{country}/Specs/{country}_data.yaml'

def get_boundaries(country):
  os.makedirs(f'Data/{country}/Boundaries', exist_ok=True)
  country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
  boundaries = pygadm.Items(country_name, content_level=0)
  boundaries.to_file(f'Data/{country}/Boundaries/{country}_adm_0.gpkg')

def get_population_data(country, resolution):
  os.makedirs(f'Data/{country}/Population', exist_ok=True)
  if resolution == '1km':
    !wget 'https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2023/{country}/v1/1km_ua/constrained/{country.lower()}_pop_2023_CN_1km_R2025A_UA_v1.tif' -O 'Data/{country}/Population/{country}_pop.tif'
  elif resolution == '100m':
    pass

def get_power_lines(country):
  os.makedirs(f'Data/{country}/MV lines', exist_ok=True)
  !wget 'https://zenodo.org/records/3628142/files/grid.gpkg' -O 'Data/Africa_mv_lines.gpkg'

def get_wind_data(country, height):
  os.makedirs(f'Data/{country}/Wind speed', exist_ok=True)
  !wget 'https://globalwindatlas.info/api/gis/country/{country}/wind-speed/{height}' -O 'Data/{country}/Wind speed/{country}_wind_speed_{height}.tif'

def get_solar_data(country):
  os.makedirs(f'Data/{country}/Solar irradiation', exist_ok=True)
  country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
  !wget "https://api.globalsolaratlas.info/download/{country_name}/{country_name}_GISdata_LTAym_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip" -O 'Data/{country}/Solar irradiation/{country}_solar_irradiance.tif'

def get_dem_data(country):
  os.makedirs(f'Data/{Country}/Elevation', exist_ok=True)
  country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
  boundaries = pygadm.Items(name=country_name, content_level=0)
  west, south, east, north = boundaries.total_bounds
  !wget 'https://portal.opentopography.org/API/globaldem?demtype=NASADEM&south={south}&north={north}&west={west}&east={east}&outputFormat=GTiff&API_Key=demoapikeyot2022' -O 'Data/{country}/Elevation/{country}_dem.tif'

def get_ntl_data(country):
  os.makedirs(f'Data/{Country}/Nighttime lights', exist_ok=True)
  !wget 'https://data.worldpop.org/GIS/Covariates/Global_2015_2030/{country}/VIIRS/v1/fvf//{country.lower()}_viirs_fvf_2023_100m_v1.tif' -O 'Data/{country}/Nighttime lights/{country}_ntl.tif'

def get_roads(country, road_types):
  os.makedirs(f'Data/{country}/Roads', exist_ok=True)
  output_dir = f'Data/{country}/Roads'
  country_start = time.time()
  try:
      # Get country name from ISO3
      country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
      log(f"Processing {country_name} ({country})", country_start)

      # Download road network as GeoDataFrame (edges only)
      G = ox.graph_from_place(country_name, network_type="drive")
      gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

      # Filter by the desired highway types
      gdf_edges = gdf_edges[gdf_edges["highway"].isin(road_types)]
      log(f"Found {len(gdf_edges)} road segments.", country_start)

      # Define output path
      out_path = os.path.join(output_dir, f"{country}_roads.gpkg")

      # Save shapefile
      if len(gdf_edges) > 0:
          gdf_edges.to_file(out_path)
          log(f"Saved file to: {out_path}", country_start)
      else:
          log("No roads found with the selected filters. Nothing saved.", country_start)

  except Exception as e:
      log(f"Error processing {country}: {e}", country_start)
