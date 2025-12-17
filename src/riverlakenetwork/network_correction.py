import geopandas as gpd
from   shapely.geometry import Point
import pandas as pd
import numpy as np
from   collections import defaultdict, deque
from   .utility import Utility   # adjust path if needed


class NetworkTopologyCorrection:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame):

        riv, cat, lake = self._riv_topology_correction(riv, cat, lake)

        self.cat_corrected = cat
        self.riv_corrected = riv
        self.lake_corrected = lake


    def _cat_geometry_correction(self, cat: gpd.GeoDataFrame, lake: gpd.GeoDataFrame):
        """Correct CAT 'unitarea' after removing lake-covered areas; replace geometry with difference geometry when partially removed and keep area_ratio."""
        cat_int = gpd.overlay(cat, lake, how="difference")  # compute CAT - LAKE difference
        cat_out = cat.copy()  # copy original CAT
        cat_out["area_org"] = cat_out.geometry.area  # original CAT area
        cat_int["area_out_lake"] = cat_int.geometry.area  # area after removing lake
        area_map = cat_int.set_index("COMID")["area_out_lake"]  # map area_out_lake by COMID (may miss fully removed)
        cat_out["area_out_lake"] = cat_out["COMID"].map(area_map).fillna(0)  # missing -> fully removed -> 0
        cat_out["area_ratio"] = cat_out["area_out_lake"] / cat_out["area_org"]  # compute area ratio (0..1)
        # prepare difference geometry per COMID (dissolve to ensure a single geometry per COMID)
        if not cat_int.empty:
            diff_geom_map = cat_int.dissolve(by="COMID").reset_index().set_index("COMID")["geometry"]
        else:
            diff_geom_map = {}
        # assign geometries: if fully removed -> None; if partially removed -> diff geometry; if unchanged -> keep original
        partially_removed_mask = (cat_out["area_ratio"] > 0) & (cat_out["area_ratio"] < 1)
        cat_out.loc[partially_removed_mask, "geometry"] = cat_out.loc[partially_removed_mask, "COMID"].map(diff_geom_map)
        cat_out.loc[cat_out["area_ratio"] == 0, "geometry"] = None
        # correct unitarea proportionally and keep area_ratio for output
        cat_out["unitarea"] = cat_out["unitarea"] * cat_out["area_ratio"]
        cat_out = cat_out.drop(columns=["area_org", "area_out_lake"])  # keep area_ratio for return
        return cat_out

    def _riv_geometry_correction(self, riv: gpd.GeoDataFrame, lake: gpd.GeoDataFrame):
        """
        Correct river lengths under lakes:

        - length_org from geometry
        - length_ratio = 1 - (length_in_lake / length_org)
        - update 'length' using ratio
        - replace geometry with difference if partially submerged
        - geometry = None if fully submerged
        """
        riv = riv.copy()
        # Original river length (km or projected units)
        riv["length_org"] = riv.geometry.length
        # --- river ∩ lake ---
        riv_int = gpd.overlay(riv, lake, how="intersection")
        # ------------------------------------------------------
        # CASE 1: No intersections → trivial correction
        # ------------------------------------------------------
        if riv_int.empty:
            riv["length_ratio"] = 1.0
            riv["length"] = riv["length"]  # unchanged
            riv = riv.drop(columns=["length_org"])
            return riv
        # ------------------------------------------------------
        # CASE 2: Compute how much of each COMID is inside lakes
        # ------------------------------------------------------
        riv_int["length_in_lake"] = riv_int.geometry.length
        # Total submerged length per COMID
        length_map = riv_int.groupby("COMID")["length_in_lake"].sum()
        # submerged amount mapped to rivers
        submerged = riv["COMID"].map(length_map).fillna(0)
        # Length correction ratio
        riv["length_ratio"] = (1 - submerged / riv["length_org"]).clip(0, 1)
        # ------------------------------------------------------
        # GEOMETRY CORRECTION
        # ------------------------------------------------------
        affected = riv["length_ratio"] < 1
        if affected.any():
            # geometry minus lake
            riv_diff = gpd.overlay(riv, lake, how="difference")
            diff_map = riv_diff.set_index("COMID").geometry
            riv.loc[affected, "geometry"] = riv.loc[affected, "COMID"].map(diff_map)
        # Fully submerged → drop geometry
        riv.loc[riv["length_ratio"] == 0, "geometry"] = None
        # Update corrected length
        riv["length"] = riv["length"] * riv["length_ratio"]
        # Cleanup
        riv = riv.drop(columns=["length_org"])
        return riv


    def _riv_topology_correction(self, riv, cat, lake):
        """
        Build lake–river hydraulic topology using explicit exhoreic/endorheic flag.

        Steps:
        1. Intersect lakes with rivers.
        2. Sort lakes by min/max uparea.
        3. Assign new COMIDs to lakes.
        4. Stack lakes into riv and cat.
        5. Loop lakes (upstream → downstream):
             - assign inflow rivers
             - if lake is exhoreic: assign outflow river
             - update NextDownID
        6. Update riv.unitarea from cat.
        """
        # -------------------------------------
        # Copies
        # -------------------------------------
        riv = riv.copy()
        cat = cat.copy()
        lake = lake.copy()
        # -------------------------------------
        # 1. Intersect lakes with rivers
        # -------------------------------------
        lake_riv = gpd.overlay(riv, lake, how="intersection")
        if lake_riv.empty:
            # If no intersections: keep original lake order
            lake = lake.reset_index(drop=True)
        else:
            # We only need lake geometry and intersecting river uparea
            # Extract lake index using spatial join after overlay (robust)
            lake_idx = gpd.sjoin(lake, lake_riv, how="left", predicate="intersects")
            # lake_idx["uparea_right"] is the river uparea from lake_riv
            # but depending on overlay version it may appear under different names.
            # So detect the uparea column robustly:
            uparea_col = [c for c in lake_idx.columns if "uparea" in c.lower()][0]
            # Compute per-lake max uparea
            lake_max_up = lake_idx.groupby(lake_idx.index)[uparea_col].max()
            # Attach this temporary sorting column
            lake["__sort_up__"] = lake_max_up
            # Missing values → place at end
            lake["__sort_up__"] = lake["__sort_up__"].fillna(float("inf"))
            # -------------------------------------
            # 2. Sort lakes by max upstream area
            # -------------------------------------
            lake = lake.sort_values("__sort_up__").reset_index(drop=True)
            # Remove temporary column
            lake = lake.drop(columns="__sort_up__")
        # -------------------------------------
        # 4. Stack lakes with riv and cat
        # -------------------------------------
        cat_geometry_corrected = self._cat_geometry_correction(cat, lake)
        riv_gemoetry_corrected = self._riv_geometry_correction(riv, lake)
        # -------------------------------------
        # 3. Assign COMIDs to lakes after sorting
        # -------------------------------------
        maxCOMID = max(riv["COMID"].max(), cat["COMID"].max())
        n_lakes = len(lake)
        lake["COMID"] = list(range(maxCOMID + 1, maxCOMID + 1 + n_lakes))
        lake["islake"] = 1
        # -------------------------------------
        # 4. Stack lakes with riv and cat
        # -------------------------------------
        riv = pd.concat([riv, lake], ignore_index=True)
        cat = pd.concat([cat, lake], ignore_index=True)
        # -------------------------------------
        # 5. Build the network topology
        # -------------------------------------
        riv["inflow"] = 0
        riv["outflow"] = 0
        riv["inoutflow"] = 0
        for _, lk in lake.iterrows():
            # Correct field name
            lk_comid = lk["LakeCOMID"]
            comid = lk["COMID"]
            # ---- 1. Get intersecting rivers ----
            riv_ids = lake_riv.loc[lake_riv["LakeCOMID"] == lk_comid, "COMID"].unique()
            if len(riv_ids) == 0:
                continue
            # Mark inflow rivers
            riv.loc[riv["COMID"].isin(riv_ids), "inflow"] = 1
            # ---- 2. Exhoreic lake: identify single outflow ----
            def is_exhoreic_flag(val):
                """
                Robustly check if lake is exhoreic.
                Accepts int, float, string representations of 0/1.
                Returns True only if val represents 1; False otherwise.
                """
                if val is None:
                    return False
                if pd.isna(val):
                    return False
                try:
                    # convert to float first, then check if == 1
                    return float(val) == 1
                except (ValueError, TypeError):
                    return False
            riv.loc[riv["LakeCOMID"] == lk_comid, "NextDownCOMID"] = -9999 # for endorheic and exorheic
            riv.loc[riv["COMID"].isin(riv_ids), "NextDownCOMID"] = comid
            if is_exhoreic_flag(lk.get("exorheic", 0)):
                subset = riv.loc[riv["COMID"].isin(riv_ids)]
                outflow_riv = subset.loc[subset["uparea"].idxmax(), "COMID"]
                riv.loc[riv["COMID"] == outflow_riv, "outflow"] = 1
                riv.loc[riv["COMID"] == outflow_riv, "inflow"] = 0
                riv.loc[riv["LakeCOMID"] == lk_comid, "NextDownCOMID"] = outflow_riv
        # -------------------------------------
        # 6. Update geometry and unit area for riv and cat
        # -------------------------------------
        riv_corr_lookup = riv_gemoetry_corrected[riv_gemoetry_corrected["length_ratio"] < 1].set_index("COMID")
        riv_geom_map = riv_corr_lookup["geometry"].to_dict()
        riv_length_map = riv_corr_lookup["length"].to_dict()
        riv_ratio_map = riv_corr_lookup["length_ratio"].to_dict()
        # Lake geometries
        lake_geom_map = lake.set_index("COMID")["geometry"].to_dict()
        # --- Loop over riv ---
        for idx, row in riv.iterrows():
            comid = row["COMID"]
            # 1. Check length_ratio from corrected rivers
            length_ratio = riv_ratio_map.get(comid, 1)
            # 2. Update geometry and length if length_ratio < 1
            if length_ratio == 0:
                # Fully submerged → geometry None, length 0
                riv.at[idx, "geometry"] = None
                riv.at[idx, "length"] = 0
            elif length_ratio < 1:
                geom = riv_geom_map.get(comid, None)
                if geom is not None and geom.is_valid:
                    riv.at[idx, "geometry"] = geom
                length = riv_length_map.get(comid, None)
                if length is not None:
                    riv.at[idx, "length"] = length
            # 3. Update geometry if this is a lake
            if row.get("islake", 0) == 1:
                geom = lake_geom_map.get(comid, None)
                if geom is not None and geom.is_valid:
                    riv.at[idx, "geometry"] = geom
        # cat correction of geometry and unitarea
        # Prepare lookup maps from corrected CAT
        cat_lookup = cat_geometry_corrected.set_index("COMID")
        cat_geom_map = cat_lookup["geometry"].to_dict()
        cat_area_map = cat_lookup["unitarea"].to_dict()
        cat_ratio_map = cat_lookup.get("area_ratio", pd.Series(1, index=cat_lookup.index)).to_dict()
        # Loop over CAT to update geometry and unitarea
        for idx, row in cat.iterrows():
            comid = row["COMID"]
            # Get area_ratio
            area_ratio = cat_ratio_map.get(comid, 1)
            if area_ratio == 0:
                # Fully removed → geometry None, unitarea 0
                cat.at[idx, "geometry"] = None
                cat.at[idx, "unitarea"] = 0
            else:
                # Update geometry from corrected CAT if available and valid
                geom = cat_geom_map.get(comid, None)
                if geom is not None and geom.is_valid:
                    cat.at[idx, "geometry"] = geom
                # Update unitarea from corrected CAT
                unitarea = cat_area_map.get(comid, None)
                if unitarea is not None:
                    cat.at[idx, "unitarea"] = unitarea
        # pass the unit area from cat to riv
        # first set the unitarea to zero in the riv
        # Build lookup from corrected CAT
        cat_unit_map = cat.set_index("COMID")["unitarea"]
        # Map CAT.unitarea → RIV.unitarea
        riv["unitarea"] = riv["COMID"].map(cat_unit_map)
        # Replace missing or NaN with 0
        riv["unitarea"] = riv["unitarea"].fillna(0)
        # add the inoutflow
        riv["inoutflow"] = ((riv["inflow"] == 1) & (riv["outflow"] == 1)).astype(int)
        # add clean up here, remove the subbasin and riv that are fully under lake
        # both their cat area and length are set to zero
        # this does not apply to inoutflow segments
        # (re)compute uparea
        riv = Utility.compute_uparea(riv)
        # add immediate upstream
        riv = Utility.add_immediate_upstream (riv, mapping = {'id':'COMID','next_id':'NextDownCOMID'})
        # return
        return riv, cat, lake
