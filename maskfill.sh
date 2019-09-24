#!/bin/sh

# Activate environment
source activate mask_fill_environment

# Call the Mask Fill Utility, passing on the input parameters
./MaskFillUtility.py "$@"