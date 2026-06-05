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
    ) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:

        cat = cat.copy()
        riv = riv.copy()

        required_cols = {"associated_COMID", "geometry"}
        if not required_cols.issubset(singlelake.columns):
            raise ValueError(f"singlelake must contain {required_cols}")

        if not (cat.crs == singlelake.crs == riv.crs):
            raise ValueError("CRS mismatch between inputs")

        # Precompute maps (fast lookup)
        riv_geom_map = riv.set_index("COMID")["geometry"].to_dict()

        valid_lakes = []  # keep only valid ones

        for _, row in singlelake.iterrows():

            comid = row["associated_COMID"]
            lake_geom = row.geometry

            # ---- find catchment ----
            cat_mask = cat["COMID"] == comid
            if not cat_mask.any():
                continue

            cidx = cat.index[cat_mask][0]
            cat_geom = cat.at[cidx, "geometry"]

            area_org = cat_geom.area

            # subtract lake
            new_cat_geom = cat_geom.difference(lake_geom)

            if new_cat_geom.is_empty:
                continue

            area_new = new_cat_geom.area
            area_ratio = area_new / area_org if area_org > 0 else 0

            # ---- river ----
            if comid not in riv_geom_map:
                continue

            riv_mask = riv["COMID"] == comid
            if not riv_mask.any():
                continue

            ridx = riv.index[riv_mask][0]
            riv_geom = riv.at[ridx, "geometry"]

            length_org = riv_geom.length

            # ⚠️ you are scaling length, not clipping → OK for now
            length_ratio = area_ratio if length_org > 0 else 0

            # ---- FILTER CONDITION ----
            if area_ratio == 0 or length_ratio == 0:
                # skip this lake completely
                continue

            # ---- APPLY UPDATES ----

            # update catchment
            cat.at[cidx, "geometry"] = new_cat_geom

            if "unitarea" in cat.columns:
                cat.at[cidx, "unitarea"] *= area_ratio

            # update river
            riv.at[ridx, "length"] = length_org * length_ratio

            # keep this lake
            valid_lakes.append(row)

        # ---- rebuild filtered singlelake ----
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
        singlelake["exorheic"] = 0
        singlelake["endorheic"] = 0
        singlelake["non_channelized"] = 0

        # -------------------------------------
        # 3. Insert lakes into cat and riv
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
                "NextDownCOMID": None,
                "geometry": row.geometry,
                "length": row.geometry.length,
                "islake": 1,
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

                # existing river now flows into lake
                mask = riv["COMID"] == assoc_comid
                riv.loc[mask, "NextDownCOMID"] = lake_comid

                riv.loc[mask, "inflow"] = 1

            # upstream insertion
            elif position == "up":

                # rivers flowing INTO assoc_comid now flow into lake
                mask = riv["NextDownCOMID"] == assoc_comid
                riv.loc[mask, "NextDownCOMID"] = lake_comid

                riv.loc[mask, "outflow"] = 1

            # optional: mark in/out
            if "inflow" in riv.columns and "outflow" in riv.columns:
                both = riv["inflow"].fillna(0) & riv["outflow"].fillna(0)
                riv.loc[both.astype(bool), "inoutflow"] = 1

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