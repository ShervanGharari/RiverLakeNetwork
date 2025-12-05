import geopandas as gpd
from pathlib import Path

class ResolvableLakes:
    """
    Class to load and manage river, subbasin, and lake GeoDataFrames
    along with their associated dictionaries from a configuration.
    Supports both file paths (str/Path) and pre-loaded GeoDataFrames.
    """

    def __init__(self, config: dict):
        """
        Initialize the config class.

        Parameters
        ----------
        config : dict
            Configuration dictionary. Expected keys:
                - riv, riv_dict
                - cat, cat_dict
                - lake, lake_dict
        """
        self.config = config

        # Initialize attributes
        self.riv = None
        self.riv_dict = None
        self.cat = None
        self.cat_dict = None
        self.lake = None
        self.lake_dict = None

        # Step 1: Check dictionaries first
        self._check_riv_dict()
        self._check_cat_dict()
        self._check_lake_dict()

        # Step 2: Load provided layers
        self._load_riv()
        self._load_cat()
        self._load_lake()

        # Step 3: Summary
        self.summary()


    def _subset_lake