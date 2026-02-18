import os
import pycountry
import pygadm
import osmnx as ox
import time
import requests
import math
import earthaccess
from .utils import handle_exceptions, mask_raster_with_geometry, unzip_file, merge_rasters


def download_file(url, path, name):
    """
    Download a file from an http url.

    Args:
        url (str): The URL to download from.
        path (str): The local path to save the file.
        name (str): The name of the dataset being downloaded.
    """
    print(f"Downloading {name} from: ", url)
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {name} to {path}")

def log(msg, start_time):
    """Print message with elapsed time since start."""
    elapsed = time.time() - start_time
    print(f"[{elapsed:6.1f} sec] {msg}")

@handle_exceptions
def get_specs(country):
    """
    Download OnSSET specifications for a country.

    Args:
        country (str): ISO3 country code.
    """
    os.makedirs(f'Data/{country}/Specs', exist_ok=True)
    download_file(f'https://geospatialsdk.s3.amazonaws.com/OnSSET_specs/{country}_data.yaml', f'Data/{country}/Specs/{country}_data.yaml', 'Specs')

@handle_exceptions
def get_boundaries(country):
    """
    Download administrative boundaries (level 0) for a country.

    Args:
        country (str): ISO3 country code.
    """
    os.makedirs(f'Data/{country}/Boundaries', exist_ok=True)
    print(f"Getting boundaries for {country}")
    boundaries = pygadm.Items(admin=country, content_level=0)
    boundaries.crs = 4326
    boundaries.to_file(f'Data/{country}/Boundaries/{country}_adm_0.gpkg')
    print(f"Downloaded: {country} boundaries to Data/{country}/Boundaries/{country}_adm_0.gpkg")

@handle_exceptions
def get_population_data(country, resolution, year=2025):
    """
    Download population data for a country at a specific resolution.

    Args:
        country (str): ISO3 country code.
        resolution (str): The resolution of the data (e.g., '1km').
    """
    os.makedirs(f'Data/{country}/Population', exist_ok=True)
    if resolution == '1km':
      download_file(f'https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{year}/{country}/v1/1km_ua/constrained/{country.lower()}_pop_{year}_CN_1km_R2025A_UA_v1.tif', f'Data/{country}/Population/{country}_{year}_pop_r{resolution}.tif', 'Population')
    elif resolution == '100m':
      download_file(f'https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{year}/{country}/v1/100m/constrained/{country.lower()}_pop_{year}_CN_100m_R2025A_v1.tif', f'Data/{country}/Population/{country}_{year}_pop_r{resolution}.tif', 'Population')

@handle_exceptions
def get_power_lines(country):
    """
    Download MV power lines data.

    Args:
        country (str): ISO3 country code.
    """
    os.makedirs(f'Data/{country}/MV lines', exist_ok=True)
    download_file(f'https://geospatialsdk.s3.amazonaws.com/Power_network/Gridfinder/{country}_mv_lines.gpkg', f'Data/{country}/MV lines/{country}_mv_lines.gpkg', 'Power lines')

@handle_exceptions
def get_wind_data(country, height):
    """
    Download wind speed data for a country at a specific height.

    Args:
        country (str): ISO3 country code.
        height (str): The height for wind speed data.
    """
    os.makedirs(f'Data/{country}/Wind speed', exist_ok=True)
    download_file(f'https://globalwindatlas.info/api/gis/country/{country}/wind-speed/{height}', f'Data/{country}/Wind speed/{country}_wind_speed_{height}.tif', 'Wind speed')
    mask_raster_with_geometry(f'Data/{country}/Wind speed/{country}_wind_speed_{height}.tif', f'Data/{country}/Boundaries/{country}_adm_0.gpkg', f'Data/{country}/Wind speed/{country}_wind_speed_{height}.tif')

@handle_exceptions
def get_solar_data(country):
    """
    Download solar irradiation data for a country.

    Args:
        country (str): ISO3 country code.
    """
    os.makedirs(f'Data/{country}/Solar irradiation', exist_ok=True)
    if country == 'COG':
      country_name = 'Republic of the Congo'
    elif country == 'COD':
      country_name = 'Democratic Republic of the Congo'
    elif country == 'CIV':
      country_name = 'Cote d Ivoire'
    else:
      country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
    download_file(f"https://api.globalsolaratlas.info/download/{country_name}/{country_name.replace(' ', '-')}_GISdata_LTAym_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip", f'Data/{country}/Solar irradiation/{country}_solar_irradiance.zip', 'Solar irradiation')
    unzip_file(f'Data/{country}/Solar irradiation/{country}_solar_irradiance.zip', f'Data/{country}/Solar irradiation')
  
