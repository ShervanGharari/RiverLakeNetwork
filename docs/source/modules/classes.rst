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
Dictionary defining input datasets and column mappings.

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

Components:

riv
River network (GeoDataFrame)

riv_dict
Mapping of river attributes:


- COMID: unique river segment ID  
- NextDownCOMID: downstream segment ID  
- length: segment length  
- uparea: upstream contributing area  

cat
Catchment polygons (GeoDataFrame)

cat_dict
Mapping of catchment attributes:


- COMID: catchment ID  
- unitarea: catchment area  


lake
Lake polygons (GeoDataFrame)

lake_dict
Mapping of lake attributes:


- LakeCOMID: lake identifier  
- unitarea: lake surface area  


SubsetLakeBuffer
Buffer distance used for spatial subsetting of lakes (in coordinate units, e.g., degrees).

EnforceOneLakePerSegment
If True, enforces that each river segment is associated with at most one lake.

SingleSegmentProcessing
Enables identification and processing of single-segment lakes.

SingleSegmentIdPosition
Optional specification of placement direction for specific lakes.
Accepts list, set, or dictionary mapping lake IDs to "up" or "down".

SingleSegmentRestrictToIdPosition
If True, processing is restricted to lakes specified in SingleSegmentIdPosition.

SingleSegmentExcludeFirstOrder
If True, excludes first-order streams when identifying single-segment lakes.

SingleSegmentGlobalPosition
Default placement direction for single-segment lakes ("down" or "up").

Attributes
~~~~~~~~~~

cat
  Processed catchment dataset (GeoDataFrame)

riv
  Processed river network (GeoDataFrame)

lake
  Final resolved lake dataset (GeoDataFrame)

cat_org
  Original catchment dataset after validation

riv_org
  Original river dataset after validation

lake_org
  Original lake dataset after validation

single_segment_lake
  Identified single-segment lakes (if enabled)

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
