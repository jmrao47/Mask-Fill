#!/Users/jrao/anaconda3/envs/mask_fill_env/bin/python3.7

import numpy as np
import gdal
import rasterio
import rasterio.mask
from osgeo import osr
from osgeo import gdal_array
import MaskFill


""" Performs a mask fill on the given GeoTIFF using the shapes in the given shapefile. 
    Writes the resulting GeoTIFF to output_dir.

    Args:
        geotiff_path (str): The path to the GeoTIFF 
        shape_path (str): The path to the shape file 
        output_dir (str): The path to the output directory
        default_fill_value (float): The fill value used for the mask fill if the GeoTIFF has no fill value
    
    Returns:
        str: The path to the output GeoTIFF file
"""
def produce_masked_geotiff(geotiff_path, shape_path, output_dir, default_fill_value):
    mask_array = get_mask_array(geotiff_path, shape_path)

    # Perform mask fill
    raster_arr, fill_value = gdal_array.LoadFile(geotiff_path), get_fill_value(geotiff_path, default_fill_value)
    out_image = MaskFill.mask_fill_array(raster_arr, mask_array, fill_value)
    out_image = np.array([out_image])

    # Output file with proper metadata
    output_path = MaskFill.get_masked_file_path(geotiff_path, output_dir)
    out_meta = rasterio.open(geotiff_path).meta.copy()
    out_meta.update({"driver": "GTiff", "height": out_image.shape[1], "width": out_image.shape[2]})
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(out_image)

    return MaskFill.get_masked_file_path(geotiff_path, output_dir)


""" Rasterizes the shapes in the given shape file to create a mask array for the given GeoTIFF.

    Args:
        geotiff_path (str): The GeoTIFF for which a mask array will be created
        shape_path (str): The path to the shape file which will be rasterized

    Returns:
        numpy.ndarray: A numpy array representing the rasterized shapes from the shape file
"""
def get_mask_array(geotiff_path, shape_path):
    projected_shapes = MaskFill.get_projected_shapes(get_geotiff_proj4(geotiff_path), shape_path)
    raster = rasterio.open(geotiff_path)
    return MaskFill.get_mask_array(projected_shapes, raster.read(1).shape, raster.transform)


""" Returns the proj4 string corresponding to the coordinate reference system of the GeoTIFF file.

    Args:
        geotiff_path (str): The path to the GeoTIFF file

    Returns:
        str: The proj4 string corresponding to the given file
"""
def get_geotiff_proj4(geotiff_path):
    data = gdal.Open(geotiff_path)
    proj_text = data.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(proj_text)
    return srs.ExportToProj4()


""" Returns the fill value for the given GeoTIFF. 
    If the GeoTIFF has no fill value, returns the given default fill value.

    Args:
        geotiff_path (str): The path to a GeoTIFF file
        default_fill_value (float): The default value which is returned if no fill value is found in the GeoTIFF

    Returns:
        float: The fill value
"""
def get_fill_value(geotiff_path, default_fill_value):
    raster = gdal.Open(geotiff_path)
    fill_value = raster.GetRasterBand(1).GetNoDataValue()
    if fill_value is None: fill_value = default_fill_value
    return fill_value













