import shutil
import numpy as np
import h5py
from pymods import H5GridProjectionInfo, MaskFill, MaskFillCaching
import logging


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
def produce_masked_hdf(hdf_path, shape_path, output_dir, cache_dir, mask_grid_cache, default_fill_value):
    mask_grid_cache = mask_grid_cache.lower()
    saved_mask_arrays = dict()

    if mask_grid_cache == 'maskgrid_only':
        process_file(hdf_path, mask_fill, shape_path, cache_dir, mask_grid_cache, default_fill_value, saved_mask_arrays)
    else:
        new_file_path = MaskFill.get_masked_file_path(hdf_path, output_dir)
        shutil.copy(hdf_path, new_file_path)
        logging.debug(f'Created output file: {new_file_path}')
        process_file(new_file_path, mask_fill, shape_path, cache_dir, mask_grid_cache, default_fill_value, saved_mask_arrays)

    MaskFillCaching.cache_mask_arrays(saved_mask_arrays, cache_dir, mask_grid_cache)

    if mask_grid_cache != 'maskgrid_only': return MaskFill.get_masked_file_path(hdf_path, output_dir)


""" Performs the given process on all datasets in the HDF5 file.

    Args:
        file_path (str): The path to the input HDF5 file
        process (function): The process to be performed on the datasets in the file
        *args: The arguments passed to the process
"""
def process_file(file_path, process, *args):
    def process_children(obj, process, *args):
        for name, child in obj.items():
            # Process the children of a group
            if isinstance(child, h5py._hl.group.Group):
                process_children(child, process, *args)
            # Process datasets
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
    if len(h5_dataset.shape) != 2:
        logging.debug(f'The dataset {h5_dataset.name} is not two dimensional and cannot be mask filled')
        return

    # Get the mask array corresponding to the HDF5 dataset and the shapefile
    mask_array = get_mask_array(h5_dataset, shape_path, cache_dir, mask_grid_cache, saved_mask_arrays)

    # Perform mask fill and write the new mask filled data to the h5_dataset,
    # unless the mask_grid_cache value only requires us to create a mask array
    if mask_grid_cache != 'maskgrid_only':
        fill_value = H5GridProjectionInfo.get_fill_value(h5_dataset, default_fill_value)
        mask_filled_data = MaskFill.mask_fill_array(h5_dataset[:], mask_array, fill_value)
        h5_dataset.write_direct(mask_filled_data)

        # Get all values in mask_filled_data excluding the fill value
        unfilled_data = mask_filled_data[mask_filled_data != fill_value]

        # Update statistics in the h5_dataset
        if h5_dataset.attrs.__contains__('observed_max'): h5_dataset.attrs.modify('observed_max', max(unfilled_data))
        if h5_dataset.attrs.__contains__('observed_min'): h5_dataset.attrs.modify('observed_min', min(unfilled_data))
        if h5_dataset.attrs.__contains__('observed_mean'): h5_dataset.attrs.modify('observed_mean', np.mean(unfilled_data))

        logging.debug(f'Mask filled the dataset {h5_dataset.name}')

""" Gets the mask array corresponding the HDF5 file and shape file from a set of saved mask arrays or the cache directory.
    If the mask array file does not already exist, it is created and added to the set of saved mask arrays.

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): The path to the shapefile used to create the mask array
        cache_dir (str): The path to the directory where the mask array file is cached
        
    Returns:
        numpy.ndarray: The mask array
"""
def get_mask_array(h5_dataset, shape_path, cache_dir, mask_grid_cache, saved_mask_arrays):
    # Get the mask id which corresponds to the mask required for the HDF5 dataset and shapefile
    mask_id = get_mask_array_id(h5_dataset, shape_path)

    # If the required mask array is in the set of saved mask arrays, get and return the mask array from the set
    if mask_id in saved_mask_arrays: return saved_mask_arrays[mask_id]

    # If the required mask array has already been created and cached, and the mask_grid_cache value allows the use of
    # cached arrays, read in the cached mask array from the file
    mask_array = MaskFillCaching.get_cached_mask_array(h5_dataset, shape_path, cache_dir, mask_grid_cache)

    # Otherwise, create the mask array
    if mask_array is None: mask_array = create_mask_array(h5_dataset, shape_path)
    
    # Save and return the mask array
    saved_mask_arrays[mask_id] = mask_array
    return mask_array


""" Creates an id corresponding to the given shapefile, projection information, and shape of a dataset,
    which determine the mask array for the dataset.  
    
    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): Path to a shape file used to create the mask array for the mask fill
        
    Returns:
        str: The id 
"""
def get_mask_array_id(h5_dataset, shape_path):
    # The mask array is determined by the CRS of the dataset, the dataset's transform, the shape of the dataset,
    # and the shapes used in the mask
    proj_string = H5GridProjectionInfo.get_hdf_proj4(h5_dataset)
    transform = H5GridProjectionInfo.get_transform(h5_dataset)
    dataset_shape = h5_dataset[:].shape

    return MaskFillCaching.create_mask_array_id(proj_string, transform, dataset_shape, shape_path)


""" Creates a mask array corresponding to the HDF5 dataset and shape file

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset
        shape_path (str): The path to the shapefile used to create the mask array

    Returns:
        numpy.ndarray: The mask array
"""
def create_mask_array(h5_dataset, shape_path):
    proj4 = H5GridProjectionInfo.get_hdf_proj4(h5_dataset)
    shapes = MaskFill.get_projected_shapes(proj4, shape_path)
    raster_arr = h5_dataset[:]
    transform = H5GridProjectionInfo.get_transform(h5_dataset)

    return MaskFill.get_mask_array(shapes, raster_arr.shape, transform)



