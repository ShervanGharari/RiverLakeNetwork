import geopandas as gpd
import pandas as pd
from typing import Optional, List


class SingleSegmentLakes:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
        lake_subset_margin: float = 2.0,
        already_resolved_lakeID: Optional[List[int]] = None,
        single_segment_lakeID: Optional[List[int]] = None,
        force_one_lake_per_riv_seg_flag: bool = False,
    ):
        """
        Main workflow controller.

        Steps:
        1. Spatially subset lakes to region of interest (+ margin)
        2. Remove lakes already processed
        3. Optionally filter to a given list of lake IDs
        4. Identify lakes that belong to a single river segment
        5. Filter lakes based on upstream/downstream connectivity

        Important:
        - The workflow is robust to empty datasets at any stage.
        - If lake_subset becomes empty at any step, subsequent steps
          will safely pass through without errors.
        """
        lake_subset = self._subset_lake(cat, lake, lake_subset_margin)

        lake_subset = self._remove_geometrically_resolved_lakes(lake_subset, already_resolved_lakeID)

        lake_subset = self._subset_for_given_single_segment_lakes_ID(lake_subset, single_segment_lakeID)

        lake_subset = self._find_single_segment_lakes(cat, lake_subset, riv)
        print(f"==== Number of single segment lakes after subsetting: {len(lake_subset)} ====")
        lake_subset = self._filter_single_segment_lakes(
            lake_subset,
            riv,
            force_one_lake_per_riv_seg_flag
        )

        print(f"==== Number of lakes after processing: {len(lake_subset)} ====")

        self.single_segment_lake = lake_subset.reset_index(drop=True)

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
        cat = cat.copy()
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
        # --- 4a. Spatial intersection with catchments ---
        cat = cat.drop(columns=["LakeCOMID"], errors="ignore")
        intersected = gpd.sjoin(lake_filtered, cat, how="inner", predicate="intersects")
        # print(intersected.columns)
        lake_ids = intersected["LakeCOMID"].unique()
        lake_subset = lake_filtered[lake_filtered["LakeCOMID"].isin(lake_ids)].reset_index(drop=True)
        # --- 5. Prepare the subset of lakes ---
        final_cols = ["LakeCOMID", "unitarea", "geometry"]
        missing = [c for c in final_cols if c not in lake_subset.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return lake_subset[final_cols]

    def _remove_geometrically_resolved_lakes(
        self,
        lake: gpd.GeoDataFrame,
        already_resolved_lakeID: Optional[List[int]],
    ) -> gpd.GeoDataFrame:
        """
        Remove lakes that were already processed externally.

        Logic:
        - If no list is provided → return unchanged
        - Otherwise filter them out

        Edge case:
        - Empty input lake → safely returned
        """

        if lake.empty or already_resolved_lakeID is None:
            return lake

        return lake[~lake["LakeCOMID"].isin(already_resolved_lakeID)].copy()

    def _subset_for_given_single_segment_lakes_ID(
        self,
        lake: gpd.GeoDataFrame,
        single_segment_lakeID: Optional[List[int]],
    ) -> gpd.GeoDataFrame:
        """
        Optional filtering step to restrict processing to a given set of lake IDs.

        Useful for:
        - Debugging
        - Targeted re-processing

        Edge case:
        - If lake is empty → no issue
        """

        if lake.empty or single_segment_lakeID is None:
            return lake

        return lake[lake["LakeCOMID"].isin(single_segment_lakeID)].copy()

    def _find_single_segment_lakes(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
    ) -> gpd.GeoDataFrame:
        """
        Identify lakes that:
        1. Intersect exactly ONE subbasin (COMID)
        2. Are the largest lake per subbasin
        3. Also intersect at least one river segment

        This ensures:
        - no boundary-crossing lakes
        - one dominant lake per subbasin
        - hydrological connectivity with river network
        """

        # ------------------ #
        # 0. Early exit
        # ------------------ #
        if lake.empty:
            return lake

        # ------------------ #
        # 1. CRS alignment
        # ------------------ #
        if cat.crs != lake.crs:
            lake = lake.to_crs(cat.crs)
        if riv.crs != lake.crs:
            riv = riv.to_crs(lake.crs)

        # ------------------ #
        # 2. Lake ↔ subbasin intersection
        # ------------------ #
        lake_cat = gpd.sjoin(
            lake,
            cat[["COMID", "geometry"]],
            predicate="intersects",
            how="inner"
        ).rename(columns={"COMID": "COMID_cat"})

        if lake_cat.empty:
            return lake_cat.iloc[0:0]

        lake_cat = lake_cat.drop(columns=["index_left", "index_right"], errors="ignore")

        # ------------------ #
        # 3. Keep lakes in ONLY one subbasin
        # ------------------ #
        counts = (
            lake_cat.groupby("LakeCOMID")["COMID_cat"]
            .nunique()
            .reset_index(name="n_cat")
        )

        single = counts[counts["n_cat"] == 1]

        if single.empty:
            return lake_cat.iloc[0:0]

        lake_cat = lake_cat.merge(single[["LakeCOMID"]], on="LakeCOMID")

        # ------------------ #
        # 4. Filter lakes that intersect river network
        # ------------------ #
        lake_riv = gpd.sjoin(
            lake_cat,
            riv[["COMID", "geometry"]],
            predicate="intersects",
            how="inner"
        ).rename(columns={"COMID": "COMID_riv"})

        if lake_riv.empty:
            return lake_riv.iloc[0:0]

        lake_riv = lake_riv.drop(columns=["index_left", "index_right"], errors="ignore")

        # ------------------ #
        # 5. Compute lake area
        # ------------------ #
        lake_riv["area_temp"] = lake_riv.geometry.area

        # ------------------ #
        # 6. Keep largest lake per subbasin
        # ------------------ #
        idx = lake_riv.groupby("COMID_cat")["area_temp"].idxmax()
        largest = lake_riv.loc[idx].copy()

        # ------------------ #
        # 7. Assign association
        # ------------------ #
        largest["associated_COMID"] = largest["COMID_cat"]

        # ------------------ #
        # 8. Cleanup
        # ------------------ #
        largest = largest.drop(
            columns=["COMID_cat", "COMID_riv", "area_temp"],
            errors="ignore"
        ).reset_index(drop=True)

        return largest

    def _find_if_up_or_down_are_lake(
        self,
        riv: gpd.GeoDataFrame,
        segment: int,
    ) -> dict:
        """
        Check whether upstream or downstream neighbors are lakes.

        Input:
        - riv must contain:
            COMID
            NextDownCOMID
            islake (1 = lake, 0 = not)

        Returns:
        - dict: {"up": bool, "down": bool}

        Logic:
        - Downstream: follow NextDownCOMID
        - Upstream: find all segments pointing to current COMID

        Edge cases:
        - Segment not found → return False for both
        """

        row = riv.loc[riv["COMID"] == segment]
        if row.empty:
            return {"up": False, "down": False}

        next_down = row["NextDownCOMID"].iloc[0]

        down = False
        if next_down != 0:
            down_row = riv.loc[riv["COMID"] == next_down]
            if not down_row.empty:
                down = bool(down_row["islake"].iloc[0] == 1)

        upstream = riv.loc[riv["NextDownCOMID"] == segment]
        up = (upstream["islake"] == 1).any() if not upstream.empty else False

        return {"up": bool(up), "down": bool(down)}

    def _filter_single_segment_lakes(
        self,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
        force_one_lake_per_riv_seg_flag: bool,
    ) -> gpd.GeoDataFrame:
        """
        Final filtering based on upstream/downstream lake connectivity.

        Rules:
        1. Always remove lakes whose downstream segment is a lake
        2. Remove upstream-connected lakes only if force flag is True
        3. Otherwise keep upstream-connected lakes

        Edge case:
        - Empty input → returned safely
        """

        if lake.empty:
            return lake

        lake = lake.copy()

        keep = []

        for _, row in lake.iterrows():

            comid = row["associated_COMID"]
            flags = self._find_if_up_or_down_are_lake(riv, comid)

            up = flags["up"]
            down = flags["down"]

            # -----------------------------
            # HARD RULE: downstream lake = always remove
            # -----------------------------
            if down:
                keep.append(False)
                continue

            # -----------------------------
            # Upstream rule
            # -----------------------------
            if up and force_one_lake_per_riv_seg_flag:
                keep.append(False)
            else:
                keep.append(True)

        lake["keep"] = keep

        return lake[lake["keep"]].drop(columns="keep").reset_index(drop=True)