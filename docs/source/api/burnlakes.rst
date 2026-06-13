# BurnLakes Class

.. class:: BurnLakes(config, lake_subset_margin=2.0, force_one_lake_per_riv_seg_flag=False, single_segment_lakes_activate_flag=False, single_segment_lakesID_position=None, single_segment_lakesID_restrict=True, single_segment_lakes_remove_first_order_flag=True, single_segment_lakes_global_position="down")

Main workflow class for processing, resolving, and integrating lakes into a river network.

This class orchestrates the full pipeline, including input loading, validation,
lake resolution, network correction, optional handling of single-segment lakes,
and output validation.

**Workflow Steps:**

1. Load input datasets (catchments, rivers, lakes)
2. Validate inputs
3. Identify resolvable lakes
4. Correct river network topology
5. (Optional) Identify single-segment lakes
6. (Optional) Correct topology including single-segment lakes
7. Validate outputs

:param dict config:
Configuration dictionary containing file paths and settings required by the input loader.

:param float lake_subset_margin:
Buffer distance (in map units) used when subsetting lakes relative to river segments.
Default is 2.0.

:param bool force_one_lake_per_riv_seg_flag:
If True, ensures that at most one lake is assigned per river segment.
Default is False.

:param bool single_segment_lakes_activate_flag:
If True, activates identification and processing of single-segment lakes.
Default is False.

:param single_segment_lakesID_position:
Optional specification of lake placement rules for single-segment lakes.
Can be a list, set, or dictionary of IDs and positions.

:type single_segment_lakesID_position: list[int] | set[int] | dict[int, str] | None

:param bool single_segment_lakesID_restrict:
If True, restricts processing to only specified lake IDs.
Default is True.

:param bool single_segment_lakes_remove_first_order_flag:
If True, removes first-order streams from consideration when identifying
single-segment lakes.
Default is True.

:param str single_segment_lakes_global_position:
Default placement for single-segment lakes ("down" or "up").
Default is "down".

**Attributes:**

.. attribute:: cat
:type: geopandas.GeoDataFrame

```
  Processed catchment dataset.
```

.. attribute:: riv
:type: geopandas.GeoDataFrame

```
  Processed river network dataset.
```

.. attribute:: lake
:type: geopandas.GeoDataFrame

```
  Final resolved lake dataset.
```

.. attribute:: cat_org
:type: geopandas.GeoDataFrame

```
  Original catchment dataset (post-validation).
```

.. attribute:: riv_org
:type: geopandas.GeoDataFrame

```
  Original river dataset (post-validation).
```

.. attribute:: lake_org
:type: geopandas.GeoDataFrame

```
  Original lake dataset (post-validation).
```

.. attribute:: single_segment_lake
:type: geopandas.GeoDataFrame

```
  Identified single-segment lakes (only present if enabled).
```

**Notes:**

* The class executes the full workflow during initialization.
* Intermediate steps are not exposed as separate public methods.
* Large datasets may result in significant processing time due to
  topology correction and spatial operations.

**Example:**

.. code-block:: python

```
  from yourpackage import BurnLakes

  config = {
      "cat_path": "catchments.shp",
      "riv_path": "rivers.shp",
      "lake_path": "lakes.shp"
  }

  model = BurnLakes(
      config=config,
      single_segment_lakes_activate_flag=True
  )

  processed_rivers = model.riv
  processed_lakes = model.lake
```

