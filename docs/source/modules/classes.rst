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
---------

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
---------------------

``riv``
    River network represented as a GeoDataFrame.

``riv_dict``
    Dictionary defining the mapping between river attributes and their corresponding columns:

    - ``COMID``: Unique identifier of each river segment.
    - ``NextDownCOMID``: Identifier of the downstream river segment.
    - ``length``: Length of the river segment.
    - ``uparea``: Upstream contributing drainage area associated with the river segment.

``cat``
    Catchment polygons represented as a GeoDataFrame.

``cat_dict``
    Dictionary defining the mapping between catchment attributes and their corresponding columns:

    - ``COMID``: Unique identifier of each catchment.
    - ``unitarea``: Catchment area.

``lake``
    Lake and reservoir polygons represented as a GeoDataFrame.

``lake_dict``
    Dictionary defining the mapping between lake attributes and their corresponding columns:

    - ``LakeCOMID``: Unique identifier of each lake or reservoir.
    - ``unitarea``: Surface area of the lake or reservoir.


Additional Processing Parameters
--------------------------------

The following parameters control the lake identification and network correction procedures. These parameters are provided separately from ``InputData``.

``SubsetLakeBuffer``
    Buffer distance used for spatial pre-selection of lakes and reservoirs. The unit corresponds to the coordinate reference system of the input spatial data (e.g., degrees for geographic coordinates).

``EnforceOneLakePerSegment``
    Logical flag controlling whether each river segment is restricted to a maximum of one associated lake. When enabled, only one lake is retained for each river segment.

``SingleSegmentProcessing``
    Logical flag enabling the identification and integration of lakes associated with a single river segment.

``SingleSegmentIdPosition``
    Optional user-defined specification of the placement direction for individual single-segment lakes. The input can be provided as:

    - A ``list`` or ``set`` of lake IDs, where the same placement direction is applied to all specified lakes.
    - A ``dictionary`` mapping individual lake IDs to either ``"up"`` or ``"down"`` placement directions.

``SingleSegmentRestrictToIdPosition``
    Logical flag controlling whether single-segment lake processing is restricted only to lakes specified in ``SingleSegmentIdPosition``.

``SingleSegmentExcludeFirstOrder``
    Logical flag controlling whether first-order river segments are excluded during single-segment lake identification.

``SingleSegmentGlobalPosition``
    Default placement direction for single-segment lakes when no lake-specific direction is provided. Accepted values are ``"up"`` and ``"down"``.


Notes
~~~~~

- The full workflow is executed automatically during initialization.  
- Large datasets may require significant computation time.  
- Single-segment lake processing is optional and controlled via flags.  
- Lake placement rules are normalized internally using utility functions.

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
