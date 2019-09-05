from pyproj import CRS
import affine
import logging


""" Raised when an HDF5 file does not follow CF conventions."""
class CFComplianceError(Exception):
    pass


""" Returns the proj4 string corresponding to the coordinate reference system of the HDF5 dataset.

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        str: The proj4 string corresponding to the given dataset
"""
def get_hdf_proj4(h5_dataset):
    dimensions = get_dimension_datasets(h5_dataset)
    if not dimensions[0].attrs.__contains__('units'):
        raise CFComplianceError(f'The dataset {h5_dataset.name} does not have a units attribute')

    units = dimensions[0].attrs['units'].decode()

    if 'degrees' in units:
        # Geographic proj4 string
        return "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

    if not h5_dataset.attrs.__contains__('grid_mapping'):
        raise CFComplianceError(f'The dataset is not geographically gridded and does not have a grid mapping attribute')

    grid_mapping_name = h5_dataset.attrs['grid_mapping']
    grid_mapping = h5_dataset.file[grid_mapping_name]
    return get_proj4(grid_mapping)


""" Finds the dimension scales datasets corresponding to the given HDF5 dataset.

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        tuple: x coordinate dataset, y coordinate dataset;
               both datasets are of type h5py._hl.dataset.Dataset
"""
def get_dimension_datasets(h5_dataset):
    file = h5_dataset.file
    if 'DIMENSION_LIST' not in h5_dataset.attrs:
        raise CFComplianceError(f'The dataset {h5_dataset.name} does not have a DIMENSION_LIST attribute')

    dim_list = h5_dataset.attrs['DIMENSION_LIST']
    for ref in dim_list:
        dim = file[ref[0]]
        if len(dim[:]) == h5_dataset.shape[0]: y = dim
        if len(dim[:]) == h5_dataset.shape[1]: x = dim
    return x, y


""" Returns the proj4 string corresponding to a grid mapping dataset.

    Args:
        grid_mapping (h5py._hl.dataset.Dataset): A dataset containing CF parameters for a coordinate reference system

    Returns:
        str: The proj4 string corresponding to the grid mapping
"""
def get_proj4(grid_mapping):
    cf_parameters = dict(grid_mapping.attrs)
    decode_bytes(cf_parameters)

    dictionary = CRS.from_cf(cf_parameters).to_dict()
    if 'standard_parallel' in dictionary: dictionary['lat_ts'] = cf_parameters['standard_parallel']

    return CRS.from_dict(dictionary).to_proj4()


""" Decodes all byte values in the dictionary.

    Args: 
        dictionary (dict): A dictionary whose values may be byte objects
"""
def decode_bytes(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, bytes): dictionary[key] = value.decode()


""" Determines the transform from the image coordinates of the HDF5 dataset to world coordinates in the 
    coordinate reference frame of the HDF5 dataset. See https://pypi.org/project/affine/ for more information.

    Args:
        h5_dataset (h5py._hl.dataset.Dataset): The given HDF5 dataset

    Returns: 
        affine.Affine: A transform mapping from image coordinates to world coordinates
"""
def get_transform(h5_dataset):
    cell_width, cell_height = get_cell_size(h5_dataset)
    x_min, x_max, y_min, y_max = get_corner_points(h5_dataset)
    return affine.Affine(cell_width, 0, x_min, 0, cell_height, y_max)


""" Gets the cell height and width of the gridded HDF5 dataset in the dataset's dimension scales.
    Note: the cell height is expected to be negative because the row indices of image data increase downwards.

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        tuple: cell width, cell height
"""
def get_cell_size(h5_dataset):
    x, y = get_dimension_arrays(h5_dataset)
    cell_width, cell_height = x[1] - x[0], y[1] - y[0]
    return cell_width, cell_height


""" Finds the min and max locations in both coordinate axes of the dataset. 

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        tuple: x min, x max, y min, y max
"""
def get_corner_points(h5_dataset):
    x, y = get_dimension_arrays(h5_dataset)
    cell_width, cell_height = get_cell_size(h5_dataset)

    x_min, x_max = x[0] - cell_width / 2, x[-1] + cell_width / 2
    y_min, y_max = y[-1] + cell_height / 2, y[0] - cell_height / 2

    return x_min, x_max, y_min, y_max


""" Gets the dimension scales arrays of the HDF5 dataset.

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        tuple: The x coordinate array and the y coordinate array
"""
def get_dimension_arrays(h5_dataset):
    x, y = get_dimension_datasets(h5_dataset)
    return x[:], y[:]


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
    logging.info(f'The dataset {h5_dataset.name} does not have a fill value, '
                 f'so the default fill value {default_fill_value} will be used')
    return default_fill_value
