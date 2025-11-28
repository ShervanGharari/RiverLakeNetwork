import geopandas as gpd
from pathlib import Path

class DataLoader:
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

    # -------------------------------
    # Dictionary checks
    # -------------------------------
    def _check_riv_dict(self):
        if "riv" in self.config and self.config["riv"] is not None:
            if "riv_dict" not in self.config or self.config["riv_dict"] is None:
                raise ValueError("riv_dict must be provided if riv is provided.")
            required_keys = ["COMID", "NextDownCOMID", "length", "uparea", "uparea_unit"]
            missing_keys = [k for k in required_keys if k not in self.config["riv_dict"]]
            if missing_keys:
                raise ValueError(f"riv_dict is missing required keys: {missing_keys}")
            self.riv_dict = self.config["riv_dict"]

    def _check_cat_dict(self):
        if "cat" in self.config and self.config["cat"] is not None:
            if "cat_dict" not in self.config or self.config["cat_dict"] is None:
                raise ValueError("cat_dict must be provided if cat is provided.")
            required_keys = ["COMID", "uparea_unit"]
            missing_keys = [k for k in required_keys if k not in self.config["cat_dict"]]
            if missing_keys:
                raise ValueError(f"cat_dict is missing required keys: {missing_keys}")
            self.cat_dict = self.config["cat_dict"]

    def _check_lake_dict(self):
        if "lake" in self.config and self.config["lake"] is not None:
            if "lake_dict" not in self.config or self.config["lake_dict"] is None:
                raise ValueError("lake_dict must be provided if lake is provided.")
            required_keys = ["unitarea", "LakeCOMID"]
            missing_keys = [k for k in required_keys if k not in self.config["lake_dict"]]
            if missing_keys:
                raise ValueError(f"lake_dict is missing required keys: {missing_keys}")
            self.lake_dict = self.config["lake_dict"]

    # -------------------------------
    # Loading GeoDataFrames
    # -------------------------------
    def _load_riv(self):
        if "riv" in self.config and self.config["riv"] is not None:
            self.riv = self._load_layer(self.config["riv"])

    def _load_cat(self):
        if "cat" in self.config and self.config["cat"] is not None:
            self.cat = self._load_layer(self.config["cat"])

    def _load_lake(self):
        if "lake" in self.config and self.config["lake"] is not None:
            self.lake = self._load_layer(self.config["lake"])

    def _load_layer(self, layer):
        """Helper to load either a file path or a GeoDataFrame"""
        if isinstance(layer, (str, Path)):
            path = Path(layer)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            return gpd.read_file(path)
        elif isinstance(layer, gpd.GeoDataFrame):
            return layer.copy()
        else:
            raise TypeError("Layer must be a file path (str/Path) or a GeoDataFrame")

    # -------------------------------
    # Summary
    # -------------------------------
    def summary(self):
        """Print a summary of the loaded datasets and dictionaries."""
        print("riv:", "Loaded" if self.riv is not None else "None")
        print("riv_dict:", self.riv_dict)
        print("cat:", "Loaded" if self.cat is not None else "None")
        print("cat_dict:", self.cat_dict)
        print("lake:", "Loaded" if self.lake is not None else "None")
        print("lake_dict:", self.lake_dict)
