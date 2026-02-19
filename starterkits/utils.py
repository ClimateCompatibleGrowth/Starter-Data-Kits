import functools
import os
from pathlib import Path
import rasterio
import rasterio.mask
from rasterio.merge import merge
import zipfile
import geopandas as gpd
from osgeo import gdal
import earthaccess

def authenticate_nasa_earth(username=None, password=None):
    # Authenticate
    if username and password:
        # Create the .netrc file that earthaccess/GDAL/curl look for
        netrc_content = f"machine urs.earthdata.nasa.gov login {username} password {password}\n"
        with open(Path.home() / ".netrc", "w") as f:
            f.write(netrc_content)
        os.chmod(Path.home() / ".netrc", 0o600) # Set proper permissions
        try:
            earthaccess.login(persistent=True)
            return True
        except ex:
           print('No username or password provided for Nasa Earthaccess, the landcover and elevation data will be skiped.')
           return False

def handle_exceptions(func):
    """
    Decorator that wraps the function in a try-except block
    and provides feedback on any exceptions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error executing {func.__name__}, this is often due to server unavailability please try againlater: {e}")
            return None
    return wrapper

def mask_raster_with_geometry(raster_path, shapes, output_path):
    """
    Mask a raster using a list of geometries or a GeoDataFrame.
    
    Args:
        raster_path (str): Path to the input raster file.
        shapes (list or GeoDataFrame): List of geometries or a GeoDataFrame to mask the raster.
                                       The geometries must be in the same CRS as the raster.
        output_path (str): Path to save the masked raster.
    """
    if isinstance(shapes, str):
        shapes = gpd.read_file(shapes)
        shapes = shapes.geometry.values
    elif isinstance(shapes, gpd.GeoDataFrame):
        shapes = shapes.geometry.values
    elif isinstance(shapes, list):
        pass
    else:
        raise ValueError("shapes must be a GeoDataFrame or a path to a GeoDataFrame")

    with rasterio.open(raster_path) as src:
        out_image, out_transform = rasterio.mask.mask(src, shapes, crop=True)
        out_meta = src.meta.copy()

    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)
    
    print(f"Masked raster saved to {output_path}")

def merge_rasters(raster_paths, output_path, method='gdal'):
    """
    Merge multiple rasters into a single file.

    Args:
        raster_paths (list): List of paths to the raster files to merge.
        output_path (str): Path to save the merged raster.
        method (str): Method to use for merging ('gdal' or 'rasterio'). Default is 'gdal'.
    """
    if not raster_paths:
        return

    if method == 'gdal':
        print(f"Merging {len(raster_paths)} rasters into {output_path} using GDAL (In-memory VRT)")
        vrt = gdal.BuildVRT('', raster_paths)
        gdal.Translate(output_path, vrt)
        vrt = None
    elif method == 'rasterio':
        print(f"Merging {len(raster_paths)} rasters into {output_path} using Rasterio (Sequential mode)")
        
        # Start with the first raster
        current_mosaic_path = raster_paths[0]
        temp_files = []

        for i in range(1, len(raster_paths)):
            next_raster_path = raster_paths[i]
            
            # Define a temporary path for the intermediate merge result
            temp_out = output_path.replace('.tif', f'_temp_merge_{i}.tif')
            temp_files.append(temp_out)
            
            with rasterio.open(current_mosaic_path) as src1, rasterio.open(next_raster_path) as src2:
                mosaic, out_trans = merge([src1, src2])
                out_meta = src1.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": out_trans
                })
                
                with rasterio.open(temp_out, "w", **out_meta) as dest:
                    dest.write(mosaic)
            
            current_mosaic_path = temp_out

        # Move the final intermediate file to the final output path
        # OR if there was only 1 raster, just copy it/save it
        if len(raster_paths) == 1:
            with rasterio.open(raster_paths[0]) as src:
                out_meta = src.meta.copy()
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(src.read())
        else:
            # The last temp file is our final result
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(current_mosaic_path, output_path)
            temp_files.remove(current_mosaic_path)

        # Cleanup temporary merge files
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
    else:
        raise ValueError("Method must be 'gdal' or 'rasterio'")
    
    print(f"Merged rasters saved to {output_path}")

def unzip_file(zip_path, extract_to):
    """
    Unzip a file to a destination directory.

    Args:
        zip_path (str): Path to the zip file.
        extract_to (str): Directory to extract files to.
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted {zip_path} to {extract_to}")
