import geopandas as gpd
from   shapely.geometry import Point, LineString
import pandas as pd
from   .utility import Utility   # adjust path if needed


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
        print(f"==== Number of lakes after subsetting: {len(lake_subset)} ====")
        # --- Step 2: remove lakes contained in only one catchment ---
        lake_cleaned = self._remove_inbasin_lakes(cat, lake_subset)
        print(f"==== Number of lakes after removing intersection with only one lake: {len(lake_cleaned)} ====")
        # --- Step 3: remove lakes that are not touching river starting or ending point ---
        lake_cleaned = self._keep_lakes_touching_river_endpoints(riv, lake_cleaned)
        print(f"==== Number of lakes after removing lakes that do not touch starting or ending points of river segments: {len(lake_cleaned)} ====")
        lake_cleaned = self._remove_lakes_touching_only_one_river_endpoint(riv, lake_cleaned)
        print(f"==== Number of lakes after removing lakes that do touch only one starting or ending points of river segments: {len(lake_cleaned)} ====")
        river_lake_int = self._river_lake_intersection_info(riv, lake_cleaned)
        lake_cleaned, river_lake_int_filtered = self._remove_lakes_int_with_one_river_segment(lake_cleaned, river_lake_int)
        print(f"==== Number of lakes after removing lakes that do intersect with only one river segment: {len(lake_cleaned)} ====")
        lake_cleaned, river_lake_int_filtered = self._remove_lakes_with_repeated_max_uparea(lake_cleaned, river_lake_int_filtered)
        print(f"==== Number of lakes after removing lakes that do have exactly the same uparea for their maximume uparea for various: {len(lake_cleaned)} ====")
        lake_cleaned, river_lake_int_filtered = self._supress_number_of_lakes_to_two_per_riv_segment(lake_cleaned, river_lake_int_filtered, riv)
        print(f"==== Number of lakes after removing lakes from segments that intersect with more than 3 lakes: {len(lake_cleaned)} ====")
        #lake_cleaned, river_lake_int_filtered = self._enforce_one_lake_per_river_segment(lake_cleaned, river_lake_int_filtered)
        #print(f"==== Number of lakes after enforcing one lake per river segment: {len(lake_cleaned)} ====")
        lake_cleaned, river_lake_int_filtered = self._identify_lake_type(lake_cleaned, river_lake_int_filtered, riv)
        print(f"==== Number of lakes after identifying the graph number within a lake: {len(lake_cleaned)} ====")
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
        # print(intersected.columns)
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

    def _remove_lakes_touching_only_one_river_endpoint(self,
                                                       riv: gpd.GeoDataFrame,
                                                       lake: gpd.GeoDataFrame):
        """
        Remove lakes that touch only one river segment at their start or end points.
        Only lakes touching two or more river segments at endpoints are kept.

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
        # Spatial join start/end points with lakes
        start_join = gpd.sjoin(start_gdf, lake, how="inner", predicate="intersects")
        end_join   = gpd.sjoin(end_gdf, lake, how="inner", predicate="intersects")
        # Combine start/end joins
        combined = pd.concat([start_join[["LakeCOMID", "COMID"]],
                              end_join[["LakeCOMID", "COMID"]]])
        # Count number of unique river segments per lake
        seg_count = combined.groupby("LakeCOMID")["COMID"].nunique()
        # Keep lakes that touch at least 2 river segments at endpoints
        keep_ids = seg_count[seg_count > 1].index.tolist()
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
        #print("Number of lakes in the intersection:", num_lakes)
        m = (
            river_lake_int.groupby("COMID")["LakeCOMID"]
            .nunique()
            .gt(1)
            .sum()
        )
        #print("Number of river segments intersecting more than one lake:", m)
        return river_lake_int

    def _remove_lakes_int_with_one_river_segment(self,
                                                 lake: gpd.GeoDataFrame,
                                                 river_lake_int: gpd.GeoDataFrame):
        """
        Remove lakes that intersect only one river segment.
        Both the river-lake intersection table and the lake GeoDataFrame are refined.

        Parameters
        ----------
        lake : GeoDataFrame
            Lake polygons with LakeCOMID.
        river_lake_int : GeoDataFrame
            Rows mapping river segments to lake polygons (must contain COMID + LakeCOMID).

        Returns
        -------
        (lake_filtered, river_lake_int_filtered)
            lake_filtered              -> lakes intersecting >1 river segment
            river_lake_int_filtered    -> cleaned rows matching lake_filtered
        """
        df = river_lake_int.copy()
        # Count unique river segments per lake
        seg_count = df.groupby("LakeCOMID")["COMID"].nunique()
        # Lakes touching more than one river segment
        keep_ids = seg_count[seg_count > 1].index.tolist()
        # Filter both datasets
        river_lake_int_filtered = df[df["LakeCOMID"].isin(keep_ids)].reset_index(drop=True)
        lake_filtered = lake[lake["LakeCOMID"].isin(keep_ids)].reset_index(drop=True)
        #print("Number of lakes after removing single-segment lakes:", len(keep_ids))
        return lake_filtered, river_lake_int_filtered

    def _remove_lakes_with_repeated_max_uparea(self,
                                               lake: gpd.GeoDataFrame,
                                               river_lake_int: gpd.GeoDataFrame):
        """
        Remove lakes where the maximum uparea is repeated for more than one COMID.
        Parameters
        ----------
        lake : GeoDataFrame
            Lake polygons with LakeCOMID.
        river_lake_int : GeoDataFrame
            Intersections containing COMID, LakeCOMID, uparea.
        Returns
        -------
        (lake_filtered, river_lake_int_filtered)
        """
        df = river_lake_int.copy()
        remove_ids = []
        # Process each lake
        for lake_id, sub in df.groupby("LakeCOMID"):
            max_up = sub["uparea"].max()
            count_max = (sub["uparea"] == max_up).sum()
            # Remove lake if maximum uparea is repeated
            if count_max > 1:
                remove_ids.append(lake_id)
        # Apply filtering
        lake_filtered = lake[~lake["LakeCOMID"].isin(remove_ids)].reset_index(drop=True)
        river_lake_int_filtered = df[~df["LakeCOMID"].isin(remove_ids)].reset_index(drop=True)
        #print(f"Removed {len(remove_ids)} lakes where max uparea repeats across multiple COMIDs.")
        return lake_filtered, river_lake_int_filtered

    def _supress_number_of_lakes_to_two_per_riv_segment(self,
                                                        lake: gpd.GeoDataFrame,
                                                        river_lake_int: gpd.GeoDataFrame,
                                                        riv_original: gpd.GeoDataFrame):
        """
        For river segments intersecting 3 or more lakes, keep only the lakes
        that intersect the original start or end point of the river segment.
        All other lakes are removed from both 'lake' and 'river_lake_int'.
        Parameters
        ----------
        lake : GeoDataFrame
            Lake polygons. Must contain 'LakeCOMID'.
        river_lake_int : GeoDataFrame
            River–lake intersections. Must contain 'COMID' and 'LakeCOMID'.
        riv_original : GeoDataFrame
            Original river geometries (before modification).
            Must contain:
                - 'COMID'
                - 'geometry' (LineString)
        Returns
        -------
        lake : GeoDataFrame
        river_lake_int : GeoDataFrame
        """
        lake = lake.copy()
        river_lake_int = river_lake_int.copy()
        lakes_to_remove = set()
        # Group intersections by river segment
        for comid, group in river_lake_int.groupby("COMID"):
            # Only suppress when 3+ lakes intersect the same river segment
            if len(group) < 3:
                continue
            # Find the ORIGINAL river segment geometry
            riv = riv_original.loc[riv_original["COMID"] == comid]
            if riv.empty:
                continue
            # inside your loop
            line = riv.iloc[0].geometry
            # check if geometry exists and is a LineString
            if line is None or line.is_empty or not isinstance(line, LineString):
                continue  # skip this river segment
            # get start and end points safely
            start_point = Point(line.coords[0])
            end_point = Point(line.coords[-1])
            # Identify lakes touching either endpoint
            touching_lakes = []
            for lake_id in group["LakeCOMID"]:
                lake_geom = lake.loc[lake["LakeCOMID"] == lake_id].geometry.iloc[0]
                if lake_geom.intersects(start_point) or lake_geom.intersects(end_point):
                    touching_lakes.append(lake_id)
            # Determine which lakes must be removed
            suppressed = set(group["LakeCOMID"]) - set(touching_lakes)
            lakes_to_remove.update(suppressed)
        # Apply removal
        lake = lake[~lake["LakeCOMID"].isin(lakes_to_remove)]
        river_lake_int = river_lake_int[~river_lake_int["LakeCOMID"].isin(lakes_to_remove)]
        return lake, river_lake_int



    def _enforce_one_lake_per_river_segment(self,
                                            lake: gpd.GeoDataFrame,
                                            river_lake_int: gpd.GeoDataFrame):
        """
        Enforce that each river segment has at most one lake.
        Logic:
            1. For each river segment (COMID) with multiple lakes, keep the lake with largest area.
            2. If multiple lakes have the same area, keep the lake with the largest upstream area (uparea).
            3. Remove other lakes from both `lake` and `river_lake_int`.
        Parameters
        ----------
        lake : GeoDataFrame
            Lake polygons, must contain 'LakeCOMID'.
        river_lake_int : GeoDataFrame
            River-lake intersections, must contain 'COMID', 'LakeCOMID', 'unitarea', 'uparea'.
        Returns
        -------
        lake_filtered : GeoDataFrame
        river_lake_int_filtered : GeoDataFrame
        """
        river_lake_int = river_lake_int.copy()
        # Step 1: For each river segment, mark lakes that are not the largest in area
        river_lake_int['remove'] = river_lake_int['unitarea'] != river_lake_int.groupby('COMID')['unitarea'].transform('max')
        # Step 2: For ties in unitarea, keep lake with largest uparea
        tied_segments = river_lake_int.groupby('COMID').filter(lambda g: (g['unitarea'] == g['unitarea'].max()).sum() > 1)
        for comid, group in tied_segments.groupby('COMID'):
            max_area = group['unitarea'].max()
            max_area_lakes = group[group['unitarea'] == max_area]
            # Find the lake with maximum uparea
            lake_to_keep = max_area_lakes.loc[max_area_lakes['uparea'].idxmax(), 'LakeCOMID']
            # Mark other lakes for removal
            remove_lakes = set(max_area_lakes['LakeCOMID']) - {lake_to_keep}
            river_lake_int.loc[river_lake_int['LakeCOMID'].isin(remove_lakes), 'remove'] = True
        # Step 3: Propagate removal to all rows of same LakeCOMID
        lake_ids_to_remove = river_lake_int.loc[river_lake_int['remove'], 'LakeCOMID'].unique()
        river_lake_int.loc[river_lake_int['LakeCOMID'].isin(lake_ids_to_remove), 'remove'] = True
        # Step 4: Filter river-lake intersections
        river_lake_int_filtered = river_lake_int[~river_lake_int['remove']].drop(columns=['remove']).reset_index(drop=True)
        # Step 5: Filter lakes
        lake_filtered = lake[~lake['LakeCOMID'].isin(lake_ids_to_remove)].reset_index(drop=True)
        #print('Number of lakes after enforcing one lake per river segment:', len(lake_filtered['LakeCOMID'].unique()))
        return lake_filtered, river_lake_int_filtered



    def _identify_lake_type(self,
                            lake: gpd.GeoDataFrame,
                            riv_lake_int: gpd.GeoDataFrame,
                            riv: gpd.GeoDataFrame):
        """
        Classify lakes as exorheic or endorheic based on river network connectivity.
        Rules:
          1) If lake intersects only ONE river network:
                - Identify most downstream segment (max uparea)
                - If its length inside lake < original river length → EXORHEIC (keep)
                - Else → remove lake (not resolvable)
          2) If lake intersects MULTIPLE river networks:
                - For each network, find if last COMID has NextDownCOMID <= 0
                - If ANY network is closed → ENDORHEIC (keep)
                - Else → remove lake
          3) After classification:
                - Each lake must have EXACTLY ONE of:
                        exorheic = 1, endorheic = 0
                    OR  exorheic = 0, endorheic = 1
                - Lakes violating this rule are removed.
        Returns
        -------
        lake_filtered, riv_lake_int_filtered
        """
        df_int = riv_lake_int.copy()
        lake = lake.copy()
        # Add classification columns
        lake["exorheic"] = 0
        lake["endorheic"] = 0
        lakes_to_remove = []
        # Build full river graph
        original_graph = Utility.create_graph(
            riv["COMID"].tolist(),
            riv["NextDownCOMID"].tolist()
        )
        # Add original river lengths (temporary)
        riv = riv.copy()
        riv["_length_org"] = riv.geometry.length
        # Add intersection lengths (temporary)
        if "length_in_lake" not in df_int.columns:
            df_int["_length_in_lake"] = df_int.geometry.length
            length_col = "_length_in_lake"
        else:
            length_col = "length_in_lake"
        # ----------------------------------------------------------
        # Process each lake
        # ----------------------------------------------------------
        for lake_id, group in df_int.groupby("LakeCOMID"):
            comids = group["COMID"].tolist()
            num_parts, components = Utility.count_network_parts(original_graph, comids)
            # ======================================================
            # CASE 1 — Single connected river network
            # ======================================================
            if num_parts == 1:
                # Most downstream segment = max uparea
                max_uparea = group["uparea"].max()
                ds_row = group[group["uparea"] == max_uparea].iloc[0]
                comid_ds = ds_row["COMID"]
                length_in_lake = ds_row[length_col]
                length_original = float(riv.loc[riv["COMID"] == comid_ds, "_length_org"])
                if length_in_lake < length_original:
                    # EXORHEIC lake
                    lake.loc[lake["LakeCOMID"] == lake_id, "exorheic"] = 1
                else:
                    # Not resolvable
                    lakes_to_remove.append(lake_id)
                continue
            # ======================================================
            # CASE 2 — Multiple river networks enter the lake
            # ======================================================
            keep = False
            for comp in components:
                sub = group[group["COMID"].isin(comp)]
                # If ANY downstream segment has NextDownCOMID <= 0 → closed basin
                if any(sub["NextDownCOMID"] <= 0):
                    keep = True
                    break
            if keep:
                lake.loc[lake["LakeCOMID"] == lake_id, "endorheic"] = 1
            else:
                lakes_to_remove.append(lake_id)
        # ----------------------------------------------------------
        # FINAL VALIDATION RULE
        # Each lake must have EXACTLY one of {exorheic, endorheic} = 1
        # ----------------------------------------------------------
        invalid = lake[(lake["exorheic"] + lake["endorheic"]) != 1]["LakeCOMID"].tolist()
        lakes_to_remove.extend(invalid)
        lakes_to_remove = list(set(lakes_to_remove))  # unique
        # ----------------------------------------------------------
        # Filter outputs
        # ----------------------------------------------------------
        lake_filtered = lake[~lake["LakeCOMID"].isin(lakes_to_remove)].reset_index(drop=True)
        riv_lake_int_filtered = df_int[~df_int["LakeCOMID"].isin(lakes_to_remove)].reset_index(drop=True)
        #print(f"Removed {len(lakes_to_remove)} unresolved lakes (graph-based check).")
        # ----------------------------------------------------------
        # Drop temporary columns
        # ----------------------------------------------------------
        riv.drop(columns=["_length_org"], inplace=True, errors="ignore")
        df_int.drop(columns=["_length_in_lake"], inplace=True, errors="ignore")
        return lake_filtered, riv_lake_int_filtered