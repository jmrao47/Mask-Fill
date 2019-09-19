import os
import hashlib
import numpy as np
import logging
from pymods import GeotiffMaskFill, H5MaskFill


mask_grid_cache_values = ['ignore_and_delete',
                          'ignore_and_save',
                          'use_cache',
                          'use_and_save',
                          'use_cache_delete',
                          'maskgrid_only']

"""
Returns cached mask array if it exists, None otherwise
"""
def get_cached_mask_array(data, shape_path, cache_dir, mask_grid_cache):
    mask_array_path = get_mask_array_path(data, shape_path, cache_dir)

    mask_array = None
    if 'use' in mask_grid_cache and os.path.exists(mask_array_path): mask_array = np.load(mask_array_path)

    return mask_array


def get_mask_array_id(data, shape_path):
    # GeoTIFF case
    if type(data) is str and data.lower().endswith('.tif'): mask_id = GeotiffMaskFill.get_mask_array_id(data, shape_path)
    # HDF5 case
    else: mask_id = H5MaskFill.get_mask_array_id(data, shape_path)

    return mask_id


""" Creates an id corresponding to the given shapefile, projection information, and shape of a dataset,
    which determine the mask array for the dataset.  

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): Path to a shape file used to create the mask array for the mask fill

    Returns:
        str: The id 
"""
def create_mask_array_id(proj_string, transform, dataset_shape, shape_file_path):
    mask_id = proj_string + str(transform) + str(dataset_shape) + shape_file_path

    # Hash the mask id and return
    mask_id = hashlib.sha224(mask_id.encode()).hexdigest()
    return mask_id


def get_mask_array_path(data, shape_path, cache_dir):
    mask_id = get_mask_array_id(data, shape_path)
    mask_array_path = get_mask_array_path_from_id(mask_id, cache_dir)
    return mask_array_path


""" Returns the path to the file containing a mask array corresponding to the given HDF5 dataset.

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        cache_dir (str): The directory in which mask arrays are cached

    Returns:
        str: The path to the mask array file 
"""
def get_mask_array_path_from_id(mask_id, cache_dir):
    return os.path.join(cache_dir, mask_id + ".npy")


def cache_mask_array(mask_array, data, shape_path, cache_dir, mask_grid_cache):
    if 'save' in mask_grid_cache or mask_grid_cache == 'maskgrid_only':
        mask_array_path = get_mask_array_path(data, shape_path, cache_dir)
        np.save(mask_array_path, mask_array)


def cache_mask_arrays(mask_arrays, cache_dir, mask_grid_cache):
    # Save mask arrays if the mask_grid_cache value requires
    if 'delete' not in mask_grid_cache:
        for mask_id, mask_array in mask_arrays.items():
            mask_array_path = get_mask_array_path_from_id(mask_id, cache_dir)
            np.save(mask_array_path, mask_array)
        logging.debug('Cached all mask arrays')