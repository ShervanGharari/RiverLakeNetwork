import geopandas as gpd
from   shapely.geometry import Point
import pandas as pd
import numpy as np
from   collections import defaultdict, deque
from   .utility import Utility   # adjust path if needed


class NetworkTopologyCorrectionSingleSegmentLakes:

    def __init__(
        self,
        singlelake: gpd.GeoDataFrame,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
        ):

        riv, cat, lake = self._riv_topology_correction(singlelake, cat, lake, riv)

        self.cat_corrected = cat
        self.riv_corrected = riv
        self.lake_corrected = lake

    def _geometry_correction(
        self,
        singlelake: gpd.GeoDataFrame,
        cat: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
    ):

        cat = cat.copy()
        riv = riv.copy()

        required_cols = {"associated_COMID", "geometry"}
        if not required_cols.issubset(singlelake.columns):
            raise ValueError(f"singlelake must contain {required_cols}")

        if not (cat.crs == singlelake.crs == riv.crs):
            raise ValueError("CRS mismatch between inputs")

        valid_lakes = []

        for _, row in singlelake.iterrows():

            comid = row["associated_COMID"]
            lake_geom = row.geometry

            # -------------------------
            # Catchment update
            # -------------------------
            cat_mask = cat["COMID"] == comid
            if not cat_mask.any():
                continue

            cidx = cat.index[cat_mask][0]
            cat_geom = cat.at[cidx, "geometry"]

            area_org = cat_geom.area
            new_cat_geom = cat_geom.difference(lake_geom)

            if new_cat_geom.is_empty:
                continue

            area_ratio = new_cat_geom.area / area_org if area_org > 0 else 0

            # -------------------------
            # River update (NEW FIX)
            # -------------------------
            riv_mask = riv["COMID"] == comid
            if not riv_mask.any():
                continue

            ridx = riv.index[riv_mask][0]
            riv_geom = riv.at[ridx, "geometry"]

            length_org = riv_geom.length

            # 🔥 CLIP river geometry by lake
            new_riv_geom = riv_geom.difference(lake_geom)

            # if lake fully removes river segment → skip
            if new_riv_geom.is_empty:
                continue

            length_new = new_riv_geom.length
            length_ratio = length_new / length_org if length_org > 0 else 0

            # -------------------------
            # FILTER CONDITION
            # -------------------------
            if area_ratio == 0 or length_ratio == 0:
                continue

            # -------------------------
            # APPLY UPDATES
            # -------------------------
            cat.at[cidx, "geometry"] = new_cat_geom
            riv.at[ridx, "geometry"] = new_riv_geom   # ✅ IMPORTANT FIX

            if "unitarea" in cat.columns:
                cat.at[cidx, "unitarea"] *= area_ratio

            if "length" in riv.columns:
                riv.at[ridx, "length"] = length_new

            valid_lakes.append(row)

        singlelake_out = gpd.GeoDataFrame(valid_lakes, crs=singlelake.crs).reset_index(drop=True)

        return singlelake_out, cat, riv

    def _riv_topology_correction(
        self,
        singlelake: gpd.GeoDataFrame,
        cat: gpd.GeoDataFrame,
        lake: gpd.GeoDataFrame,
        riv: gpd.GeoDataFrame,
    ):
        """
        Build lake–river hydraulic topology.

        Steps:
        1. Apply geometry correction
        2. Assign COMIDs to lakes
        3. Insert lakes into cat and riv
        4. Update topology (NextDownCOMID)
        5. Recompute attributes
        """

        # -------------------------------------
        # Copies
        # -------------------------------------
        riv = riv.copy()
        cat = cat.copy()
        lake = lake.copy()

        # -------------------------------------
        # 1. Geometry correction
        # -------------------------------------
        singlelake, cat, riv = self._geometry_correction(singlelake, cat, riv)

        # -------------------------------------
        # 2. Assign COMIDs to lakes
        # -------------------------------------
        max_comid = max(riv["COMID"].max(), cat["COMID"].max())
        singlelake = singlelake.copy()

        singlelake["COMID"] = range(max_comid + 1, max_comid + 1 + len(singlelake))

        # flags
        singlelake["islake"] = 1
        singlelake["exorheic"] = 1 # assumption
        singlelake["endorheic"] = 0
        singlelake["non_channelized"] = 0
        singlelake["single_segment_lake"] = 1

        # -------------------------------------
        # 3. Insert lakes into cat and riv, and lake
        # -------------------------------------
        for _, row in singlelake.iterrows():

            lake_comid = row["COMID"]
            assoc_comid = row["associated_COMID"]
            position = str(row.get("position", "")).lower()

            # ---- add to CAT ----
            new_cat_row = row.copy()
            new_cat_row["COMID"] = lake_comid

            cat = gpd.GeoDataFrame(
                pd.concat([cat, gpd.GeoDataFrame([new_cat_row], crs=cat.crs)],
                          ignore_index=True),
                crs=cat.crs
            )

            # ---- add to RIV ----
            new_riv_row = {
                "COMID": lake_comid,
                "NextDownCOMID": -9999,
                "LakeCOMID": row.LakeCOMID,
                "geometry": row.geometry,
                "length": None,
                "islake": row.islake,
                "exorheic": row.exorheic,
                "endorheic": row.endorheic,
                "non_channelized": row.non_channelized,
                "single_segment_lake": row.single_segment_lake,
            }

            riv = gpd.GeoDataFrame(
                pd.concat([riv, gpd.GeoDataFrame([new_riv_row], crs=riv.crs)],
                          ignore_index=True),
                crs=riv.crs
            )

            # -------------------------------------
            # 4. Update topology
            # -------------------------------------

            # downstream insertion
            if position == "down":

                # find upstream river segment (assoc_comid)
                mask = riv["COMID"] == assoc_comid
                if not mask.any():
                    continue

                # safe extraction
                nextCOMID = riv.loc[mask, "NextDownCOMID"].iloc[0]

                # A → L
                riv.loc[mask, "NextDownCOMID"] = lake_comid
                riv.loc[mask, "inflow"] = 1

                # L → B
                mask_lake = riv["COMID"] == lake_comid
                if mask_lake.any():
                    riv.loc[mask_lake, "NextDownCOMID"] = nextCOMID

            # upstream insertion
            elif position == "up":

                # A → B becomes A → L
                mask = riv["NextDownCOMID"] == assoc_comid

                if mask.any():
                    riv.loc[mask, "NextDownCOMID"] = lake_comid
                    riv.loc[mask, "outflow"] = 1

                # L → B
                mask_lake = riv["COMID"] == lake_comid
                if mask_lake.any():
                    riv.loc[mask_lake, "NextDownCOMID"] = assoc_comid
                    riv.loc[mask_lake, "inflow"] = 1

            # optional: mark in/out
            if "inflow" in riv.columns and "outflow" in riv.columns:
                both = riv["inflow"].fillna(0).astype(bool) & riv["outflow"].fillna(0).astype(bool)
                riv.loc[both.astype(bool), "inoutflow"] = 1

        # update lake with singlelake
        lake = gpd.GeoDataFrame(
            pd.concat([lake, singlelake], ignore_index=True),
            crs=lake.crs
        )


        # -------------------------------------
        # 5. Transfer unitarea, update int riv
        # -------------------------------------
        if "unitarea" in cat.columns:
            cat_map = cat.set_index("COMID")["unitarea"]
            riv["unitarea"] = riv["COMID"].map(cat_map)

        # -------------------------------------
        # 6. Recompute topology
        # -------------------------------------
        riv = Utility.add_immediate_upstream(
            riv,
            mapping={"id": "COMID", "next_id": "NextDownCOMID"},
        )

        riv = Utility.compute_uparea(riv)

        # -------------------------------------
        # 7. Cleanup columns
        # -------------------------------------
        drop_cols = ["associated_COMID", "position"]

        for df in [lake, cat, riv]:
            df.drop(columns=[c for c in drop_cols if c in df.columns],
                    inplace=True, errors="ignore")

        return riv, cat, lake