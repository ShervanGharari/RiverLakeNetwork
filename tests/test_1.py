import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString
from shapely import affinity
from riverlakenetwork import Utility, BurnLakes

def test1():

    # ============================================================
    # CREATE CATCHMENTS (POLYGONS)
    # ============================================================
    basin_data = [
        {"COMID": 1, "geometry": Polygon([(-4.0, 4.0), ( 0.0, 4.0), (-2.0, 2.0)])},
        {"COMID": 2, "geometry": Polygon([(-4.0, 4.0), (-2.0, 2.0), (-4.0, 0.0)])},
        {"COMID": 3, "geometry": Polygon([( 0.0, 4.0), ( 0.0, 0.0), (-4.0, 0.0)])},
        {"COMID": 4, "geometry": Polygon([( 0.0, 4.0), ( 4.0, 4.0), ( 2.0, 2.0), ( 0.0, 2.0)])},
        {"COMID": 5, "geometry": Polygon([( 4.0, 4.0), ( 4.0, 0.0), ( 2.0, 0.0), ( 2.0, 2.0)])},
        {"COMID": 6, "geometry": Polygon([( 0.0, 0.0), ( 0.0, 2.0), ( 2.0, 2.0), ( 2.0, 0.0)])},
        {"COMID": 7, "geometry": Polygon([(-4.0, 0.0), (-2.0,-2.0), (-4.0,-4.0)])},
        {"COMID": 8, "geometry": Polygon([(-4.0,-4.0), (-2.0,-2.0), ( 0.0,-4.0)])},
        {"COMID": 9, "geometry": Polygon([( 0.0, 0.0), ( 0.0,-2.0), (-1.0,-1.7), (-1.4,-1.4), (-1.7,-1.0), (-2.0, 0.0)])},
        {"COMID":10, "geometry": Polygon([(-4.0, 0.0), (-2.0, 0.0), (-1.7,-1.0), (-1.4,-1.4), (-1.0,-1.7), ( 0.0,-2.0), ( 0.0,-4.0)])},
        {"COMID":11, "geometry": Polygon([( 0.0, 0.0), ( 2.0, 0.0), ( 2.0,-3.0), ( 0.0,-4.0)])},
        {"COMID":12, "geometry": Polygon([( 2.0, 0.0), ( 4.0, 0.0), ( 4.0,-4.0), ( 2.0,-3.0)])},
        {"COMID":13, "geometry": Polygon([( 0.0,-4.0), ( 2.0,-3.0), ( 4.0,-4.0)])},
    ]
    basins = gpd.GeoDataFrame(basin_data)

    basins_location_data = [
        {"COMID":  1, "LABEL": "B1", "X": -3.4, "Y":  3.6},
        {"COMID":  2, "LABEL": "B2", "X": -3.8, "Y":  3.2},
        {"COMID":  3, "LABEL": "B3", "X": -3.4, "Y":  0.2},
        {"COMID":  4, "LABEL": "B4", "X":  0.2, "Y":  3.6},
        {"COMID":  5, "LABEL": "B5", "X":  2.2, "Y":  0.2},
        {"COMID":  6, "LABEL": "B6", "X":  0.2, "Y":  1.6},
        {"COMID":  7, "LABEL": "B7", "X": -3.8, "Y": -0.8},
        {"COMID":  8, "LABEL": "B8", "X": -3.4, "Y": -3.8},
        {"COMID":  9, "LABEL": "B9", "X": -1.6, "Y": -0.2},
        {"COMID": 10, "LABEL": "B10", "X": -3.4, "Y": -0.4},
        {"COMID": 11, "LABEL": "B11", "X":  0.1, "Y": -3.6},
        {"COMID": 12, "LABEL": "B12", "X":  2.2, "Y": -0.2},
        {"COMID": 13, "LABEL": "B13", "X":  0.7, "Y": -3.8},
    ]
    basins_location = pd.DataFrame(basins_location_data)
    # ============================================================
    # CREATE RIVERS (LINES)
    # ============================================================
    river_data = [
        {"COMID": 1, "DOWN": 3, "AREA": 4.00, "geometry": LineString([(-2.0, 3.0), (-2.0, 2.0)])},
        {"COMID": 2, "DOWN": 3, "AREA": 4.00, "geometry": LineString([(-3.0, 2.0), (-2.0, 2.0)])},
        {"COMID": 3, "DOWN":11, "AREA": 8.00, "geometry": LineString([(-2.0, 2.0), ( 0.0, 0.0)])},
        {"COMID": 4, "DOWN": 6, "AREA": 6.00, "geometry": LineString([( 1.0, 3.0), ( 2.0, 2.0)])},
        {"COMID": 5, "DOWN": 6, "AREA": 6.00, "geometry": LineString([( 3.5, 0.5), ( 2.0, 2.0)])},
        {"COMID": 6, "DOWN":11, "AREA": 4.00, "geometry": LineString([( 2.0, 2.0), ( 0.0, 0.0)])},
        {"COMID": 7, "DOWN":-9, "AREA": 4.00, "geometry": LineString([(-3.0,-2.0), (-2.0,-2.0)])},
        {"COMID": 8, "DOWN":-9, "AREA": 4.00, "geometry": LineString([(-2.0,-3.0), (-2.0,-2.0)])},
        {"COMID": 9, "DOWN":11, "AREA": 2.98, "geometry": LineString([(-1.0,-1.0), ( 0.0, 0.0)])},
        {"COMID":10, "DOWN":-9, "AREA": 5.02, "geometry": LineString([(-2.5,-1.0), (-2.0,-2.0)])},
        {"COMID":11, "DOWN":13, "AREA": 7   , "geometry": LineString([( 0.0, 0.0), ( 2.0,-3.0)])},
        {"COMID":12, "DOWN":13, "AREA": 7   , "geometry": LineString([( 3.0,-2.0), ( 2.0,-3.0)])},
        {"COMID":13, "DOWN":-9, "AREA": 2   , "geometry": LineString([( 2.0,-3.0), ( 2.0,-4.0)])},
    ]
    rivers = gpd.GeoDataFrame(river_data)

    # ============================================================
    # CREATE LAKES (POLYGONS)
    # ============================================================
    lake_data = [
        {"lake_id": 100, "geometry": Polygon([(-2.5,  2.5), (-1.5,  2.5), (-1.5,  1.5), (-2.5, 1.5)])},
        {"lake_id": 200, "geometry": Polygon([(-0.5, -1.0), (-0.5,  0.0), ( 2.5,  3.0), ( 2.5, 2.0)])},
        {"lake_id": 300, "geometry": Polygon([(-2.5, -1.5), (-1.5, -1.5), (-1.5, -2.5), (-2.5,-2.5)])},
        {"lake_id": 400, "geometry": Polygon([(0.75, 3.25), (1.25, 3.25), (1.25, 2.75), (0.75, 2.75)])},
        {"lake_id": 500, "geometry": Polygon([(3.25,-0.25), (3.75,-0.25), (3.75,-0.75), (3.25,-0.75)])},
        {"lake_id": 600, "geometry": Polygon([(-1.25,0.75), (-1.25,1.25), (-0.75,1.25), (-0.75,0.75)])},
        {"lake_id": 700, "geometry": Polygon([(0.5, -0.25), (1.5, -1.75), (1.5, -2.75), (0.5, -1.25)])},
    ]
    lakes = gpd.GeoDataFrame(lake_data)

    lakes_location_data = [
        {"lake_id":  100, "LABEL": "L1", "X": -1.825, "Y":  2.0,  "COLOR":"k"},
        {"lake_id":  200, "LABEL": "L2", "X":  0.4,   "Y":  0.18, "COLOR":"k"},
        {"lake_id":  300, "LABEL": "L3", "X": -1.825, "Y": -2.0,  "COLOR":"k"},
        {"lake_id":  400, "LABEL": "L4", "X":  0.88,  "Y":  3.1,  "COLOR":"k"},
        {"lake_id":  500, "LABEL": "L5", "X":  3.4,   "Y": -0.5,  "COLOR":"k"},
        {"lake_id":  600, "LABEL": "L6", "X":  -0.785,"Y":  1.0,  "COLOR":"k"},
        {"lake_id":  700, "LABEL": "L7", "X":  +1,    "Y": -1.0,  "COLOR":"k"},
    ]
    lakes_location = pd.DataFrame(lakes_location_data)

    lakes_resolved_location_data = [
        {"lake_id":  100, "LABEL": "L1", "X": -2.1, "Y":  2.0, "COLOR":"k"},
        {"lake_id":  200, "LABEL": "L2", "X":  0.9, "Y":  1.0, "COLOR":"k"},
        {"lake_id":  300, "LABEL": "L3", "X": -2.1, "Y": -2.0, "COLOR":"white"},
        {"lake_id":  700, "LABEL": "L7", "X":  0.8, "Y": -3.0/2.0, "COLOR":"k"},
    ]
    lakes_resolved_location = pd.DataFrame(lakes_resolved_location_data)

    # Factor for compression along y-axis
    y_factor = 1.0

    # ----------------------------
    # Compress basins
    # ----------------------------
    basins["geometry"] = basins.geometry.apply(lambda g: affinity.scale(g, xfact=1.0, yfact=y_factor, origin=(0,0)))

    # ----------------------------
    # Compress rivers
    # ----------------------------
    rivers["geometry"] = rivers.geometry.apply(lambda g: affinity.scale(g, xfact=1.0, yfact=y_factor, origin=(0,0)))

    # ----------------------------
    # Compress lakes
    # ----------------------------
    lakes["geometry"] = lakes.geometry.apply(lambda g: affinity.scale(g, xfact=1.0, yfact=y_factor, origin=(0,0)))


    # area of cat and length of riv
    basins["AREA"] = basins.geometry.area
    rivers["LENGTH"] = rivers.geometry.length
    lakes["AREA"] = lakes.geometry.area
    rivers["AREA"] = basins["AREA"] # pass the information to rivers
    rivers = Utility.compute_uparea(rivers,
                                    mapping = {
                                        "id": "COMID",
                                        "next_id": "DOWN",
                                        "unitarea": "AREA",},
                                    out_col = 'UPAREA')
    basins.set_crs("EPSG:4326", inplace=True)
    rivers.set_crs("EPSG:4326", inplace=True)
    lakes.set_crs("EPSG:4326", inplace=True)


    # create the config and pass it to the Burn lake
    config = {
        "riv": rivers,
        "riv_dict": {
            "COMID": {"col":"COMID"},
            "NextDownCOMID": {"col":"DOWN"},
            "length": {"col":"LENGTH"},
            "uparea": {"col":"UPAREA","unit":"km2"}
        },
        "cat": basins,
        "cat_dict": {
            "COMID": {"col":"COMID"},
            "unitarea": {"col":"AREA","unit":"km2"},
        },
        "lake": lakes,
        "lake_dict": {
            "LakeCOMID": {"col":"lake_id"},
            "unitarea": {"col":"AREA","unit":"km2"}
        },
    }

    # burn lakes into river network
    bl = BurnLakes(InputData = config,
                   SingleSegmentProcessing = True)

    #
    def assert_gdfs_equal(
        gdf1,
        gdf2,
        key_col="COMID",
        tol=1e-5):
        """
        Assert two GeoDataFrames are equal (attributes only).
        Fails pytest test with clear message if mismatch.
        """

        # Sort
        df1 = gdf1.sort_values(key_col).reset_index(drop=True)
        df2 = gdf2.sort_values(key_col).reset_index(drop=True)

        # Drop geometry
        df1 = df1.drop(columns="geometry", errors="ignore")
        df2 = df2.drop(columns="geometry", errors="ignore")

        # Shape check
        assert df1.shape == df2.shape, \
            f"Shape mismatch: {df1.shape} != {df2.shape}"

        # Column check
        assert set(df1.columns) == set(df2.columns), \
            f"Column mismatch:\nOnly in df1: {set(df1.columns) - set(df2.columns)}\nOnly in df2: {set(df2.columns) - set(df1.columns)}"

        # Align columns
        df1 = df1[sorted(df1.columns)]
        df2 = df2[sorted(df2.columns)]

        # Convert numerics
        df1 = df1.apply(pd.to_numeric, errors='ignore')
        df2 = df2.apply(pd.to_numeric, errors='ignore')

        # Compare values
        for col in df1.columns:
            s1 = df1[col]
            s2 = df2[col]

            if pd.api.types.is_numeric_dtype(s1):
                equal = np.isclose(s1, s2, atol=tol, equal_nan=True)
            else:
                equal = (s1 == s2) | (s1.isna() & s2.isna())

            if not np.all(equal):
                idx = np.where(~equal)[0][:10]  # first 10 mismatches
                details = "\n".join(
                    f"row {i}: {s1.iloc[i]} != {s2.iloc[i]}"
                    for i in idx
                )
                raise AssertionError(
                    f"Mismatch in column '{col}' (showing first {len(idx)}):\n{details}"
                )

    # # test riv
    # riv = gpd.read_file("./test_1/riv.gpkg")
    # assert_gdfs_equal(riv, bl.riv)

    # # test cat
    # cat = gpd.read_file("./test_1/cat.gpkg")
    # assert_gdfs_equal(cat, bl.cat)

    # # test lake
    # lake = gpd.read_file("./test_1/lake.gpkg")
    # assert_gdfs_equal(lake, bl.lake)