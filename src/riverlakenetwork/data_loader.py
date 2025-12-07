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
    # Specific dictionary checks
    # -------------------------------
    def _validate_dict(self, name, dict_name, required_keys, unit_keys=None):
        """Generic compact validator for riv_dict, cat_dict, lake_dict."""
        gdf = self.config.get(name)
        d = self.config.get(dict_name)
        if gdf is None:
            return
        if d is None:
            raise ValueError(f"{dict_name} must be provided if {name} is provided.")
        # Check required keys exist
        missing = [k for k in required_keys if k not in d]
        if missing:
            raise ValueError(f"{dict_name} is missing required keys: {missing}")
        # Validate structure for each key
        for key, entry in d.items():
            if not isinstance(entry, dict) or "col" not in entry:
                raise ValueError(f"{dict_name}['{key}'] must be a dict with at least 'col'.")
            # If unit is required, validate it
            if unit_keys and key in unit_keys:
                if "unit" not in entry:
                    raise ValueError(f"{dict_name}['{key}'] must include 'unit'.")
                if entry["unit"] not in {"km2", "m2", "ha"}:
                    raise ValueError(
                        f"Invalid unit '{entry['unit']}' for {dict_name}['{key}'] "
                        f"(allowed: km2, m2, ha)"
                    )
        return d

    def _check_riv_dict(self):
        self.riv_dict = self._validate_dict(
            name="riv",
            dict_name="riv_dict",
            required_keys=["COMID", "NextDownCOMID", "length", "uparea"],
            unit_keys=["uparea"]         # only uparea needs a unit
        )

    def _check_cat_dict(self):
        self.cat_dict = self._validate_dict(
            name="cat",
            dict_name="cat_dict",
            required_keys=["COMID", "unitarea"],
            unit_keys=["unitarea"]       # only unitarea needs a unit
        )

    def _check_lake_dict(self):
        self.lake_dict = self._validate_dict(
            name="lake",
            dict_name="lake_dict",
            required_keys=["LakeCOMID", "unitarea"],
            unit_keys=["unitarea"]       # only unitarea needs a unit
        )

    # -------------------------------
    # Loading GeoDataFrames
    # -------------------------------
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

    def _load_riv(self):
        if "riv" in self.config and self.config["riv"] is not None:
            self.riv = self._load_layer(self.config["riv"])

    def _load_cat(self):
        if "cat" in self.config and self.config["cat"] is not None:
            self.cat = self._load_layer(self.config["cat"])

    def _load_lake(self):
        if "lake" in self.config and self.config["lake"] is not None:
            self.lake = self._load_layer(self.config["lake"])

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
