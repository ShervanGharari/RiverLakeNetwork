import geopandas as gpd

class DataChecker:
    """
    Checks river network, subbasins, and lakes.

    Can initialize with a LoadedData object that has riv, cat, lake
    and their dictionaries, or directly via GeoDataFrames + dicts.
    """

    def __init__(self, loaded_data=None,
                 riv=None, riv_dict=None,
                 cat=None, cat_dict=None,
                 lake=None, lake_dict=None):
        """
        Initialize DataChecker.

        Parameters
        ----------
        loaded_data : object, optional
            An object with attributes:
                riv, riv_dict, cat, cat_dict, lake, lake_dict
        riv, cat, lake : GeoDataFrames, optional
            Individual GeoDataFrames if not using loaded_data.
        riv_dict, cat_dict, lake_dict : dict, optional
            Corresponding dictionaries.
        """

        if loaded_data is not None:
            self.riv = getattr(loaded_data, "riv", None)
            self.riv_dict = getattr(loaded_data, "riv_dict", {}) or {}
            self.cat = getattr(loaded_data, "cat", None)
            self.cat_dict = getattr(loaded_data, "cat_dict", {}) or {}
            self.lake = getattr(loaded_data, "lake", None)
            self.lake_dict = getattr(loaded_data, "lake_dict", {}) or {}
        else:
            self.riv = riv
            self.riv_dict = riv_dict or {}
            self.cat = cat
            self.cat_dict = cat_dict or {}
            self.lake = lake
            self.lake_dict = lake_dict or {}

        # Make copies to avoid modifying original data
        if self.riv is not None:
            self.riv = self.riv.copy()
        if self.cat is not None:
            self.cat = self.cat.copy()
        if self.lake is not None:
            self.lake = self.lake.copy()

        # Run the fucntion
        _check_riv_attr()
        _check_cat_attr()
        _check_lake_attr()
        _check_COMIDs()
        _check_area_units()
        _check_crs(suppress=False)
        _pass_unitarea()



    def _check_riv_attr(self):
        if self.riv is not None:
            required_keys = ["COMID", "NextDownCOMID", "length", "uparea", "uparea_unit", "geometry"]
            for key in required_keys:
                if key not in self.riv_dict:
                    raise ValueError(f"Missing required key in riv_dict: '{key}'")
                col_name = self.riv_dict[key]
                if col_name is None:
                    raise ValueError(f"riv_dict['{key}'] cannot be None, must specify column name in GeoDataFrame")
                if col_name not in self.riv.columns:
                    raise ValueError(f"Column '{col_name}' specified for '{key}' not found in rivers GeoDataFrame")
                # Rename the column in GeoDataFrame to standard key
                self.riv = self.riv.rename(columns={col_name: key})

    def _check_cat_attr(self):
        if self.cat is not None:
                required_keys = ["COMID", "uparea_unit", "geometry"]
                for key in required_keys:
                    if key not in self.cat_dict:
                        raise ValueError(f"Missing required key in cat_dict: '{key}'")
                    col_name = self.cat_dict[key]
                    if col_name is None:
                        raise ValueError(f"cat_dict['{key}'] cannot be None, must specify column name in GeoDataFrame")
                    if col_name not in self.cat.columns:
                        raise ValueError(f"Column '{col_name}' specified for '{key}' not found in subbasins GeoDataFrame")
                    # Rename the column in GeoDataFrame to standard key
                    self.cat = self.cat.rename(columns={col_name: key})


    def _check_lake_attr(self):
        if self.lake is not None:
            required_keys = ["LakeCOMID", "unitarea", "geometry"]
            for key in required_keys:
                if key not in self.lake_dict:
                    raise ValueError(f"Missing required key in lake_dict: '{key}'")
                col_name = self.lake_dict[key]
                if col_name is None:
                    raise ValueError(f"lake_dict['{key}'] cannot be None, must specify column name in GeoDataFrame")
                if col_name not in self.lake.columns:
                    raise ValueError(f"Column '{col_name}' specified for '{key}' not found in lakes GeoDataFrame")
                # Rename the column in GeoDataFrame to standard key
                self.lake = self.lake.rename(columns={col_name: key})

    def _check_COMIDs(self):
        """
        Check that COMIDs in rivers and subbasins match, have same length,
        and sort both GeoDataFrames by COMID.
        """
        if self.riv is None or self.cat is None:
            raise ValueError("Both riv and cat GeoDataFrames must be loaded to check COMIDs.")

        # Extract COMID series
        riv_COMIDs = self.riv['COMID']
        cat_COMIDs = self.cat['COMID']

        # Check lengths
        if len(riv_COMIDs) != len(cat_COMIDs):
            raise ValueError(f"Length mismatch: riv has {len(riv_COMIDs)}, cat has {len(cat_COMIDs)}")

        # Check exact matching
        if not set(riv_COMIDs) == set(cat_COMIDs):
            missing_in_riv = set(cat_COMIDs) - set(riv_COMIDs)
            missing_in_cat = set(riv_COMIDs) - set(cat_COMIDs)
            raise ValueError(
                f"COMID mismatch between riv and cat.\n"
                f"Missing in riv: {missing_in_riv}\n"
                f"Missing in cat: {missing_in_cat}"
            )

        # Sort both GeoDataFrames by COMID
        self.riv = self.riv.sort_values('COMID').reset_index(drop=True)
        self.cat = self.cat.sort_values('COMID').reset_index(drop=True)

    def _pass_unitarea(self):

        self.riv["unitarea"] = self.cat["unitarea"]


    def _check_area_units(self):
        """
        Check that uparea/unitarea for subbasins and lakes are in the same unit.
        If lake unit differs, convert it to subbasin unit.
        Supported units: 'm2', 'ha', 'km2'
        """
        if self.cat is None or self.cat_dict is None:
            raise ValueError("Subbasins (cat) and cat_dict must be provided for area unit check.")
        if self.lake is None or self.lake_dict is None:
            print("No lakes provided; skipping lake area unit check.")
            return
        # Get units and columns
        cat_area_col = self.cat_dict.get("uparea")
        cat_unit = self.cat_dict.get("uparea_unit")
        lake_area_col = self.lake_dict.get("unitarea")
        lake_unit = self.lake_dict.get("unitarea_unit", None)  # optional
        if cat_area_col is None or cat_unit is None:
            raise ValueError("cat_dict must have 'uparea' and 'uparea_unit' defined")
        if lake_area_col is None or lake_unit is None:
            raise ValueError("lake_dict must have 'unitarea' and 'unitarea_unit' defined")
        # Check if units differ
        if cat_unit != lake_unit:
            # Convert lake area to cat unit
            conversion = self._get_area_conversion(lake_unit, cat_unit)
            self.lake[lake_area_col] = self.lake[lake_area_col] * conversion
            print(f"Converted lake area from {lake_unit} to {cat_unit}")
            # Update lake_dict unit to match cat
            self.lake_dict["unitarea_unit"] = cat_unit
        else:
            print(f"Subbasin and lake area units are consistent: {cat_unit}")

    def _get_area_conversion(self, from_unit, to_unit):
        """
        Return a multiplier to convert area from 'from_unit' to 'to_unit'.
        Supported units: 'm2', 'ha', 'km2'
        """
        # Convert everything to m2 first
        unit_to_m2 = {"m2": 1, "ha": 10000, "km2": 1e6}
        if from_unit not in unit_to_m2 or to_unit not in unit_to_m2:
            raise ValueError(f"Unsupported area unit conversion: {from_unit} -> {to_unit}")
        return unit_to_m2[from_unit] / unit_to_m2[to_unit]


    def _check_crs(self, suppress=False):
        """
        Check that CRS is set for riv, cat, and lake (if provided)
        and that they are identical.

        Parameters
        ----------
        suppress : bool, optional
            If True, do not raise an error when CRS mismatch occurs; just print a warning.
        """
        crs_list = []

        if self.riv is not None:
            if self.riv.crs is None:
                raise ValueError("Rivers GeoDataFrame has no CRS defined.")
            crs_list.append(("riv", self.riv.crs))

        if self.cat is not None:
            if self.cat.crs is None:
                raise ValueError("Subbasins GeoDataFrame has no CRS defined.")
            crs_list.append(("cat", self.cat.crs))

        if self.lake is not None:
            if self.lake.crs is None:
                raise ValueError("Lakes GeoDataFrame has no CRS defined.")
            crs_list.append(("lake", self.lake.crs))

        # Print CRS of each layer
        for name, crs in crs_list:
            print(f"{name} CRS: {crs}")

        # Check if all CRS are identical
        crs_values = [crs for _, crs in crs_list]
        if len(set(crs_values)) > 1:
            msg = f"CRS mismatch among provided GeoDataFrames: {crs_list}"
            if suppress:
                print("WARNING:", msg)
            else:
                raise ValueError(msg)


