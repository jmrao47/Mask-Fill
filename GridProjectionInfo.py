from pyproj import CRS
import affine


""" Returns the proj4 string corresponding to the coordinate reference system of the HDF5 dataset.

    Args:
         h5_dataset (h5py._hl.dataset.Dataset): The HDF5 dataset

    Returns:
        str: The proj4 string corresponding to the given dataset
"""
def get_hdf_proj4(h5_dataset):
    dimensions = get_dimension_datasets(h5_dataset)
    units = dimensions[0].attrs['units'].decode()

    if 'degrees' in units:
        # Geographic proj4 string
        return "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

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

    if 'DIMENSION_LIST' in h5_dataset.attrs:
        dim_list = h5_dataset.attrs['DIMENSION_LIST']

        for ref in dim_list:
            dim = file[ref[0]]
            if len(dim[:]) == h5_dataset.shape[0]: y = dim
            if len(dim[:]) == h5_dataset.shape[1]: x = dim
        return x, y


""" Returns the proj4 string corresponding to a grid mapping dataset

    Args:
        grid_mapping (h5py._hl.dataset.Dataset): A dataset containing CF parameters for a coordinate reference system

    Returns:
        str: The proj4 string corresponding to the grid mapping
"""
def get_proj4(grid_mapping):
    cf_parameters = dict(grid_mapping.attrs)
    decode_bytes(cf_parameters)

    dictionary = CRS.from_cf(cf_parameters).to_dict()
    dictionary['lat_ts'] = cf_parameters['standard_parallel']

    return CRS.from_dict(dictionary).to_proj4()


""" Decodes all byte values in the dictionary.

    Args: 
        dictionary (dict): A dictionary whose values may be byte objects
"""
def decode_bytes(dictionary):
    for key, value in dictionary.items():
        if isinstance(value, bytes): dictionary[key] = value.decode()


""" Determines the transform from the image coordinates of the HDF5 dataset to  world coordinates in the 
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
    Note: the cell height may be negative.

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
