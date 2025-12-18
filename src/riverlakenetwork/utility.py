import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import os
from   shapely.geometry import Point
import yaml
import shutil
import warnings
import networkx as nx
import re
import copy
from   collections import defaultdict, deque
from typing import (
    Optional,
    Dict,
    Tuple,
    Union,
    Sequence,
    Iterable,
    List,
)

class Utility:

    def compute_uparea(
        riv: pd.DataFrame,
        comid_col: str = "COMID",
        next_col: str = "NextDownCOMID",
        area_col: str = "unitarea",
        out_col: str = "uparea",
    ) -> pd.DataFrame:
        """
        Compute upstream contributing area ("uparea") for a river network.

        Design principles
        -----------------
        - Preserves original NextDownCOMID values (e.g. -9999)
        - Internally treats invalid / terminal downstream IDs as NaN
        - Never propagates flow into non-existent nodes
        - Robust to clipped networks and lake suppression
        - Side-effect free: input DataFrame is not modified
        """

        # --------------------------------------------------
        # 0. Copy + enforce clean state
        # --------------------------------------------------
        df = riv.copy()

        # Always recompute uparea
        if out_col in df.columns:
            df = df.drop(columns=out_col)

        # Enforce integer COMIDs
        df[comid_col] = df[comid_col].astype(int)
        df[next_col] = df[next_col].astype("Int64")  # preserves -9999

        # --------------------------------------------------
        # 1. Prepare area values
        # --------------------------------------------------
        df[area_col] = df[area_col].fillna(0.0).astype(float)

        # --------------------------------------------------
        # 2. Prepare COMID set
        # --------------------------------------------------
        comids = set(df[comid_col])

        # --------------------------------------------------
        # 3. Create CLEAN downstream column (internal only)
        # --------------------------------------------------
        next_clean = df[next_col].replace(-9999, np.nan)

        # Downstream IDs not in this network → terminal
        next_clean.loc[~next_clean.isin(comids)] = np.nan

        # --------------------------------------------------
        # 4. Build topology dictionaries
        # --------------------------------------------------
        nextdown = dict(zip(df[comid_col], next_clean))
        uparea = dict(zip(df[comid_col], df[area_col]))

        # --------------------------------------------------
        # 5. Compute indegree (number of upstream tributaries)
        # --------------------------------------------------
        indegree = defaultdict(int)
        for u, d in nextdown.items():
            if pd.notna(d):
                indegree[int(d)] += 1

        # --------------------------------------------------
        # 6. Initialize queue with headwaters
        # --------------------------------------------------
        queue = deque([cid for cid in comids if indegree.get(cid, 0) == 0])

        # --------------------------------------------------
        # 7. Topological accumulation
        # --------------------------------------------------
        while queue:
            u = queue.popleft()
            d = nextdown.get(u)

            # Terminal segment
            if pd.isna(d):
                continue

            d = int(d)
            uparea[d] += uparea[u]
            indegree[d] -= 1

            if indegree[d] == 0:
                queue.append(d)

        # --------------------------------------------------
        # 8. Assign output (topology untouched)
        # --------------------------------------------------
        df[out_col] = df[comid_col].map(uparea)

        return df

    def add_immediate_upstream (df,
                                mapping = {'id':'LINKNO','next_id':'DSLINKNO'}):

        # this function add immediate segment of upstream for a river network if not provided
        # it first convert the df into a networkx derected graph, finds the sucessores for
        # river segments, provide the maximume existing upstream segments in column called maxup
        # and the values in up1, up2, up3, etc

        # remove existing max up and up*
        df = df.drop(columns=df.filter(regex=r'^(maxup|up\d+)$').columns, errors="ignore")

        # get the name of ID and downID
        downID = mapping.get('next_id')
        ID = mapping.get('id')

        # Create a directed graph
        G = nx.DiGraph()

        # Add edges from the DataFrame (reversing the direction)
        for _, row in df.iterrows():
            # print(row[ID], row[downID])
            if row[downID] > -0.01:  # Skip nodes with negative downstream
                G.add_edge(row[downID], row[ID])

        # Find immediate upstream nodes for each node
        immediate_upstream = {}
        for node in G.nodes():
            immediate_upstream[node] = list(G.successors(node))

        # Create a new column containing lists of immediate upstream nodes
        df['upstream'] = df[ID].apply(lambda x: immediate_upstream[x] if x in immediate_upstream else [])

        # Find the maximum length of the lists in the 'upstream' column
        df['maxup'] = 0
        df['maxup'] = df['upstream'].apply(len)

        # Create new columns 'maxup', 'up1', 'up2', 'up3', etc.
        max_length = df['maxup'].max()
        if max_length > 0:
            for i in range(max_length):
                df[f'up{i + 1}'] = df['upstream'].apply(lambda x: x[i] if i < len(x) else 0)
        else:
            print('It seems there is no upstream segment for the provided river network. '+\
                  'This may mean the river network you are working may have first order rivers '+\
                  'that are not connected.')
        # drop upstream
        df = df.drop(columns = 'upstream')
        return df


    def create_graph(segment_ids, next_down_ids):
        """Create a directed graph from river network data."""
        G = nx.DiGraph()
        for seg, down in zip(segment_ids, next_down_ids):
            if pd.isna(down) or down is None or down < 0:
                G.add_node(seg)
            else:
                G.add_edge(seg, down)
        return G

    def count_network_parts(graph, COMID_sample=None):
        """Count the number of connected parts in a river network graph."""
        # Get all weakly connected components
        connected_components = list(nx.weakly_connected_components(graph))

        if COMID_sample is None:
            return len(connected_components), connected_components

        # Find which component each sampled node belongs to
        sample_components = set()
        for component in connected_components:
            if any(node in component for node in COMID_sample):
                sample_components.add(frozenset(component))  # Use frozenset to store unique components

        return len(sample_components), [set(comp) for comp in sample_components]



    def merit_read_file (pfaf: str,
                         riv_file_template: str,
                         cat_file_template: str,
                         cst_file_template: Optional [str] = None):

        # local function to read costal hillslope
        def merit_cst_prepare(
            cst: gpd.GeoDataFrame,
            cst_col: Optional[Dict[str, str]] = None,
            cat: Optional[gpd.GeoDataFrame] = None,
            cat_col_id: Optional[str] = None,
            cst_col_id_reset: bool = True,
            crs: int = 4326,
            *args,
            ) -> gpd.GeoDataFrame:
            # get the possible existing id, area if exists
            cst_col_id = 'COMID'
            cst_col_area = 'unitarea'
            if cst_col is not None:
                cst_col_id = cst_col.get('id')
                cst_col_area = cst_col.get('area')
            if not cst.crs:
                cst.set_crs(epsg=4326, inplace=True, allow_override=True)
                warnings.warn('CRS of the coastal hillslope Shapefile has been assumed to be EPSG:4326')
            if cst_col_id_reset:
                max_cat_id = 0
                if cat is not None:
                    max_cat_id = cat[cat_col_id].max()
                cst[cst_col_id] = range(max_cat_id+1,
                                        max_cat_id+1+len(cst))
            else:
                if not cst_col_id in cst.columns:
                    sys.exit('the corresponding id is not given for cosatl hillslope')
                else:
                    max_cat_id = 0
                    if cat is not None:
                        max_cat_id = cat[cat_col_id].max()
                    min_cst_id = cst[cst_col_id].min()
                    if min_cst_id < max_cat_id:
                        sys.exit('there is some mixed up COMID between the cat and costal hillslope')
            if not cst_col_area in cst.columns: # then we need to populate the id
                cst[cst_col_area] = cst.to_crs(epsg=6933).area / 1e6
            # drop FID column
            cst = cst.drop(columns = ['FID'])
            # return
            return cst

        def add_cat_only_comids_to_riv(riv: pd.DataFrame, cat: pd.DataFrame):
            riv = riv.copy()
            cat = cat.copy()

            # Ensure consistent COMID type
            riv["COMID"] = riv["COMID"].astype(int)
            cat["COMID"] = cat["COMID"].astype(int)

            # -----------------------------
            # 1. Identify CAT-only COMIDs
            # -----------------------------
            missing_comids = sorted(set(cat["COMID"]) - set(riv["COMID"]))
            if not missing_comids:
                return riv

            # -----------------------------
            # 2. Create empty riv rows
            # -----------------------------
            new_rows = pd.DataFrame(index=range(len(missing_comids)), columns=riv.columns)
            new_rows["COMID"] = missing_comids

            # -----------------------------
            # 3. Transfer unitarea → uparea
            # -----------------------------
            unitarea_map = cat.set_index("COMID")["unitarea"].astype(float)
            new_rows["uparea"] = new_rows["COMID"].map(unitarea_map)

            # -----------------------------
            # 4. Set topology defaults
            # -----------------------------
            new_rows["NextDownID"] = 0
            new_rows["lengthkm"] = 0
            new_rows["maxup"] = 0

            # up* columns EXCEPT uparea
            up_cols = [
                c for c in riv.columns
                if c.lower().startswith("up") and c.lower() != "uparea"
            ]
            new_rows[up_cols] = 0

            # -----------------------------
            # 5. Append and sort
            # -----------------------------
            riv = pd.concat([riv, new_rows], ignore_index=True)
            riv = riv.sort_values("COMID").reset_index(drop=True)

            return riv

        def fix_DownID(riv: pd.DataFrame) -> pd.DataFrame:
            riv = riv.copy()

            riv["COMID"] = riv["COMID"].astype(int)
            riv["NextDownID"] = pd.to_numeric(
                riv["NextDownID"], errors="coerce"
            ).astype("Int64")

            valid_comids = set(riv["COMID"])

            invalid = (
                riv["NextDownID"].notna()
                & (
                    (riv["NextDownID"] <= 0)
                    | ~riv["NextDownID"].isin(valid_comids)
                )
            )

            riv.loc[invalid, "NextDownID"] = -9999
            return riv

        # read files cat, riv, cst
        riv = gpd.read_file(os.path.join(riv_file_template.replace('*', pfaf)))
        cat = gpd.read_file(os.path.join(cat_file_template.replace('*', pfaf)))
        # check the length of riv and cat
        if len(riv) != len(cat):
            raise error
        if not cst_file_template is None:
            cst = gpd.read_file(os.path.join(cst_file_template.replace('*', pfaf)))
            # add cat and cst
            cst = merit_cst_prepare(cst,
                                    {'id':'COMID','area':'unitarea'},
                                    cat = cat,
                                    cat_col_id = 'COMID')
        else:
            cst = None
        # merge the cat and cst
        if not cst is None:
            cat = gpd.GeoDataFrame(pd.concat([cat, cst]))
        else:
            cat = cat
        # assign crs
        cat.set_crs(epsg=4326, inplace=True, allow_override=True)
        cat.reset_index(drop=True, inplace=True)
        # sort COMID
        riv.sort_values(by='COMID', axis='index', inplace=True)
        riv.reset_index(drop=True, inplace=True)
        # sort COMID
        cat.sort_values(by='COMID', axis='index', inplace=True)
        cat.reset_index(drop=True, inplace=True)
        # set the projection
        riv.set_crs(epsg=4326, inplace=True, allow_override=True)
        cat.set_crs(epsg=4326, inplace=True, allow_override=True)
        # fix the network topology
        riv = add_cat_only_comids_to_riv(riv,cat)
        # fix network topology
        riv = fix_DownID(riv)
        # return
        return riv, cat



