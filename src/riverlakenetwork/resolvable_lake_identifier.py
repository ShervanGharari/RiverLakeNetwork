import geopandas as gpd
from   shapely.geometry import Point
import pandas as pd


class ResolvableLakes:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
        margin: float = 2.0):
        """
        Full workflow for computing resolvable lakes:
            1. Subset lakes spatially (subset to study area)
            2. Remove lakes fully inside single catchment
            3. River–lake intersection (all)
            4. Remove smaller lakes for segments with >1 lake
            5. Remove lakes intersecting only one river segment
            6. Filter the lake layer to keep only lakes that remain
        """
        # --- Step 1: spatial subset of lakes ---
        lake_subset = self._subset_lake(cat, lake, margin)
        # --- Step 2: remove lakes contained in only one catchment ---
        lake_cleaned = self._remove_inbasin_lakes(cat, lake_subset)
        # --- Step 3: remove lakes that are not touching river starting or ending point ---
        lake_cleaned = self._keep_lakes_touching_river_endpoints(riv, lake_cleaned)
        # --- Save final output ---
        self.lake_resolvable = lake_cleaned

    def _subset_lake(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        margin: float = 2.0
    ) -> gpd.GeoDataFrame:
        """
        Subset lakes using catchment extent and spatial intersection.
        Parameters
        ----------
        cat : GeoDataFrame
            Catchment polygons.
        lake : GeoDataFrame
            Lake polygons.
        margin : float, default=2.0
            Margin (in degrees) added around catchment bounding box.
        Returns
        -------
        GeoDataFrame
            Filtered lake dataset
        """
        # --- 1. Compute lake centroids ---
        lake = lake.copy()
        lake_centroids = lake.geometry.centroid
        lake["x"], lake["y"] = lake_centroids.x, lake_centroids.y
        # --- 2. Catchment bounding box with margin ---
        minx, miny, maxx, maxy = cat.total_bounds
        minx, miny, maxx, maxy = minx - margin, miny - margin, maxx + margin, maxy + margin
        # --- 3. Fast filter lakes by centroid within bounding box ---
        lake_filtered = lake[
            (lake["x"] >= minx) & (lake["x"] <= maxx) &
            (lake["y"] >= miny) & (lake["y"] <= maxy)
        ]
        # --- 4. Spatial intersection with catchments ---
        intersected = gpd.sjoin(lake_filtered, cat, how="inner", predicate="intersects")
        print(intersected.columns)
        lake_ids = intersected["LakeCOMID"].unique()
        lake_subset = lake_filtered[lake_filtered["LakeCOMID"].isin(lake_ids)].reset_index(drop=True)
        # Keep only the relevant columns
        final_cols = ["LakeCOMID", "unitarea", "geometry"]
        missing = [c for c in final_cols if c not in lake_subset.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return lake_subset[final_cols]

    def _remove_inbasin_lakes(self, cat: gpd.GeoDataFrame, lake: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Remove lakes that lie entirely within a single subbasin.
        Logic:
        - Perform a spatial intersection between catchments and lakes.
        - Count how many catchments each lake intersects.
        - If a lake intersects only one catchment, it is considered 'in-basin only'
          and is removed.
        Parameters
        ----------
        cat : GeoDataFrame
            Catchment polygons.
        lake : GeoDataFrame
            Lake polygons containing a 'LakeCOMID' column.
        Returns
        -------
        GeoDataFrame
            Filtered lakes after removing those that lie entirely within one basin.
        """
        if "LakeCOMID" not in lake.columns:
            raise ValueError("lake GeoDataFrame must contain a 'LakeCOMID' column")
        # Spatial intersection
        cat_lake_int = gpd.overlay(cat, lake, how="intersection")
        if "LakeCOMID" not in cat_lake_int.columns:
            raise ValueError("Spatial intersection did not retain 'LakeCOMID' column")
        # Count how many catchments each lake touches
        lake_counts = cat_lake_int["LakeCOMID"].value_counts()
        # Lakes that appear exactly once are “entirely in one basin”
        single_occurrence_ids = lake_counts[lake_counts == 1].index.tolist()
        # Remove them
        filtered_lake = lake[~lake["LakeCOMID"].isin(single_occurrence_ids)].reset_index(drop=True)
        return filtered_lake

    def _keep_lakes_touching_river_endpoints(self,
                                             riv: gpd.GeoDataFrame,
                                             lake: gpd.GeoDataFrame):
        """
        Keep only lakes that intersect with the start or end points of river segments.
        Handles rivers with None or empty geometries.

        Parameters
        ----------
        riv : GeoDataFrame
            River linestrings with at least geometry + COMID.
        lake : GeoDataFrame
            Lake polygons containing LakeCOMID.

        Returns
        -------
        GeoDataFrame
            Filtered lake GeoDataFrame
        """
        riv = riv.copy()
        # Remove null or empty geometries
        riv = riv[riv.geometry.notnull() & ~riv.geometry.is_empty].reset_index(drop=True)
        # Extract start and end points safely
        def get_start_pt(g):
            return Point(g.coords[0]) if g and g.coords else None
        def get_end_pt(g):
            return Point(g.coords[-1]) if g and g.coords else None
        riv["start_pt"] = riv.geometry.apply(get_start_pt)
        riv["end_pt"]   = riv.geometry.apply(get_end_pt)
        # Convert start/end points to GeoDataFrames
        start_gdf = gpd.GeoDataFrame(riv[["COMID"]], geometry=riv["start_pt"], crs=riv.crs)
        end_gdf   = gpd.GeoDataFrame(riv[["COMID"]], geometry=riv["end_pt"], crs=riv.crs)
        # Spatial join start points with lakes
        start_join = gpd.sjoin(start_gdf, lake, how="inner", predicate="intersects")
        end_join   = gpd.sjoin(end_gdf, lake, how="inner", predicate="intersects")
        # Combine LakeCOMID from start and end joins
        keep_ids = pd.Index(start_join["LakeCOMID"].tolist() +
                            end_join["LakeCOMID"].tolist()).unique()
        filtered_lake = lake[lake["LakeCOMID"].isin(keep_ids)].reset_index(drop=True)
        return filtered_lake

    def _river_lake_intersection_info(self, riv: gpd.GeoDataFrame, lake: gpd.GeoDataFrame):
        """
        Computes basic intersection summary between rivers and lakes.
        Prints:
          - number of lakes intersecting any river segment
          - number of river segments intersecting >1 lake
        """
        river_lake_int = gpd.overlay(riv, lake, how="intersection")
        num_lakes = river_lake_int["LakeCOMID"].nunique()
        print("Number of lakes in the intersection:", num_lakes)
        m = (
            river_lake_int.groupby("COMID")["LakeCOMID"]
            .nunique()
            .gt(1)
            .sum()
        )
        print("Number of river segments intersecting more than one lake:", m)
        return river_lake_int

    def _remove_lakes_int_with_one_river_segment(self, river_lake_int: gpd.GeoDataFrame):
        """
        Remove lakes that intersect only a single river segment.
        Only lakes intersecting >1 segment are kept.
        """
        df = river_lake_int.copy()
        df["keep"] = df.groupby("LakeCOMID")["COMID"].transform("nunique") > 1
        df = df[df["keep"]].reset_index(drop=True)
        print("Number of lakes after Step-2:", df["LakeCOMID"].nunique())
        return df.drop(columns="keep")

    def _remove_lakes_int_with_more_than_two_river_segment(self, river_lake_int: gpd.GeoDataFrame):
        """
        Keep only lakes that intersect more than one river segment.
        Parameters
        ----------
        river_lake_int : GeoDataFrame
            Output of overlay between river segments and lakes.
            Must contain 'COMID' (river ID) and 'LakeCOMID' (lake ID).
        Returns
        -------
        GeoDataFrame
            Filtered GeoDataFrame containing only lakes intersecting >1 river segment.
        """
        df = river_lake_int.copy()
        # Count number of unique river segments per lake
        seg_count = df.groupby("LakeCOMID")["COMID"].transform("nunique")
        # Keep only lakes with >1 segment intersecting
        df_filtered = df[seg_count > 1].reset_index(drop=True)
        return df_filtered

    def _filter_lake(self, lake: gpd.GeoDataFrame, river_lake_int: gpd.GeoDataFrame):
        """
        Subset the lake GeoDataFrame to only those lakes that appear
        in the river–lake intersection GeoDataFrame.
        Parameters
        ----------
        lake : GeoDataFrame
            Original lake layer containing 'LakeCOMID'.
        river_lake_int : GeoDataFrame
            Intersection layer containing 'LakeCOMID'.
        Returns
        -------
        GeoDataFrame
            Subset of `lake` containing only lakes present in `river_lake_int`.
        """
        # All LakeCOMID IDs that intersect with river segments
        keep_ids = river_lake_int["LakeCOMID"].unique()
        # Subset the lake dataset
        lake_filtered = lake[lake["LakeCOMID"].isin(keep_ids)].reset_index(drop=True)
        return lake_filtered