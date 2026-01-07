import functools
import rasterio
import rasterio.mask
import zipfile
import geopandas as gpd

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
