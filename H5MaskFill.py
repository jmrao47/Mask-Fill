import os
import shutil
from rasterio.plot import show
import numpy as np
import h5py
import MaskFill
import hashlib
import GridProjectionInfo


mask_grid_cache_values = ['ignore_and_delete',
                          'ignore_and_save',
                          'use_cache',
                          'use_and_save',
                          'use_cache_delete',
                          'maskgrid_only']


""" Creates a mask filled version of the given HDF5 file using the given shapefile. Outputs the new HDF5 file to the
    given output directory. 

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): Path to a shape file used to create the mask array for the mask fill
        output_dir (str): The path to the output directory
        cache_dir (str): The path to a cache directory 
        mask_grid_cache (str): Value determining whether to use previously cached mask arrays and whether to cache newly 
                               created mask arrays
        default_fill_value (float): The default fill value for the mask fill if no other fill values are provided
        
    Returns:
        str: The path to the output HDF5 file
"""
def produce_masked_hdf(hdf_path, shape_path, output_dir, mask_grid_cache, default_fill_value):
    mask_grid_cache = mask_grid_cache.lower()
    cache_dir = output_dir
    saved_mask_arrays = dict()

    if mask_grid_cache == 'maskgrid_only':
        process_file(hdf_path, mask_fill, shape_path, cache_dir, mask_grid_cache, default_fill_value, saved_mask_arrays)
    else:
        new_file_path = MaskFill.get_masked_file_path(hdf_path, output_dir)
        shutil.copy(hdf_path, new_file_path)
        process_file(new_file_path, mask_fill, shape_path, cache_dir, mask_grid_cache, default_fill_value, saved_mask_arrays)

    if mask_grid_cache.__contains__('save') or mask_grid_cache == 'maskgrid_only':
        for mask_id, mask_array in saved_mask_arrays.items():
            mask_array_path = get_mask_array_path(mask_id, cache_dir)
            np.save(mask_array_path, mask_array)

    if mask_grid_cache == 'maskgrid_only': return None
    return MaskFill.get_masked_file_path(hdf_path, output_dir)


""" Performs the given process on all objects in the HDF5 file.

    Args:
        file_path (str): The path to the input HDF5 file
        process (function): The process to be performed on the objects in the file
        *args: The arguments passed to the process
"""
def process_file(file_path, process, *args):
    def process_children(obj, process, *args):
        for name, child in obj.items():
            if isinstance(child, h5py._hl.group.Group):
                process_children(child, process, *args)

            elif isinstance(child, h5py._hl.dataset.Dataset):
                process(child, *args)

    with h5py.File(file_path, mode='r+') as file:
        process_children(file, process, *args)


""" Replaces the data in the HDF5 dataset with a mask filled version of the data. 

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): Path to a shape file used to create the mask array for the mask fill
        cache_dir (str): The path to a cache directory 
        mask_grid_cache (str): Value determining how the mask arrays used in the mask fill are created and cached
        default_fill_value (float): The default fill value for the mask fill if no other fill values are provided
"""
def mask_fill(h5_dataset, shape_path, cache_dir, mask_grid_cache, default_fill_value, saved_mask_arrays):
    # Ensure dataset has at least two dimensions and can be mask filled
    if len(h5_dataset.shape) != 2: return
    show(h5_dataset[:], title="Original " + h5_dataset.name)

    # Perform mask fill and write the new mask filled data to the h5_dataset
    mask_array = get_mask_array(h5_dataset, shape_path, cache_dir, mask_grid_cache, saved_mask_arrays)
    if mask_grid_cache != 'maskgrid_only':
        fill_value = get_fill_value(h5_dataset, default_fill_value)
        mask_filled_data = MaskFill.mask_fill_array(h5_dataset[:], mask_array, fill_value)
        h5_dataset.write_direct(mask_filled_data)

        show(mask_filled_data, title="Mask Filled " + h5_dataset.name)

        # Get all values in mask_filled_data excluding the fill value
        data = mask_filled_data[mask_filled_data != fill_value]

        # Update statistics in the h5_dataset
        if h5_dataset.attrs.__contains__('observed_max'): h5_dataset.attrs.modify('observed_max', max(data))
        if h5_dataset.attrs.__contains__('observed_min'): h5_dataset.attrs.modify('observed_min', min(data))
        if h5_dataset.attrs.__contains__('observed_mean'): h5_dataset.attrs.modify('observed_mean', np.mean(data))


""" Retrieves the mask array corresponding the HDF5 file and shape file from the cache directory. 
    If the mask array file does not already exist, it is created. 

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): The path to the shapefile used to create the mask array
        cache_dir (str): The path to the directory where the mask array file is cached
"""
def get_mask_array(h5_dataset, shape_path, cache_dir, mask_grid_cache, saved_mask_arrays):
    mask_id = get_mask_array_id(h5_dataset, shape_path)
    if mask_id in saved_mask_arrays: return saved_mask_arrays[mask_id]

    mask_array_path = get_mask_array_path(mask_id, cache_dir)
    if mask_grid_cache.__contains__('use') and os.path.exists(mask_array_path): mask_array = np.load(mask_array_path)
    else: mask_array = create_mask_array(h5_dataset, shape_path)

    saved_mask_arrays[mask_id] = mask_array
    return mask_array


def get_mask_array_id(h5_dataset, shape_path):
    # The mask array is determined by the CRS of the dataset, the dataset's transform, and the shapes used in the mask
    mask_id = str(GridProjectionInfo.get_hdf_proj4(h5_dataset)) + str(GridProjectionInfo.get_transform(h5_dataset)) \
              + str(h5_dataset[:].shape) + shape_path
    # Hash mask_id
    mask_id = hashlib.sha224(mask_id.encode()).hexdigest()
    return mask_id


""" Returns the path to the file containing a mask array corresponding to the given HDF5 dataset.

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        cache_dir (str): The directory in which mask arrays are cached

    Returns:
        str: The path to the mask array file 
"""
def get_mask_array_path(mask_id, cache_dir):
    return os.path.join(cache_dir, mask_id + ".npy")


""" Creates a mask array corresponding to the HDF5 dataset and shape file

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): The path to the shapefile used to create the mask array

    Returns:
        numpy.ndarray: The mask array
"""
def create_mask_array(h5_dataset, shape_path):
    proj4 = GridProjectionInfo.get_hdf_proj4(h5_dataset)
    shapes = MaskFill.get_projected_shapes(proj4, shape_path)
    raster_arr = h5_dataset[:]
    transform = GridProjectionInfo.get_transform(h5_dataset)

    return MaskFill.get_mask_array(shapes, raster_arr.shape, transform)


""" Returns the fill value for the given HDF5 dataset. 
    If the HDF5 dataset has no fill value, returns the given default fill value.

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        default_fill_value (float): The default value which is returned if no fill value is found in the dataset

    Returns:
        float: The fill value
"""
def get_fill_value(h5_dataset, default_fill_value):
    if h5_dataset.attrs.__contains__('_FillValue'): return h5_dataset.attrs['_FillValue']
    return default_fill_value
