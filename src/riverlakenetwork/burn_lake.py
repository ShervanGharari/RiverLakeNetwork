import geopandas as gpd
from   shapely.geometry import Point
import pandas as pd
import numpy as np
from   .utility import Utility   # adjust path if needed


class BurnLakes:

    def __init__(
        self,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame):

        #cat = self._cat_correction(cat, lake)
        #riv = self._riv_correction(riv, lake)
        riv, cat, lake = self._riv_topology_correction(riv, cat, lake)

        self.cat_corrected = cat
        self.riv_corrected = riv


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
        # 3. Assign COMIDs to lakes after sorting
        # -------------------------------------
        maxCOMID = max(riv["COMID"].max(), cat["COMID"].max())
        n_lakes = len(lake)
        lake["COMID"] = list(range(maxCOMID + 1, maxCOMID + 1 + n_lakes))
        lake["islake"] = 1
        # -------------------------------------
        # 4. Stack lakes with riv and cat
        # -------------------------------------
        cat_geometry_corrected = self._cat_geometry_correction(cat, lake)
        riv_gemoetry_corrected = self._riv_geometry_correction(riv, lake)
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
            if is_exhoreic_flag(lk.get("exorheic", 0)):
                subset = riv.loc[riv["COMID"].isin(riv_ids)]
                outflow_riv = subset.loc[subset["uparea"].idxmax(), "COMID"]
                riv.loc[riv["COMID"] == outflow_riv, "outflow"] = 1
                riv.loc[riv["COMID"] == outflow_riv, "inflow"] = 0
                riv.loc[riv["LakeCOMID"] == lk_comid, "NextDownCOMID"] = outflow_riv
            # ---- 3. All intersecting rivers drain INTO this lake ----
            riv.loc[riv["COMID"].isin(riv_ids), "NextDownCOMID"] = lk_comid
        # -------------------------------------
        # 6. Update geometry and unit area for riv and cat
        # -------------------------------------
        # Map corrected geometry and length from riv_geometry_corrected
        geom_map = riv_gemoetry_corrected.set_index("COMID")["geometry"].to_dict()
        length_map = riv_gemoetry_corrected.set_index("COMID")["length"].to_dict()
        # Only replace geometry and length if length_ratio < 1
        mask = riv.get("length_ratio", 1) < 1
        riv.loc[mask, "geometry"] = riv.loc[mask, "COMID"].map(geom_map)
        riv.loc[mask, "length"] = riv.loc[mask, "COMID"].map(length_map)
        # 2. Map corrected unitarea and geometry from cat_geometry_corrected
        cat_geom_map = cat_geometry_corrected.set_index("COMID")["geometry"].to_dict()
        cat_area_map = cat_geometry_corrected.set_index("COMID")["unitarea"].to_dict()
        riv["geometry"] = riv["COMID"].map(cat_geom_map).combine_first(riv["geometry"])
        riv["unitarea"] = riv["COMID"].map(cat_area_map).fillna(riv["unitarea"])
        # 3. Map lake geometries for lake COMIDs
        lake_geom_map = lake.set_index("COMID")["geometry"].to_dict()
        riv.loc[riv.get("islake", 0) == 1, "geometry"] = riv.loc[riv.get("islake", 0) == 1, "COMID"].map(lake_geom_map)
        # return
        return riv, cat, lake
