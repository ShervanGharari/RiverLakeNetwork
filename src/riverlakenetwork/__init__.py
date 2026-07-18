from importlib.metadata import version

__version__ = version("riverlakenetwork")

# Import core classes and functions
from .input_loader                           import InputLoader
from .input_checker                          import InputChecker
from .multi_segment_lake_identifier          import MultiSegmentLakeIdentifier
from .network_correction_multi_segment_lake  import NetworkTopologyCorrectionMultiSegmentLakes
from .single_segment_lake_identifier         import SingleSegmentLakesIdentifier
from .network_correction_single_segment_lake import NetworkTopologyCorrectionSingleSegmentLakes
from .output_checker                         import OutputChecker
from .utility                                import Utility
from .burn_lakes                             import BurnLakes

# Define what is available when users do: `from riverlakenetwork import *`
__all__ = [
    "InputLoader",
    "InputChecker",
    "MultiSegmentLakeIdentifier",
    "NetworkTopologyCorrectionMultiSegmentLakes",
    "SingleSegmentLakesIdentifier",
    "NetworkTopologyCorrectionSingleSegmentLakes",
    "BurnLakes",
    "OutputChecker",
    "Utility",
    "BurnLakes",
]