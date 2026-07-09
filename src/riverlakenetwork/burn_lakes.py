import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import numpy as np
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional, Union, List, Set, Dict
from .input_loader import InputLoader
from .input_checker import InputChecker
from .multi_segment_lake_identifier import MultiSegmentLakeIdentifier
from .network_correction_multi_segment_lake import NetworkTopologyCorrectionMultiSegmentLakes
from .single_segment_lake_identifier import SingleSegmentLakesIdentifier
from .network_correction_single_segment_lake import NetworkTopologyCorrectionSingleSegmentLakes
from .output_checker import OutputChecker
from .utility import Utility


class BurnLakes:

    def __init__(
        self,
        InputData: dict,
        SubsetLakeBuffer: float = 2.00, # degrees buffer, can be other units
        EnforceOneLakePerSegment: bool = False,
        SingleSegmentProcessing: bool = False,
        SingleSegmentIdPosition: Optional[Union[List[int], Set[int], Dict[int, str]]] = None,
        SingleSegmentRestrictToIdPosition: bool = True,
        SingleSegmentExcludeFirstOrder: bool = True,
        SingleSegmentGlobalPosition: str = "down"  # "down" or "up"
    ):

        # =========================================================
        # 0. Store inputs
        # =========================================================
        self.InputData = InputData
        self.SubsetLakeBuffer = SubsetLakeBuffer
        self.EnforceOneLakePerSegment = EnforceOneLakePerSegment
        self.SingleSegmentProcessing = SingleSegmentProcessing
        self.SingleSegmentIdPosition = SingleSegmentIdPosition
        self.SingleSegmentRestrictToIdPosition = SingleSegmentRestrictToIdPosition
        self.SingleSegmentExcludeFirstOrder = SingleSegmentExcludeFirstOrder
        self.SingleSegmentGlobalPosition = SingleSegmentGlobalPosition

        # =========================================================
        # Normalize Single Segment IDs
        # =========================================================
        if self.SingleSegmentIdPosition is not None:
            self.SingleSegmentIdPosition = Utility.normalize_single_segment_lakes(
                single_segment_lakesID_position=self.SingleSegmentIdPosition,
                single_segment_lakes_global_position=self.SingleSegmentGlobalPosition
            )

        # =========================================================
        # 1. Load inputs
        # =========================================================
        t0 = datetime.now()
        print("=======================================================================")
        print("=== Input loader started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

        loader = InputLoader(self.InputData)

        self.cat_org = loader.cat
        self.riv_org = loader.riv
        self.lake_org = loader.lake

        self.cat_dict = loader.cat_dict
        self.riv_dict = loader.riv_dict
        self.lake_dict = loader.lake_dict

        self.cat = self.cat_org.copy()
        self.riv = self.riv_org.copy()
        self.lake = self.lake_org.copy()

        del loader

        t1 = datetime.now()
        print("=== Input loader finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Input loader took      :", (t1 - t0), " ===========================")
        print("=======================================================================")

        # =========================================================
        # 2. Validate inputs
        # =========================================================
        t0 = datetime.now()
        print("========================================================================")
        print("=== Input checker started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

        checker = InputChecker(
            riv=self.riv,
            riv_dict=self.riv_dict,
            cat=self.cat,
            cat_dict=self.cat_dict,
            lake=self.lake,
            lake_dict=self.lake_dict
        )

        self.cat = checker.cat
        self.riv = checker.riv
        self.lake = checker.lake

        self.cat_org = checker.cat
        self.riv_org = checker.riv
        self.lake_org = checker.lake

        del checker

        t1 = datetime.now()
        print("=== Input checker finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Input checker took      :", (t1 - t0), " ===========================")
        print("========================================================================")

        # =========================================================
        # 3. Identifying multi-segment lakes
        # =========================================================
        t0 = datetime.now()
        print("==========================================================================================")
        print("=== Identifying multi-segment lakes started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

        resolver = MultiSegmentLakeIdentifier(
            cat=self.cat,
            riv=self.riv,
            lake=self.lake,
            SubsetLakeBuffer=self.SubsetLakeBuffer,
            EnforceOneLakePerSegment=self.EnforceOneLakePerSegment
        )

        self.lake = resolver.lake_resolvable

        del resolver

        t1 = datetime.now()
        print("=== Identifying multi-segment lakes finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Identifying multi-segment lakes took      :", (t1 - t0), " ===========================")
        print("==========================================================================================")

        # =========================================================
        # 4. Network correction for multi-segment lakes
        # =========================================================
        t0 = datetime.now()
        print("==============================================================================================================")
        print("=== Network topology correction for multi-segment lakes started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

        corrector = NetworkTopologyCorrectionMultiSegmentLakes(
            cat=self.cat,
            riv=self.riv,
            lake=self.lake
        )

        self.cat = corrector.cat_corrected
        self.riv = corrector.riv_corrected
        self.lake = corrector.lake_corrected

        del corrector

        t1 = datetime.now()
        print("=== Network topology correction for multi-segment lakes finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Network topoloty correction for multi-segment lakes took      :", (t1 - t0), " ===========================")
        print("==============================================================================================================")

        # =========================================================
        # 5. Identifying single-segment lakes
        # =========================================================
        if self.SingleSegmentProcessing:

            t0 = datetime.now()
            print("===========================================================================================")
            print("=== Identifying single-segment lakes started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

            unresolved_lakes = self.lake_org[
                ~self.lake_org["LakeCOMID"].isin(set(self.lake["LakeCOMID"].values))
            ]

            SingleSegment = SingleSegmentLakesIdentifier(
                cat=self.cat,
                riv=self.riv,
                lake=unresolved_lakes,
                SubsetLakeBuffer=self.SubsetLakeBuffer,
                EnforceOneLakePerSegment=self.EnforceOneLakePerSegment,
                SingleSegmentIdPosition=self.SingleSegmentIdPosition,
                SingleSegmentRestrictToIdPosition=self.SingleSegmentRestrictToIdPosition,
                SingleSegmentExcludeFirstOrder=self.SingleSegmentExcludeFirstOrder,
                SingleSegmentGlobalPosition=self.SingleSegmentGlobalPosition
            )

            self.single_segment_lake = SingleSegment.single_segment_lake

            del SingleSegment

            t1 = datetime.now()
            print("=== Identifying single-segment lakes finished at :", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
            print("=== Identifying single-segment lakes took        :", (t1 - t0), " ==========================")
            print("============================================================================================")

        # =========================================================
        # 6. Network correction for single-segment lakes
        # =========================================================
        if (
            getattr(self, "single_segment_lake", None) is not None
            and self.SingleSegmentProcessing
            and not self.single_segment_lake.empty
        ):

            t0 = datetime.now()
            print("===============================================================================================================")
            print("=== Network topology correction for single-segment lakes started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

            corrector = NetworkTopologyCorrectionSingleSegmentLakes(
                singlelake=self.single_segment_lake,
                cat=self.cat,
                lake=self.lake,
                riv=self.riv
            )

            self.cat = corrector.cat_corrected
            self.riv = corrector.riv_corrected
            self.lake = corrector.lake_corrected

            del corrector

            t1 = datetime.now()
            print("=== Network topology correction for single-segment lakes finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
            print("=== Network topology correction for single-segment lakes took      :", (t1 - t0), " ===========================")
            print("===============================================================================================================")

        # =========================================================
        # 7. Output check
        # =========================================================
        t0 = datetime.now()
        print("=============================================================================")
        print("=== Output checker started at :", t0.strftime("%Y-%m-%d %H:%M:%S"), " ===")

        OutputChecker(
            riv=self.riv,
            riv_org=self.riv_org,
            lake=self.lake
        )

        t1 = datetime.now()
        print("=== Output checker finished at:", t1.strftime("%Y-%m-%d %H:%M:%S"), " ===")
        print("=== Output checker took      :", (t1 - t0), " ===========================")
        print("=============================================================================")