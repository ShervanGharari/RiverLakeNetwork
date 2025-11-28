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

class Utility:

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