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

class Utility:

    def compute_uparea(
            riv: pd.DataFrame,
            comid_col: str = "COMID",
            next_col: str = "NextDownCOMID",
            area_col: str = "unitarea",
            out_col: str = "uparea"):
        """
        Compute upstream contributing area ("uparea") for a river network while
        safely handling terminal segments and invalid downstream identifiers.

        Notes on network structure and special cases
        -------------------------------------------
        In many hydrological datasets, the downstream identifier (`NextDownCOMID`)
        can contain special values that indicate the end of the river network or
        a topological break. For example:
            - -9999   → indicates the segment is an outlet (no downstream)
            - NaN     → missing or undefined downstream COMID
            - values not present in the list of COMIDs → caused by clipping,
              lake suppression, topology repair, or incomplete river networks

        The original topological traversal algorithm assumes that every
        `NextDownCOMID` is a valid node in the river network. If special values
        such as -9999 are treated as real COMIDs, the algorithm attempts to
        accumulate upstream area into a non-existent node, resulting in a
        KeyError such as:

            KeyError: -9999.0

        To avoid this, the function first *sanitizes* the downstream column by:
            1. Converting -9999 to NaN
            2. Converting any downstream ID that does not exist in the COMID list
               to NaN as well
            3. Treating NaN in the downstream column as a terminal outlet

        After cleaning the topology, the algorithm performs a standard
        topological traversal (from headwaters to outlet), accumulating upstream
        contributing area along the valid downstream connections only.

        This ensures:
            - No KeyErrors during traversal
            - Proper handling of outlet segments
            - Robust behavior even when the network has missing or pruned segments
            - Correct propagation of contributing area through the river graph

        Returns
        -------
        pd.DataFrame
            A copy of the input with a new column containing the computed upstream
            contributing area for every COMID.
        """
        df = riv.copy()
        # Ensure numeric area
        df[area_col] = df[area_col].fillna(0).astype(float)
        # COMIDs in network
        comids = set(df[comid_col].tolist())
        # Normalize terminal markers
        df[next_col] = df[next_col].replace(-9999, np.nan)
        # Replace downstream COMIDs not part of this network → treat as terminal
        df.loc[~df[next_col].isin(comids), next_col] = np.nan
        # Build lookup dictionaries
        nextdown = df.set_index(comid_col)[next_col].to_dict()
        uparea = df.set_index(comid_col)[area_col].to_dict()
        # Compute indegree
        indegree = defaultdict(int)
        for u, d in nextdown.items():
            if d in comids:   # only count valid downstreams
                indegree[d] += 1
        # Headwaters = no upstream tributaries
        queue = deque([cid for cid in comids if indegree.get(cid, 0) == 0])
        visited = set()
        # Propagate areas
        while queue:
            u = queue.popleft()
            visited.add(u)
            d = nextdown.get(u, None)
            # Terminal → stop here
            if d is None or pd.isna(d) or d not in comids:
                continue
            # Add upstream contribution
            uparea[d] += uparea[u]
            # Decrease indegree
            indegree[d] -= 1
            if indegree[d] == 0:
                queue.append(d)
        # Assign output
        df[out_col] = df[comid_col].map(uparea)
        return df

    def add_immediate_upstream (df,
                                mapping = {'id':'LINKNO','next_id':'DSLINKNO'}):

        # this function add immediate segment of upstream for a river network if not provided
        # it first convert the df into a networkx derected graph, finds the sucessores for
        # river segments, provide the maximume existing upstream segments in column called maxup
        # and the values in up1, up2, up3, etc

        # get the name of ID and downID
        downID = mapping.get('next_id')
        ID = mapping.get('id')

        # Create a directed graph
        G = nx.DiGraph()

        # Add edges from the DataFrame (reversing the direction)
        for _, row in df.iterrows():
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