#!/bin/sh

# Commands to create an environment for the Mask Fill Utility:

# conda create --name mask_fill_environment --file conda_requirements.txt
# source activate mask_fill_environment
# pip install -r pip_requirements.txt

# Activate environment
source activate mask_fill_environment

# Call the Mask Fill Utility, passing on the input parameters
./MaskFillUtility.py "$@"