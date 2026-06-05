import geopandas as gpd
import pandas as pd
from typing import Optional, Union, List, Set, Dict
from .utility import Utility

class SingleSegmentLakes:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
        lake_subset_margin: float = 2.0,
        force_one_lake_per_riv_seg_flag: bool = False,
        single_segment_lakesID_position: Optional[
            Union[List[int], Set[int], Dict[int, str]]
        ] = None,
        single_segment_lakes_remove_first_order_flag: bool = True,
        single_segment_lakesID_restrict: bool = True,
        single_segment_lakes_global_position: str = "down",
    ):
        """
        Main workflow controller.
        """

        # ------------------ #
        # Step 1: subset lakes
        # ------------------ #
        lake_subset = self._subset_lake(cat, lake, lake_subset_margin)

        # ------------------ #
        # Step 2: optional restriction to provided IDs
        # ------------------ #
        if single_segment_lakesID_position:

            position_map = Utility.normalize_single_segment_lakes(
                single_segment_lakesID_position,
                single_segment_lakes_global_position,
            )

            if single_segment_lakesID_restrict:
                if "LakeCOMID" not in lake_subset.columns:
                    raise ValueError("LakeCOMID column is required")

                lake_subset = (
                    lake_subset[
                        lake_subset["LakeCOMID"].isin(position_map.keys())
                    ]
                    .copy()
                    .reset_index(drop=True)
                )

        # ------------------ #
        # Step 3: detect single segment lakes
        # ------------------ #
        lake_subset = self._find_single_segment_lakes(
            cat, lake_subset, riv
        )

        print(
            f"==== Number of single segment lakes after subsetting: "
            f"{len(lake_subset)} ===="
        )

        # ------------------ #
        # Step 4: filtering
        # ------------------ #
        lake_subset = self._filter_single_segment_lakes(
            lake_subset,
            riv,
            force_one_lake_per_riv_seg_flag,
            single_segment_lakesID_position,
            single_segment_lakes_remove_first_order_flag,
            single_segment_lakes_global_position,
        )

        print(
            f"==== Number of lakes after processing: "
            f"{len(lake_subset)} ===="
        )

        # ------------------ #
        # Final output
        # ------------------ #
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
        force_one_lake_per_riv_seg_flag: bool = False,
        single_segment_lakesID_position: Optional[
            Union[List[int], Set[int], Dict[int, str]]
        ] = None,
        single_segment_lakes_remove_first_order_flag: bool = True,
        single_segment_lakes_global_position: str = "down",
    ) -> gpd.GeoDataFrame:
        """
        Final filtering based on upstream/downstream lake connectivity.
        """

        if lake.empty:
            return lake

        # ------------------ #
        # Validate required columns
        # ------------------ #
        required_cols = {"associated_COMID", "LakeCOMID"}
        missing = required_cols - set(lake.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        lake = lake.copy()

        # one to one valibration
        if not (
            lake["LakeCOMID"].is_unique
            and lake["associated_COMID"].is_unique
        ):
            raise ValueError("Mapping is not one-to-one between LakeCOMID and associated_COMID")

        # ------------------ #
        # Normalize position map
        # ------------------ #
        position_map = Utility.normalize_single_segment_lakes(
            single_segment_lakesID_position,
            single_segment_lakes_global_position,
        )

        lake["position"] = "down"
        keep = []

        # ------------------ #
        # Identify the headwater riv segment
        # ------------------ #
        downstream_targets = set(riv["NextDownCOMID"].dropna())
        riv["headwater"] = ~riv["COMID"].isin(downstream_targets)

        for idx, row in lake.iterrows():

            comid = row["associated_COMID"]

            flags = self._find_if_up_or_down_are_lake(riv, comid)
            up = flags["up"]
            down = flags["down"]

            # safer COMID handling
            try:
                lake_comid = int(row["LakeCOMID"])
            except Exception:
                keep.append(False)
                continue

            position = position_map.get(
                lake_comid,
                single_segment_lakes_global_position,
            )

            # if position is up and the associated COMID for riv headwater
            # and if filter is True, the lake is removed
            river_row = riv.loc[riv["COMID"] == comid]
            if (
                not river_row.empty
                and river_row["headwater"].iloc[0]
                and single_segment_lakes_remove_first_order_flag
                and position.lower() == "up"
            ):
                keep.append(False)
                continue

            # --------------------------------------------------
            # RULE 1: forced simplification
            # --------------------------------------------------
            if force_one_lake_per_riv_seg_flag and (up or down):
                keep.append(False)
                continue

            # --------------------------------------------------
            # RULE 2: no lakes up/down → always keep
            # --------------------------------------------------
            if not up and not down:
                lake.at[idx, "position"] = position
                keep.append(True)
                continue

            # --------------------------------------------------
            # RULE 3 & 4 combined
            # --------------------------------------------------
            allow = (
                (down and position == "up") or
                (up and position == "down")
            )

            if allow:
                lake.at[idx, "position"] = position
                keep.append(True)
            else:
                keep.append(False)

        lake["keep"] = keep

        lake = lake.drop(columns=["headwater"])

        return (
            lake[lake["keep"]]
            .drop(columns="keep")
            .reset_index(drop=True)
        )