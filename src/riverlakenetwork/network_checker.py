import geopandas as gpd
from   shapely.geometry import Point
import pandas as pd
import numpy as np
from   collections import defaultdict, deque
from   .utility import Utility   # adjust path if needed


class NetworkTopologyChecker:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame):

        riv, cat, lake = self._riv_topology_correction(riv, cat, lake)

        self.cat_corrected = cat
        self.riv_corrected = riv
