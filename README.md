OVERVIEW

MaskFill provides shapefile subsetting for gridded Level 3 and Level 4 
NASA earth data GeoTIFF and HDF5 files. It returns a copy of the data file
where all data points corresponding to regions outside of the given shape 
are replaced with a fill value. 

INSTALLATION

MaskFill was developed using the Anaconda distribution of python
(https://www.anaconda.com/download) and conda virutal environment.  This
simplifies dependency management.  Run these commands to create a mask fill conda
virtual environment and install all the needed packages:

    conda create --name mask_fill_environment --file conda_requirements.txt
    source activate mask_fill_environment
    pip install -r pip_requirements.txt

RUNNING TEST DATA

Run the following command to mask fill the test data:
    
    ./maskfill.sh --FILE_URLS test_data/MOD10CM_North_Polar.tif --SHAPEFILE test_data/USA.geojson
    
This test data contains a north polar view of NASA earth data collected from the MODIS instrument
along with a shapefile of the USA. The output file 'MOD10CM_North_Polar_mf.tif' shows the 
subsetted GeoTIFF file containing only data from within the United States.
