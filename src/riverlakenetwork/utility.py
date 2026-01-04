import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import os
from   shapely.geometry import Point, LineString, MultiLineString
from   scipy.spatial import cKDTree
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
        mapping: dict = {
            "id": "COMID",
            "next_id": "NextDownCOMID",
            "unitarea": "unitarea",
        },
        out_col: str = "uparea",
    ) -> pd.DataFrame:
        """
        Compute upstream contributing area (uparea) for a river network.
        Parameters
        ----------
        riv : pd.DataFrame
            River network table.
        mapping : dict
            Column mapping:
                - 'id'        → unique river segment ID
                - 'next_id'   → downstream segment ID
                - 'unitarea'  → local contributing area
        out_col : str
            Name of output upstream area column.
        Returns
        -------
        pd.DataFrame
            Copy of input with computed uparea column.
        """
        # --------------------------------------------------
        # 0. Copy + clean state
        # --------------------------------------------------
        df = riv.copy()
        id_col = mapping["id"]
        next_col = mapping["next_id"]
        area_col = mapping["unitarea"]
        # Always recompute uparea
        if out_col in df.columns:
            df = df.drop(columns=out_col)
        # --------------------------------------------------
        # 1. Enforce types
        # --------------------------------------------------
        df[id_col] = df[id_col].astype(int)
        df[next_col] = df[next_col].astype("Int64")  # preserves -9999
        df[area_col] = df[area_col].fillna(0.0).astype(float)
        # --------------------------------------------------
        # 2. Prepare COMID set
        # --------------------------------------------------
        comids = set(df[id_col])
        # --------------------------------------------------
        # 3. Internal clean downstream column
        # --------------------------------------------------
        next_clean = df[next_col].replace(-9999, np.nan)
        # Downstream IDs not present → terminal
        next_clean.loc[~next_clean.isin(comids)] = np.nan
        # --------------------------------------------------
        # 4. Build topology
        # --------------------------------------------------
        nextdown = dict(zip(df[id_col], next_clean))
        uparea = dict(zip(df[id_col], df[area_col]))
        # --------------------------------------------------
        # 5. Compute indegree
        # --------------------------------------------------
        indegree = defaultdict(int)
        for u, d in nextdown.items():
            if pd.notna(d):
                indegree[int(d)] += 1
        # --------------------------------------------------
        # 6. Initialize headwaters
        # --------------------------------------------------
        queue = deque([cid for cid in comids if indegree.get(cid, 0) == 0])
        # --------------------------------------------------
        # 7. Accumulate upstream area
        # --------------------------------------------------
        while queue:
            u = queue.popleft()
            d = nextdown.get(u)
            if pd.isna(d):
                continue
            d = int(d)
            uparea[d] += uparea[u]
            indegree[d] -= 1
            if indegree[d] == 0:
                queue.append(d)
        # --------------------------------------------------
        # 8. Assign output
        # --------------------------------------------------
        df[out_col] = df[id_col].map(uparea)
        return df

    @staticmethod
    def add_immediate_upstream (df,
                                mapping = {
                                'id':'COMID',
                                'next_id':'NextDownCOMID'}):
        """
        Add immediate upstream connectivity information to a river network table.
        This function identifies all *directly connected upstream river segments*
        for each river segment and appends this information to the input DataFrame.
        The river network is treated as a directed graph in which edges point
        from upstream segments to their immediate downstream segment.
        The function performs the following steps:
        1. Removes any existing upstream-related columns (`maxup`, `up1`, `up2`, ...).
        2. Builds a directed graph representation of the river network using
           the downstream linkage information.
        3. Identifies immediate upstream segments for each river segment.
        4. Computes the number of immediate upstream segments (`maxup`).
        5. Expands upstream connectivity into separate columns (`up1`, `up2`, ...).
        Notes
        -----
        - Downstream identifiers with negative values are treated as terminal
          (i.e., no downstream connection).
        - Upstream segments are ordered arbitrarily based on graph traversal.
        - First-order rivers will have `maxup = 0` and no `up*` columns populated.
        - The function is side-effect free except for modifications to the
          returned DataFrame.
        Parameters
        ----------
        df : pandas.DataFrame
            River network attribute table containing at least the river segment
            identifier and its downstream segment identifier.
        mapping : dict, optional
            Dictionary mapping column roles to DataFrame column names:
            - 'id' : unique river segment identifier (default: 'COMID')
            - 'next_id' : downstream river segment identifier (default: 'NextDownCOMID')
        Returns
        -------
        pandas.DataFrame
            A copy of the input DataFrame with additional columns:
            - `maxup` : number of immediate upstream segments
            - `up1`, `up2`, ..., `upN` : IDs of immediate upstream segments
        """
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

    @staticmethod
    def compute_next_downstream(
        riv: gpd.GeoDataFrame,
        mapping: Dict[str, str] = {"id": "COMID"},
        output_mapping: Dict[str, str] = {"next_id": "NextDownCOMID"},
        dist_tol: float = 1e-6,
    ) -> gpd.GeoDataFrame:
        """
        Compute downstream connectivity (NextDown) for a river network using geometry.

        Each river segment is assigned a downstream segment whose start point matches
        (within a distance tolerance) the current segment's end point. Segments without
        a valid downstream connection are marked as terminal using -9999.

        Design principles
        -----------------
        - Mapping-based column access
        - Geometry-driven connectivity
        - Robust to LineString and MultiLineString geometries
        - Terminal-safe (-9999)
        - Side-effect free (input is not modified)

        Parameters
        ----------
        riv : geopandas.GeoDataFrame
            River network with line geometries.
        mapping : dict
            Dictionary defining the river segment ID column.
            Example: {'id': 'COMID'}
        output_mapping : dict
            Dictionary defining the downstream column name.
            Example: {'next_id': 'NextDownCOMID'}
        dist_tol : float
            Distance tolerance for endpoint matching (units of CRS).

        Returns
        -------
        geopandas.GeoDataFrame
            Copy of input GeoDataFrame with downstream column added.
        """

        id_col = mapping["id"]
        out_col = output_mapping["next_id"]

        if id_col not in riv.columns:
            raise ValueError(f"ID column '{id_col}' not found in GeoDataFrame")

        gdf = riv.copy()
        gdf[id_col] = gdf[id_col].astype(int)

        # --------------------------------------------------
        # Helper: extract start/end points
        # --------------------------------------------------
        def get_start_end(geom):
            if isinstance(geom, LineString):
                coords = geom.coords
            elif isinstance(geom, MultiLineString):
                coords = geom.geoms[0].coords
            else:
                raise TypeError("Geometry must be LineString or MultiLineString")
            return np.array(coords[0]), np.array(coords[-1])

        # --------------------------------------------------
        # Extract endpoints
        # --------------------------------------------------
        starts, ends, ids = [], [], []

        for _, row in gdf.iterrows():
            s, e = get_start_end(row.geometry)
            starts.append(s)
            ends.append(e)
            ids.append(row[id_col])

        starts = np.asarray(starts)
        ends = np.asarray(ends)
        ids = np.asarray(ids)

        # --------------------------------------------------
        # Build KD-tree on start points
        # --------------------------------------------------
        tree = cKDTree(starts)

        # --------------------------------------------------
        # Find downstream segment
        # --------------------------------------------------
        downstream_ids = []

        for i, end_pt in enumerate(ends):
            dist, idx = tree.query(end_pt, k=2)

            # Avoid self-match
            if idx[0] == i:
                candidate_idx = idx[1]
                candidate_dist = dist[1]
            else:
                candidate_idx = idx[0]
                candidate_dist = dist[0]

            if candidate_dist <= dist_tol:
                downstream_ids.append(int(ids[candidate_idx]))
            else:
                downstream_ids.append(-9999)

        # --------------------------------------------------
        # Assign output
        # --------------------------------------------------
        gdf[out_col] = downstream_ids

        return gdf


    @staticmethod
    def identify_non_channelized(
        riv,
        cat,
        riv_dict={
            "id": "COMID",
            "next_id": "NextDownCOMID",
            "length": "length",
            "geometry": "geometry",
            "islake": "islake"},
        cat_dict={"id": "COMID"}):
        """
        Identify non-channelized river segments in a river–catchment network.

        This function flags river segments that do not represent an explicit
        channelized flow path and should therefore be excluded from
        channel-based routing and accumulation operations. Non-channelized
        segments typically arise from lake merging, network clipping, or
        artificial segmentation where a river reach is fully submerged or
        suppressed.

        A river segment is classified as *non-channelized* if **all** of the
        following conditions are met:
        1. The river geometry is missing (e.g., fully submerged or removed).
        2. The river length is zero or undefined.
        3. The segment has no valid downstream river connection *or* drains
           directly into a lake.
        4. The segment has no immediate upstream river segments (i.e., it is
           not a junction or transit reach).

        The function does **not** modify network topology or downstream
        connectivity. It only assigns a binary classification flag
        (`non_channelized`) to both the river and catchment tables.

        Notes
        -----
        - Upstream connectivity is computed internally and used only for
          classification; it is not persisted.
        - Downstream connections to lakes are optionally considered if an
          `islake` column is provided.
        - The function assumes a one-to-one correspondence between rows in
          `riv` and `cat`, aligned by COMID.

        Parameters
        ----------
        riv : pandas.DataFrame or geopandas.GeoDataFrame
            River network attribute table containing river segment information,
            including downstream connectivity, length, and geometry.
        cat : pandas.DataFrame or geopandas.GeoDataFrame
            Catchment or subbasin attribute table corresponding one-to-one with
            the river segments.
        riv_dict : dict, optional
            Dictionary mapping river attribute roles to column names:
            - 'id' : river segment identifier
            - 'next_id' : downstream river segment identifier
            - 'length' : river segment length
            - 'geometry' : river geometry column
            - 'islake' : optional flag indicating lake segments
        cat_dict : dict, optional
            Dictionary mapping catchment attribute roles to column names:
            - 'id' : catchment identifier (must match river COMIDs)

        Returns
        -------
        tuple of pandas.DataFrame
            (riv, cat) with an added column:
            - `non_channelized` : integer flag (1 = non-channelized, 0 = channelized)

        Raises
        ------
        ValueError
            If `riv` and `cat` do not have the same length or if their COMID
            columns do not align after sorting.

        """
        # --------------------------
        # Resolve column names
        # --------------------------
        rid = riv_dict["id"]
        next_id_col = riv_dict["next_id"]
        length_col = riv_dict["length"]
        geom_col = riv_dict["geometry"]
        islake_col = riv_dict.get("islake", None)
        cid = cat_dict["id"]
        # --------------------------
        # Sort & align
        # --------------------------
        riv = riv.sort_values(rid).reset_index(drop=True)
        cat = cat.sort_values(cid).reset_index(drop=True)
        if len(riv) != len(cat):
            raise ValueError("riv and cat must have the same number of rows")
        if not (riv[rid].values == cat[cid].values).all():
            raise ValueError("riv and cat COMID columns are not identical after sorting")
        # --------------------------
        # Compute local upstream (TEMP ONLY)
        # --------------------------
        local_maxup = Utility.add_immediate_upstream(
            riv.copy(),
            mapping={'id': rid, 'next_id': next_id_col})
        # --------------------------
        # Core conditions
        # --------------------------
        geom_missing = riv[geom_col].isna()
        length_zero = riv[length_col].fillna(0) == 0
        down_invalid = riv[next_id_col].fillna(-9999) <= 0
        # --------------------------
        # Detect downstream-to-lake (optional)
        # --------------------------
        if islake_col is not None and islake_col in riv.columns:
            # map COMID -> islake
            islake_map = riv.set_index(rid)[islake_col]
            down_lake = riv[next_id_col].map(islake_map).fillna(0).astype(bool)
        else:
            down_lake = False  # scalar False, safely broadcast
        # --------------------------
        # Non-channelized definition
        # --------------------------
        non_channelized_mask = (
            geom_missing &
            length_zero &
            (down_invalid | down_lake) &
            (local_maxup["maxup"].fillna(0) == 0))
        # --------------------------
        # Assign flags ONLY (no topology mutation)
        # --------------------------
        riv = riv.copy()
        cat = cat.copy()
        riv["non_channelized"] = non_channelized_mask.astype(int)
        cat["non_channelized"] = non_channelized_mask.astype(int)
        # print(f"Non-channelized count: {riv['non_channelized'].sum()}")
        return riv, cat

    @staticmethod
    def FixHydroLAKESv1(lake_shp,
        lake_to_remove=None,
        merge_lakes=None):
        """
        Remove specified lakes and merge selected lakes in the HydroLAKES dataset.

        Parameters
        ----------
        lake_shp : GeoDataFrame
            HydroLAKES shapefile with lake attributes.
        lake_to_remove : list, optional
            List of Hylak_id to remove from the dataset.
        merge_lakes : dict, optional
            Dictionary specifying lakes to merge.
            Keys: new lake name
            Values: list of Hylak_id to merge

            Example:
            merge_lakes = {
                "Michigan+Huron": [6, 8],
                "OtherLake": [101, 102]
            }

        Returns
        -------
        GeoDataFrame
            Updated lake shapefile.
        """
        import geopandas as gpd

        # ---------------------------
        # Remove lakes if specified
        # ---------------------------
        if lake_to_remove:
            lake_shp = lake_shp[~lake_shp["Hylak_id"].isin(lake_to_remove)].reset_index(drop=True)

        # ---------------------------
        # Merge lakes if specified
        # ---------------------------
        if merge_lakes:
            for new_name, ids_to_merge in merge_lakes.items():
                # Select lakes to merge
                shp_slice = lake_shp[lake_shp["Hylak_id"].isin(ids_to_merge)].copy()
                if shp_slice.empty:
                    continue

                # Fix potential geometry issues with small buffer
                shp_slice.geometry = shp_slice.geometry.buffer(0.00001)

                # Dissolve into one geometry
                shp_dissolve = shp_slice.dissolve().reset_index(drop=True)

                # Update the first lake in the list with merged values
                target_idx = lake_shp[lake_shp["Hylak_id"] == ids_to_merge[-1]].index
                lake_shp.loc[target_idx, "geometry"] = shp_dissolve.geometry.iloc[0]
                lake_shp.loc[target_idx, "Lake_name"] = new_name
                lake_shp.loc[target_idx, "Lake_area"] = shp_slice["Lake_area"].sum()
                lake_shp.loc[target_idx, "Vol_total"] = shp_slice["Vol_total"].sum()
                lake_shp.loc[target_idx, "Shore_len"] = shp_slice["Shore_len"].sum()
                lake_shp.loc[target_idx, "Depth_avg"] = shp_slice["Depth_avg"].mean()
                lake_shp.loc[target_idx, "Dis_avg"] = shp_slice["Dis_avg"].mean()
                lake_shp.loc[target_idx, "Res_time"] = shp_slice["Res_time"].mean()
                lake_shp.loc[target_idx, "Country"] = shp_slice["Country"].iloc[0]  # take first value
                lake_shp.loc[target_idx, "Continent"] = shp_slice["Continent"].iloc[0]
                lake_shp.loc[target_idx, "Poly_src"] = shp_slice["Poly_src"].iloc[0]
                lake_shp.loc[target_idx, "Lake_type"] = 1
                lake_shp.loc[target_idx, "Grand_id"] = 0

                # Drop all other merged lakes except the last one
                drop_ids = [i for i in ids_to_merge if i != ids_to_merge[-1]]
                lake_shp = lake_shp[~lake_shp["Hylak_id"].isin(drop_ids)].reset_index(drop=True)

        return lake_shp

    @staticmethod
    def check_network_loops(
        riv: pd.DataFrame,
        mapping: Dict[str, str] = {
            "id": "COMID",
            "next_id": "NextDownCOMID",
        },
        verbose: bool = True,
    ) -> bool:
        """
        Detect directed topological loops in a river network.

        This function checks a river network for the presence of *directed
        cycles* (loops), where one or more river segments form a closed
        downstream path. Such loops violate the acyclic assumption required
        by most hydrologic routing, accumulation, and lake-resolution
        algorithms.

        The check is performed using a depth-first traversal of the directed
        river graph defined by downstream connectivity. Only valid internal
        connections are considered; terminal segments, clipped downstream
        references, and placeholder values (e.g., -9999) are safely ignored.

        The function is read-only and does not modify the input DataFrame.

        Design principles
        -----------------
        - Uses mapping-based column access for flexibility
        - Preserves original downstream identifiers in the input
        - Ignores terminal and non-existent downstream references
        - Detects only true directed cycles (not branching artifacts)
        - Side-effect free

        Parameters
        ----------
        riv : pandas.DataFrame
            River network attribute table containing at least a unique river
            segment identifier and a downstream connectivity column.
        mapping : dict, optional
            Dictionary mapping semantic roles to column names:
            - 'id' : unique river segment identifier
            - 'next_id' : downstream river segment identifier
        verbose : bool, optional
            If True, prints a human-readable report indicating whether loops
            were detected and lists the segments involved in each loop.

        Returns
        -------
        bool
            True if one or more directed loops are detected in the river
            network; False otherwise.

        Notes
        -----
        - This function detects *topological* loops only; it does not check
          for geometric self-intersections.
        - Multiple disjoint loops can be detected and reported.
        - The function is robust to clipped networks, lake suppression, and
          partially defined downstream connectivity.

        """
        id_col = mapping["id"]
        next_col = mapping["next_id"]
        # --------------------------------------------------
        # 1. Prepare clean topology
        # --------------------------------------------------
        df = riv[[id_col, next_col]].copy()
        df[id_col] = df[id_col].astype(int)
        df[next_col] = df[next_col].astype("Int64")
        comids = set(df[id_col])
        # Clean downstream (internal only)
        next_clean = df[next_col].replace(-9999, np.nan)
        next_clean.loc[~next_clean.isin(comids)] = np.nan
        next_map = dict(zip(df[id_col], next_clean))
        # --------------------------------------------------
        # 2. Loop detection
        # --------------------------------------------------
        visited_global = set()
        loops: List[List[int]] = []
        for start in next_map:
            if start in visited_global:
                continue
            visited_local = {}
            path = []
            current = start
            while pd.notna(current) and current in next_map:
                # ----- LOOP DETECTED -----
                if current in visited_local:
                    idx = visited_local[current]
                    loop = path[idx:]
                    loops.append(loop)
                    break
                visited_local[current] = len(path)
                path.append(current)
                current = next_map[current]
            visited_global.update(path)
        # --------------------------------------------------
        # 3. Reporting
        # --------------------------------------------------
        has_loop = len(loops) > 0
        if verbose:
            if has_loop:
                print("❌ Loop detected in network topology")
                for loop in loops:
                    print("  Loop:", " → ".join(map(str, loop)))
            else:
                print("✅ No loop detected in network topology")
        return has_loop


    @staticmethod
    def merit_read_file (riv_file: str,
                         cat_file: str,
                         cst_file: Optional [str] = None):
        """
        Read and preprocess MERIT-Hydro river network, catchments, and optional
        coastal hillslopes for a given Pfafstetter basin.

        This function loads MERIT-Hydro shapefiles using Pfaf-based filename
        templates, harmonizes river–catchment topology, fixes invalid downstream
        references, optionally incorporates coastal hillslopes, and identifies
        non-channelized subbasins following the river–lake network rules.

        The input file paths must be provided as templates containing a single
        wildcard character ('*'), which is replaced internally by the supplied
        Pfafstetter code.

        Expected file naming convention (MERIT-Hydro bug-fix release):
            riv_pfaf_*_MERIT_Hydro_v07_Basins_v01_bugfix1.shp
            cat_pfaf_*_MERIT_Hydro_v07_Basins_v01_bugfix1.shp
            hillslope_*_clean.shp

        For example, if pfaf = "43", the following files are read:
            riv_pfaf_43_MERIT_Hydro_v07_Basins_v01_bugfix1.shp
            cat_pfaf_43_MERIT_Hydro_v07_Basins_v01_bugfix1.shp
            hillslope_43_clean.shp

        River and catchment datasets must contain identical COMID values. If
        catchments exist without corresponding river segments, empty river
        records are automatically created to preserve network consistency.

        Invalid or clipped downstream references (NextDownID ≤ 0 or not present
        in the network) are reset to -9999. Coastal hillslopes, when provided, are
        appended to the catchment dataset with unique COMIDs and computed areas.

        Non-channelized subbasins are identified based on missing geometry,
        zero-length river reaches, lack of upstream connections, and downstream
        termination into lakes or sinks.

        All datasets are returned in EPSG:4326.

        Data source:
            MERIT-Hydro river network and basin products can be downloaded from:
            https://www.reachhydro.org/home/params/merit-basins

        Parameters
        ----------
        pfaf : str
            Pfafstetter basin identifier used to resolve input file templates.
        riv_file_template : str
            File path template for river network shapefiles containing '*'.
        cat_file_template : str
            File path template for catchment shapefiles containing '*'.
        cst_file_template : str, optional
            File path template for coastal hillslope shapefiles containing '*'.
        identify_non_channelized : callable
            Function used to classify non-channelized subbasins.

        Returns
        -------
        riv : geopandas.GeoDataFrame
            Processed river network with corrected topology and flags.
        cat : geopandas.GeoDataFrame
            Catchments (and optional coastal hillslopes) aligned with the river
            network.

        """
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
        riv = gpd.read_file(os.path.join(riv_file))
        cat = gpd.read_file(os.path.join(cat_file))
        # check the length of riv and cat
        if len(riv) != len(cat):
            raise error
        if not cst_file is None:
            cst = gpd.read_file(os.path.join(cst_file))
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
        # add the non_channelized
        riv, cat =Utility.identify_non_channelized(riv, cat,
            riv_dict={"id": "COMID",
            "next_id": "NextDownID",
            "length": "lengthkm",
            "geometry": "geometry"},
            cat_dict={"id": "COMID"})
        # return
        return riv, cat

    @staticmethod
    def hdma_read_file_processed(
            riv_file: str,
            cat_file: str):
        def fix_DownID(riv: pd.DataFrame) -> pd.DataFrame:
            riv = riv.copy()
            riv["seg_id"] = riv["seg_id"].astype(int)
            riv["Tosegment"] = pd.to_numeric(
                riv["Tosegment"], errors="coerce"
            ).astype("Int64")
            valid_comids = set(riv["seg_id"])
            invalid = (
                riv["Tosegment"].notna()
                & (
                    (riv["Tosegment"] <= 0)
                    | ~riv["Tosegment"].isin(valid_comids)
                )
            )
            riv.loc[invalid, "Tosegment"] = -9999
            return riv
        # read files cat, riv, cst
        riv = gpd.read_file(os.path.join(riv_file))
        cat = gpd.read_file(os.path.join(cat_file))
        # sync the riv and cat
        riv_ids = set(riv["seg_id"].dropna())
        cat_ids = set(cat["hruid"].dropna())
        shared_ids = riv_ids.intersection(cat_ids)
        riv = riv[riv["seg_id"].isin(shared_ids)].reset_index(drop=True)
        cat = cat[cat["hruid"].isin(cat_ids)].reset_index(drop=True)
        missing_riv_ids = cat_ids - riv_ids
        if missing_riv_ids:
            new_riv_rows = []
            for _, row in cat[cat["hruid"].isin(missing_riv_ids)].iterrows():
                new_riv_rows.append({
                    "seg_id": row["hruid"],
                    "Tosegment": -9999,
                    "Length": 0.0,
                    "geometry": None
                })
            new_riv = gpd.GeoDataFrame(
                new_riv_rows,
                geometry="geometry",
                crs=riv.crs
            )
            riv = pd.concat([riv, new_riv], ignore_index=True)
        # ------------------------------------------------------------------
        # riv and cat are now synchronized
        # ------------------------------------------------------------------
        # sort seg_id
        riv.sort_values(by='seg_id', axis='index', inplace=True)
        riv.reset_index(drop=True, inplace=True)
        # sort hruid
        cat.sort_values(by='hruid', axis='index', inplace=True)
        cat.reset_index(drop=True, inplace=True)
        # set the projection
        riv.set_crs(epsg=4326, inplace=True, allow_override=True)
        cat.set_crs(epsg=4326, inplace=True, allow_override=True)
        # fix network topology
        riv = fix_DownID(riv)
        # add the non_channelized
        riv, cat = Utility.identify_non_channelized(riv, cat,
            riv_dict={"id": "seg_id",
            "next_id": "Tosegment",
            "length": "Length",
            "geometry": "geometry"},
            cat_dict={"id": "hruid"})
        # return
        return riv, cat

    @staticmethod
    def hdma_read_file(
            riv_file: str,
            cat_file: str):
        def fix_DownID(riv: pd.DataFrame) -> pd.DataFrame:
            riv = riv.copy()
            riv["COMID"] = riv["COMID"].astype(int)
            riv["NextDownCOMID"] = pd.to_numeric(
                riv["NextDownCOMID"], errors="coerce"
            ).astype("Int64")
            valid_comids = set(riv["COMID"])
            invalid = (
                riv["NextDownCOMID"].notna()
                & (
                    (riv["NextDownCOMID"] <= 0)
                    | ~riv["NextDownCOMID"].isin(valid_comids)
                )
            )
            riv.loc[invalid, "NextDownCOMID"] = -9999
            return riv
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
            new_rows["NextDownCOMID"] = 0
            new_rows["length"] = 0
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
        # read files cat, riv, cst
        riv = gpd.read_file(os.path.join(riv_file))
        cat = gpd.read_file(os.path.join(cat_file))
        # fix the downstream for riv and add compute unit area
        riv["COMID"] = riv["PFAF_CODE"].astype(int)
        riv["uparea"] = riv["flow_acc"].astype(float)
        riv = Utility.compute_next_downstream(riv, mapping = {"id": "COMID"}, output_mapping = {"next_id": "NextDownCOMID"})
        riv["length"] = riv.set_crs(4326, allow_override=True).to_crs(6933).length / 1000
        # cat unitarea calculation
        cat["COMID"] = cat["PFAF_CODE"].astype(int)
        cat["unitarea"] = cat.set_crs(4326, allow_override=True).to_crs(6933).area / 1000000
        # sync the riv and cat

        # riv_ids = set(riv["COMID"].dropna())
        # cat_ids = set(cat["COMID"].dropna())
        # shared_ids = riv_ids.intersection(cat_ids)
        # riv = riv[riv["COMID"].isin(shared_ids)].reset_index(drop=True)
        # cat = cat[cat["COMID"].isin(cat_ids)].reset_index(drop=True)
        # missing_riv_ids = cat_ids - riv_ids
        # if missing_riv_ids:
        #     new_riv_rows = []
        #     for _, row in cat[cat["COMID"].isin(missing_riv_ids)].iterrows():
        #         new_riv_rows.append({
        #             "COMID": row["COMID"],
        #             "NextDownCOMID": -9999,
        #             "length": 0.0,
        #             "geometry": None
        #         })
        #     new_riv = gpd.GeoDataFrame(
        #         new_riv_rows,
        #         geometry="geometry",
        #         crs=riv.crs
        #     )
        #     riv = pd.concat([riv, new_riv], ignore_index=True)
        # ------------------------------------------------------------------
        # riv and cat are now synchronized
        # ------------------------------------------------------------------
        # sort seg_id
        riv.sort_values(by='COMID', axis='index', inplace=True)
        riv.reset_index(drop=True, inplace=True)
        # sort hruid
        cat.sort_values(by='COMID', axis='index', inplace=True)
        cat.reset_index(drop=True, inplace=True)
        # set the projection
        riv.set_crs(epsg=4326, inplace=True, allow_override=True)
        cat.set_crs(epsg=4326, inplace=True, allow_override=True)
        # fix the network topology
        riv = add_cat_only_comids_to_riv(riv,cat)
        # fix network topology
        riv = fix_DownID(riv)
        # add the non_channelized
        riv, cat = Utility.identify_non_channelized(riv, cat,
            riv_dict={"id": "COMID",
            "next_id": "NextDownCOMID",
            "length": "length",
            "geometry": "geometry"},
            cat_dict={"id": "COMID"})
        # Sort: valid geometry first, None/empty last
        riv = riv.assign(
            _geom_missing=riv.geometry.isna() | riv.geometry.is_empty
        ).sort_values(
            by="_geom_missing",
            ascending=True
        ).drop(columns="_geom_missing").reset_index(drop=True)
        cat = (
            cat.set_index("COMID")
               .loc[riv["COMID"]]
               .reset_index()
        )
        riv.reset_index(drop=True, inplace=True)
        cat.reset_index(drop=True, inplace=True)
        # return
        return riv, cat