import argparse
import time
import os
import GeotiffMaskFill
import H5MaskFill


""" Executable which creates a mask filled version of a data file using a shapefile.
    Applies a fill value to the data file in the areas outside of the given shapes.

    Input parameters:
        --FILE_URLS: Path to a GeoTIFF of HDF5 file 
        --SHAPEFILE: Path to a .shp shapefile
        --OUTPUT_DIR: (optional) Path to the output directory where the mask filled file will be written.
                     If not provided, the current working directory will be used.
        --MASK_GRID_CACHE: (optional) Value determining how the mask arrays used in the mask fill are created and cached.
                          If not provided, the value 'ignore_and_delete' will be used.
        --DEFAULT_FILL: (optional) The default fill value for the mask fill if no other fill values are provided.
                       If not provided, the value -9999 will be used.
"""


default_fill_value = -9999
default_mask_grid_cache = 'ignore_and_delete'


""" Performs a mask fill on the given data file using RQS agent call input parameters. 

    Returns:
        str: An ESI standard XML string for either normal (successful) completion, 
        including the download-URL for accessing the output file, or an exception response if necessary.
"""
def mask_fill():
    args = get_input_parameters()
    error_message = validate_input_parameters(args)
    if error_message is not None: return error_message

    try:
        # GeoTIFF case
        if args.input_file.lower().endswith('.tif'):
            output_file = GeotiffMaskFill.produce_masked_geotiff(args.input_file, args.shape_file, args.output_dir,
                                                                 args.fill_value)

        # HDF5 case
        if args.input_file.lower().endswith('.h5'):
            output_file = H5MaskFill.produce_masked_hdf(args.input_file, args.shape_file, args.output_dir,
                                                        args.mask_grid_cache, args.fill_value)

        return get_xml_success_response(args.input_file, args.shape_file, output_file)
    except: return get_xml_error_response()


""" Gets the input parameters using an argparse argument parser. If no input is given for certain parameters, a default 
    value is stored.
    
    Returns: 
        argparse.Namespace: A Namespace object containing all of the input parameters values
"""
def get_input_parameters():
    parser = argparse.ArgumentParser()

    parser.add_argument('--FILE_URLS', dest='input_file', help='Name of the input file to mask fill')
    parser.add_argument('--SHAPEFILE', dest='shape_file', help='Shapefile with which to perform the mask fill')
    parser.add_argument('--OUTPUT_DIR', dest='output_dir', help='Name of the output directory to put the output file',
                        default=os.getcwd())
    parser.add_argument('--MASK_GRID_CACHE', dest='mask_grid_cache',
                        help='ignore_and_delete | ignore_and_save | use_cache | use_cache_delete | MaskGrid_Only',
                        default=default_mask_grid_cache)
    parser.add_argument('--DEFAULT_FILL', dest='fill_value', help='Fill value for mask fill',
                        default=default_fill_value)

    return parser.parse_args()


""" Ensures that all required input parameters exist, and that all given parameters are valid. If not, returns an XML
    error response. Otherwise, returns None.
    
    Returns:
        str: An ESI standard XML error response if something is wrong; otherwise, None
"""
def validate_input_parameters(params):
    # Ensure that an input file and a shape file are given
    if params.input_file is None:
        error_message = "An input data file is required for the mask fill utility"
        return get_xml_error_response(exit_status=2, error_message=error_message)
    if params.shape_file is None:
        error_message = "A shapefile is required for the mask fill utility"
        return get_xml_error_response(exit_status=2, error_message=error_message)

    # Ensure the input file and shape file are valid file types
    if not params.input_file.endswith('.tif') and not params.input_file.endswith('.h5'):
        error_message = "The input data file must be a GeoTIFF or HDF5 file type"
        return get_xml_error_response(exit_status=1, error_message=error_message)
    if not params.shape_file.endswith('.shp'):
        error_message = "The input shapefile must be a .shp file type"
        return get_xml_error_response(exit_status=1, error_message=error_message)

    # Ensure that all given paths exist
    paths = {params.input_file, params.shape_file, params.output_dir}
    for path in paths:
        if not os.path.exists(path):
            error_message = f"The path {path} does not exist"
            return get_xml_error_response(exit_status=2, error_message=error_message)

    # Ensure that fill_value is a float
    try: params.fill_value = float(params.fill_value)
    except ValueError:
        error_message = "The default fill value must be a number"
        return get_xml_error_response(exit_status=1, error_message=error_message)

    return None


""" Returns an XML error response corresponding to the input exit status, error message, and code. 
    If no code is given, the default code will be InternalError; if no error message is given, the default error 
    message will be "An internal error occurred." 


    Returns:
        str: An ESI standard XML error response 
"""
def get_xml_error_response(exit_status=None, error_message=None, code="InternalError"):
    if exit_status == 1:
        code = "InvalidParameterValue"
        if error_message is None: error_message = "Incorrect parameter specified for given dataset(s)."
    elif exit_status == 2:
        code = "MissingParameterValue"
        if error_message is None: error_message = "No parameter value(s) specified for given dataset(s)."
    elif exit_status == 3:
        code = "NoMatchingData"
        if error_message is None: error_message = "No data found that matched the subset constraints."

    if error_message is None: error_message = "An internal error occurred."

    xml_response = f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <iesi:Exception
        xmlns:iesi="http://eosdis.nasa.gov/esi/rsp/i"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:esi="http://eosdis.nasa.gov/esi/rsp"
        xmlns:ssw="http://newsroom.gsfc.nasa.gov/esi/rsp/ssw"
        xmlns:eesi="http://eosdis.nasa.gov/esi/rsp/e"
        xsi:schemaLocation="http://eosdis.nasa.gov/esi/rsp/i 
        http://newsroom.gsfc.nasa.gov/esi/8.1/schemas/ESIAgentResponseInternal.xsd">
        <Code>{code}</Code>
        <Message>
                {error_message}
                MaskFillUtility failed with code {exit_status}
        </Message>
    </iesi:Exception>
    """

    return xml_response


def get_xml_success_response(input_file, shape_file, output_file):
    xml_response = f"""
    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <ns2:agentResponse xmlns:ns2="http://eosdis.nasa.gov/esi/rsp/i">
        <downloadUrls>
            {output_file}
        </downloadUrls>
        <processInfo>
            <message>
                INFILE = {input_file},
                SHAPEFILE = {shape_file},
                OUTFILE = {output_file}
            </message>
        </processInfo>
    </ns2:agentResponse>
    """

    return xml_response


if __name__ == '__main__':
    start_time = time.time()
    response = mask_fill()
    print(response)
    print("Execution time:", time.time() - start_time)