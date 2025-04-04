import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import os
from   shapely.geometry import Point
import yaml
import shutil
import warnings
import networkx as nx
import re
import copy

def FixHydroLakesForMerit (lake_shp):

    # Hylak_id to be removed from lake
    lake_to_remove = [
                        1262598, # PFAF 24
                        50, 832978, 106815, 63, 1007254, 6314, 6108, 67331, 732781, 753291,  # PFAF 72
                        851, 847, 9585, # PFAF 74
                        9759, # PFAF 75
                        115503, # PFAF 76
                        213, 206,  # PFAF 82
                    ]

    # PFAF 72: 50, 832978, 106815, 63, 1007254, 6314, 6108, 67331, 732781, 753291
    # PFAF 82: 213, 206

    ######
    # Greate Lakes merging of Lake Huron and Michigan and removal
    ######

    # # manupulation of great lakes to make them resolvable (for HDMA)
    # box = Polygon([[-84.3885, 46.5672],[-84.0244,46.5672],[-84.0244,46.2540],[-84.3885,46.2540]])
    # box = gpd.GeoDataFrame(pd.DataFrame(['p1'], columns = ['geometry']),
    #                        crs = {'init':'epsg:4326'},
    #                        geometry = [box])
    # index_8 = lake_shp[lake_shp['Hylak_id'] == 8].index # lake Huron
    # temp = gpd.overlay(lake_shp.loc[index_8], box, how = 'difference') # remove the box from lake Huron
    # shp_sub['geometry'].loc[index_8] = temp['geometry'].iloc[0] # update lake Huron in shp_sub

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

# PFAF 24: 1262598 1262873 have similar area on one segment, the most downstream, 1262873, is kept and 1262598 is removed
# PFAF 71: seems ok!
# PFAF 72: 67349 67331 have similar area on one segment, the most downstream, 67331, is kept and 67349 is removed
# PFAF 72: 732078 732781 have similar area on one segment, the most downstream, 732781, is kept and 732078 is removed
# PFAF 72: 753908 753291 have similar area on one segment, the most downstream, 753291, is kept and 753908 is removed
# PFAF 72: 50, 832978, 106815, 63, 1007254, 6314, 6108
# Hylak_ID 6314 (at -64.78994, 54.75624) connects to two different river systems; either remove or fix the shape of the lake
# Hylak_ID 6108 (at -62.92842, 55.16738) has two outlet; removed or split into two lakes
# the rest are next to open sea or ocean lakes
# PFAF 74: 851, 847, 9585
# next to open sea or ocean lakes
# PFAF 75: 9759
# next to open sea or ocean lakes
# PFAF 76: 115503
# TODO 860 is considered with outlet; it should be changed to endorehic with segment correction 76004286, 76003475, 76003492
# PFAF 77: seems ok!
# PFAF 78: seems ok!
# PFAF 82: 213, 206
# next to open sea or ocean lakes