@handle_exceptions
def get_dem_data(country, api_key='demoapikeyot2022', dem_type='SRTMGL3'):
    """
    Download Digital Elevation Model (DEM) data for a country.

    Args:
        country (str): ISO3 country code.
        api_key (str): API key for OpenTopography.
        dem_type (str): Type of DEM to download, choose from: SRTMGL3, SRTMGL1, SRTMGL1_E, AW3D30, AW3D30_E, SRTM15Plus, NASADEM, COP30, COP90, EU_DTM, GEDI_L3, GEBCOIceTopo, GEBCOSubIceTopo, CA_MRDEM_DSM, CA_MRDEM_DTM
    """
    os.makedirs(f'Data/{country}/Elevation', exist_ok=True)
    boundaries = pygadm.Items(admin=country, content_level=0)
    boundaries.crs = 4326
    west, south, east, north = boundaries.total_bounds
    
    # Estimate area of the bounding box in km2
    avg_lat = (south + north) / 2
    height_deg = north - south
    width_deg = east - west
    height_km = height_deg * 111
    width_km = width_deg * 111 * math.cos(math.radians(avg_lat))
    area_km2 = height_km * width_km
    
    output_path = f'Data/{country}/Elevation/{country}_dem.tif'
    limit_km2 = 450000
    
    if area_km2 > limit_km2:
        num_parts = math.ceil(area_km2 / limit_km2)
        print(f"Area is large ({area_km2:.0f} km2), splitting into {num_parts} regions.")
        
        lat_step = height_deg / num_parts
        part_paths = []
        
        for i in range(num_parts):
            p_south = south + i * lat_step
            p_north = south + (i + 1) * lat_step
            # Handle potential floating point issues on the last part
            if i == num_parts - 1:
                p_north = north
                
            p_path = f'Data/{country}/Elevation/{country}_dem_part{i+1}.tif'
            p_url = f'https://portal.opentopography.org/API/globaldem?demtype={dem_type}&south={p_south}&north={p_north}&west={west}&east={east}&outputFormat=GTiff&API_Key={api_key}'
            
            download_file(p_url, p_path, f'Elevation Part {i+1}')
            part_paths.append(p_path)
        
        merge_rasters(part_paths, output_path)
        
        # Cleanup
        for p in part_paths:
            if os.path.exists(p):
                os.remove(p)
    else:
        url = f'https://portal.opentopography.org/API/globaldem?demtype=NASADEM&south={south}&north={north}&west={west}&east={east}&outputFormat=GTiff&API_Key={api_key}'
        download_file(url, output_path, 'Elevation')

@handle_exceptions
def get_ntl_data(country):
    """
    Download Nighttime Lights (NTL) data for a country.

    Args:
        country (str): ISO3 country code.
    """
    os.makedirs(f'Data/{country}/Nighttime lights', exist_ok=True)
    download_file(f'https://data.worldpop.org/GIS/Covariates/Global_2015_2030/{country}/VIIRS/v1/fvf//{country.lower()}_viirs_fvf_2023_100m_v1.tif', f'Data/{country}/Nighttime lights/{country}_ntl.tif', 'Nighttime lights')

@handle_exceptions
def get_roads(country): #, road_types):
    """
    Download and process road network data for a country.

    Args:
        country (str): ISO3 country code.
        road_types (list): List of OSM highway types to include.
    """
    os.makedirs(f'Data/{country}/Roads', exist_ok=True)
    download_file(f'https://geospatialsdk.s3.amazonaws.com/Roads/Country/{country}_roads.gpkg', f'Data/{country}/Roads/{country}_roads.gpkg', 'Roads')
    # os.makedirs(f'Data/{country}/Roads', exist_ok=True)
    # output_dir = f'Data/{country}/Roads'
    # country_start = time.time()
    # # Get country name from ISO3
    # country_name = pycountry.countries.get(alpha_3=country).name # type: ignore
    # log(f"Getting roads for {country_name} ({country})", country_start)

    # # Download road network as GeoDataFrame (edges only)
    # G = ox.graph_from_place(country_name, network_type="drive")
    # gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

    # # Filter by the desired highway types
    # gdf_edges = gdf_edges[gdf_edges["highway"].isin(road_types)]
    # log(f"Found {len(gdf_edges)} road segments.", country_start)

    # # Define output path
    # out_path = os.path.join(output_dir, f"{country}_roads.gpkg")

    # # Save shapefile
    # if len(gdf_edges) > 0:
    #     gdf_edges.to_file(out_path)
    #     log(f"Saved file to: {out_path}", country_start)
    # else:
    #     log("No roads found with the selected filters. Nothing saved.", country_start)


@handle_exceptions
def get_landcover_data(country, year=2022, username=None, password=None):
    """
    Download MODIS Land Cover Type 1 (MCD12Q1) data for a country.
    
    Args:
        country (str): ISO3 country code.
        year (int): Year of data to download.
        username (str): Earthdata username.
        password (str): Earthdata password.
    """
    print(f"Getting land cover data for {country}")
    # Authenticate
    if username and password:
        earthaccess.login(username=username, password=password)
    else:
        earthaccess.login(strategy="interactive")
        
    os.makedirs(f'Data/{country}/Land cover', exist_ok=True)
    
    boundaries = pygadm.Items(admin=country, content_level=0)
    boundaries.crs = 4326
    
    # Get bounding box
    bbox = tuple(boundaries.total_bounds)
    
    results = earthaccess.search_data(
        short_name='MCD12Q1',
        bounding_box=bbox,
        temporal=(f"{year}-01-01", f"{year}-12-31")
    )
    
    if not results:
        print(f"No MODIS data found for {country} in {year}")
        return

    earthaccess.download(results, f'Data/{country}/Land cover')
    print(f"Downloaded MODIS land cover data to Data/{country}/Land cover")
