import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import os
from   shapely.geometry import Point, Polygon
import yaml
import shutil
import warnings
import networkx as nx
import re
import copy

def FixHydroLakesForHDMA (lake_shp):

    lake_to_remove = []

    ######
    # Great Lakes merging of Lake Huron and Michigan, and removal
    ######

    # manipulation of Great Lakes to make them resolvable (for HDMA)
    box = Polygon([[-84.3885, 46.5672],[-84.0244,46.5672],[-84.0244,46.2540],[-84.3885,46.2540]])
    box = gpd.GeoDataFrame(pd.DataFrame(['p1'], columns = ['geometry']),
                           crs = {'init':'epsg:4326'},
                           geometry = [box])
    index_8 = lake_shp[lake_shp['Hylak_id'] == 8].index # lake Huron
    temp = gpd.overlay(lake_shp.loc[index_8], box, how = 'difference') # remove the box from lake Huron
    lake_shp['geometry'].loc[index_8] = temp['geometry'].iloc[0] # update lake Huron in shp_sub

    # Select Lake Michigan (6) and Lake Huron (8)
    shp_slice = lake_shp[lake_shp['Hylak_id'].isin([6, 8])].copy()
    
    # Merge the geometries with a small buffer to fix potential topology issues
    shp_slice.geometry = shp_slice.geometry.buffer(0.00001)
    shp_slice_dissolve = shp_slice.dissolve().reset_index(drop=True)
    
    # Get index for Hylak_id == 6
    index_6 = lake_shp[lake_shp['Hylak_id'] == 6].index
    
    # Get index for Hylak_id == 8
    index_8 = lake_shp[lake_shp['Hylak_id'] == 8].index
    
    # lake update
    lake_shp.loc[index_8, 'geometry']  = shp_slice_dissolve['geometry'].iloc[0]
    lake_shp.loc[index_8, 'Lake_name'] = 'Michigan+Huron'
    lake_shp.loc[index_8, 'Lake_area'] = shp_slice['Lake_area'].sum()
    lake_shp.loc[index_8, 'Vol_total'] = shp_slice['Vol_total'].sum()
    lake_shp.loc[index_8, 'Shore_len'] = shp_slice['Shore_len'].sum()
    lake_shp.loc[index_8, 'Depth_avg'] = shp_slice['Depth_avg'].mean()
    lake_shp.loc[index_8, 'Dis_avg']   = shp_slice['Dis_avg'].mean()
    lake_shp.loc[index_8, 'Res_time']  = shp_slice['Res_time'].mean()
    lake_shp.loc[index_8, 'Country']   = 'United States of America'
    lake_shp.loc[index_8, 'Continent'] = 'North America'
    lake_shp.loc[index_8, 'Poly_src']  = 'SWBD'
    lake_shp.loc[index_8, 'Lake_type'] = 1
    lake_shp.loc[index_8, 'Grand_id']  = 0
    
    # Drop the row using its index and reset the index
    lake_shp = lake_shp.drop(index_6).reset_index(drop=True)

    ######
    # Remove lakes to remove
    ######
    lake_shp = lake_shp[~lake_shp['Hylak_id'].isin(lake_to_remove)].reset_index(drop=True)
    
    # return
    return lake_shp