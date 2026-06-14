Classes
=======

BurnLakes
---------

.. class:: BurnLakes(config, lake_subset_margin=2.0, force_one_lake_per_riv_seg_flag=False, single_segment_lakes_activate_flag=False, single_segment_lakesID_position=None, single_segment_lakesID_restrict=True, single_segment_lakes_remove_first_order_flag=True, single_segment_lakes_global_position="down")

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

config
  Configuration dictionary defining input datasets and column mappings.

  The expected structure is:

  ::

      config = {
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

lake_subset_margin
  Buffer distance used for lake subsetting.

force_one_lake_per_riv_seg_flag
  If True, enforces one lake per river segment.

single_segment_lakes_activate_flag
  Enables processing of single-segment lakes.

single_segment_lakesID_position
  Optional specification of lake placement rules (list, set, dict, or None).

single_segment_lakesID_restrict
  Restrict processing to specified lake IDs.

single_segment_lakes_remove_first_order_flag
  Remove first-order streams when identifying lakes.

single_segment_lakes_global_position
  Default placement direction ("down" or "up").

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
  Single-segment lakes (if enabled)

Notes
~~~~~

- Workflow is executed automatically during initialization.
- Large datasets may require significant computation time.
- Single-segment lake processing is optional.

Example
~~~~~~~

::

    from riverlakenetwork import BurnLakes

    model = BurnLakes(
        config=config,
        single_segment_lakes_activate_flag=True
    )

    riv = model.riv
    lake = model.lake