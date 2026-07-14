Classes
=======

BurnLakes
---------

.. class:: BurnLakes(InputData, SubsetLakeBuffer=2.0, EnforceOneLakePerSegment=False, SingleSegmentProcessing=False, SingleSegmentIdPosition=None, SingleSegmentRestrictToIdPosition=True, SingleSegmentExcludeFirstOrder=True, SingleSegmentGlobalPosition="down")

Main workflow class for processing, resolving, and integrating lakes into a river network.

This class executes the full processing pipeline during initialization.

Workflow
~~~~~~~~

1. Load input datasets (catchments, rivers, lakes)  
2. Validate inputs  
3. Identify resolvable lakes  
4. Correct river network topology  
5. Identify single-segment lakes (optional)  
6. Apply topology corrections for single-segment lakes (optional)  
7. Validate outputs  

Parameters
~~~~~~~~~~

InputData
^^^^^^^^^

``InputData`` is a dictionary defining the input datasets and their corresponding column mappings. It contains the river network, catchment, and lake datasets required for lake integration.

The expected structure is:

::

  InputData = {
      "riv": riv,
      "riv_dict": {
          "COMID": {"col": "link_id"},
          "NextDownCOMID": {"col": "ds_link_id"},
          "length": {"col": "length"},
          "uparea": {"col": "uparea", "unit": "km2"}
      },
      "cat": cat,
      "cat_dict": {
          "COMID": {"col": "link_id"},
          "unitarea": {"col": "unitarea", "unit": "km2"}
      },
      "lake": lake,
      "lake_dict": {
          "LakeCOMID": {"col": "Hylak_id"},
          "unitarea": {"col": "Lake_area", "unit": "km2"}
      }
  }


InputData Components
""""""""""""""""""""

``riv``
    River network represented as a GeoDataFrame or a path to the input file.

``riv_dict``
    Dictionary defining the mapping between river attributes and their corresponding columns:

    - ``COMID``: Unique identifier of each river segment.
    - ``NextDownCOMID``: Identifier of the downstream river segment.
    - ``length``: Length of the river segment.
    - ``uparea``: Upstream contributing drainage area associated with the river segment.

``cat``
    Catchment polygons represented as a GeoDataFrame or a path to the input file.

``cat_dict``
    Dictionary defining the mapping between catchment attributes and their corresponding columns:

    - ``COMID``: Unique identifier of each catchment.
    - ``unitarea``: Catchment area.

``lake``
    Lake and reservoir polygons represented as a GeoDataFrame or a path to the input file.

``lake_dict``
    Dictionary defining the mapping between lake attributes and their corresponding columns:

    - ``LakeCOMID``: Unique identifier of each lake or reservoir.
    - ``unitarea``: Surface area of the lake or reservoir.


Additional Processing Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following parameters control the lake identification and river network correction procedures. These parameters are provided separately from ``InputData``.

``SubsetLakeBuffer``
    Buffer distance used for the spatial pre-selection of lakes and reservoirs based on the spatial extent of the input subbasins (``cat``) or river network. The unit corresponds to the coordinate reference system of the input spatial data (e.g., degrees for geographic coordinates). Default value is ``2.00``.

``EnforceOneLakePerSegment``
    Logical flag controlling whether each river segment is restricted to a maximum of one associated lake. When enabled, only one lake is retained for each river segment. If multiple lakes intersect the same river segment, the lake with the largest surface area is automatically retained.

    Users can also remove undesired lakes and reservoirs before initiating the workflow or iteratively after reviewing the identified lakes to ensure that the intended lakes are resolved. Default is ``False``.

``SingleSegmentProcessing``
    Logical flag enabling the identification and integration of lakes associated with a single river segment. Default is ``False``.

``SingleSegmentIdPosition``
    Optional user-defined specification of the placement direction for individual single-segment lakes. The input can be provided as:

    - A ``list`` or ``set`` of lake IDs, where the same placement direction is applied to all specified lakes.
    - A ``dictionary`` mapping individual lake IDs to either ``"up"`` or ``"down"`` placement directions.

    Example::

        {234: "up", 345: "down"}

``SingleSegmentRestrictToIdPosition``
    Logical flag controlling whether single-segment lake processing is restricted only to lakes specified in ``SingleSegmentIdPosition``.

    For example, if ``SingleSegmentIdPosition`` is defined as ``{234: "up", 345: "down"}``, enabling this option restricts single-segment lake processing only to lakes 234 and 345. Default is ``False``.

``SingleSegmentExcludeFirstOrder``
    Logical flag controlling whether first-order river segments are excluded during single-segment lake identification.

    When enabled, single-segment lakes assigned upstream of first-order river segments (either through ``SingleSegmentGlobalPosition`` or ``SingleSegmentIdPosition``) are excluded. This ensures that all resolved lakes have at least one river segment contributing inflow. Default is ``True``.

``SingleSegmentGlobalPosition``
    Default placement direction for single-segment lakes when no lake-specific direction is provided. Accepted values are ``"up"`` and ``"down"``. Default is ``"down"``.


Notes
~~~~~

- The upstream contributing area (``uparea``) attribute in ``riv`` is required for the workflow. If it is not available, it can be calculated from the river network topology and catchment unit areas using the RiverLakeNetwork utility function:

  ::

      from riverlakenetwork import Utility
      
      rivers = Utility.compute_uparea(
          rivers,
          mapping={
              "id": "COMID",
              "next_id": "NextDownID",
              "unitarea": "AREA",
          },
          out_col="UPAREA"
      )

- The area units of the subbasins (``cat``) and lakes (``lake``) must be consistent. If different units are used, discrepancies may occur in the calculated upstream contributing areas after lake integration. These differences are reported in the final ``riv`` output through the columns ``difference_uparea``, ``difference_percent``, and ``difference_fraction``. Users can use these attributes to evaluate the consistency of the corrected river network compared to the original network.

Example
~~~~~~~

::

    from riverlakenetwork import BurnLakes

    model = BurnLakes(
        InputData=InputData,
        SingleSegmentProcessing=True
    )

    riv = model.riv
    lake = model.lake
