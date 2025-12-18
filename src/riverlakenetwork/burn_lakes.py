import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from .input_loader import InputLoader
from .input_checker import InputChecker
from .resolvable_lake_identifier import ResolvableLakes
from .network_correction import NetworkTopologyCorrection
from .output_checker import OutputChecker
from .utility import Utility


class BurnLakes:

    def __init__(self,
        config: dict,
        lake_subset_margin: float=2.00,
        network_clean_up_flag: bool=True,
        force_one_lake_per_riv_seg_flag: bool=False):

        self.config = config

        # ------------------
        # 1. Load inputs
        # ------------------
        t0 = datetime.now()
        print("=======================================================================")
        print("=== Input loader started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        loader = InputLoader(config)
        # Keep originals (read-only by convention)
        self.cat_org  = loader.cat
        self.riv_org  = loader.riv
        self.lake_org = loader.lake
        self.cat_dict = loader.cat_dict
        self.riv_dict = loader.riv_dict
        self.lake_dict = loader.lake_dict
        # Working copies (single deep copy)
        self.cat  = self.cat_org.copy()
        self.riv  = self.riv_org.copy()
        self.lake = self.lake_org.copy()
        del loader
        t1 = datetime.now()
        print("=== Input loader finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Input loader took      :", (t1 - t0), " ===========================")
        print("=======================================================================")

        # ------------------
        # 2. Validate inputs
        # ------------------
        t0 = datetime.now()
        print("========================================================================")
        print("=== Input checker started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        #checker = InputChecker(loaded_data=loader)
        checker = InputChecker(riv=self.riv, riv_dict=self.riv_dict,
                               cat=self.cat, cat_dict=self.cat_dict,
                               lake=self.lake, lake_dict=self.lake_dict)
        self.cat, self.riv, self.lake = checker.cat, checker.riv, checker.lake
        self.cat_org, self.riv_org, self.lake_org = checker.cat, checker.riv, checker.lake
        del checker
        t1 = datetime.now()
        print("=== Input checker finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Input checker took      :", (t1 - t0), " ===========================")
        print("========================================================================")

        # ------------------
        # 3. Identify resolvable lakes
        # ------------------
        t0 = datetime.now()
        print("==========================================================================")
        print("=== Resolving lakes started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        resolver = ResolvableLakes(
            cat=self.cat,
            riv=self.riv,
            lake=self.lake,
            lake_subset_margin=lake_subset_margin,
            force_one_lake_per_riv_seg_flag=force_one_lake_per_riv_seg_flag
        )
        self.lake = resolver.lake_resolvable
        del resolver
        t1 = datetime.now()
        print("=== Resolving lakes finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Resolving lakes took      :", (t1 - t0), " ===========================")
        print("==========================================================================")

        # ------------------
        # 4. Correct network topology
        # ------------------
        t0 = datetime.now()
        print("=============================================================================")
        print("=== Network correction started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        corrector = NetworkTopologyCorrection(
            cat=self.cat,
            riv=self.riv,
            lake=self.lake,
            network_clean_up_flag=network_clean_up_flag
        )
        self.cat, self.riv, self.lake = corrector.cat_corrected, corrector.riv_corrected, corrector.lake_corrected
        del corrector
        t1 = datetime.now()
        print("=== Network correction finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Network correction took      :", (t1 - t0), " ===========================")
        print("=============================================================================")

        # ------------------
        # 5. Check network topology
        # ------------------
        t0 = datetime.now()
        print("=============================================================================")
        print("=== Output checker started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " =======")
        OutputChecker(
            riv=self.riv,
            riv_org=self.riv_org,
            lake=self.lake
        )
        t1 = datetime.now()
        print("=== Output checker finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Output checker took      :", (t1 - t0), " ===========================")
        print("=========================================================================")

