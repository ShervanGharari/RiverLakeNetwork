.. RiverLakeNetwork documentation master file

🔥 Burning Lakes and Reservoirs into River Network Topology
============================================================

This package provides a Python-based workflow for integrating lakes and reservoirs into an existing river network topology. It combines vector river networks, lake/reservoir polygons, and subbasin polygons to produce a topologically consistent river–lake system suitable for hydrological modeling.

The main objective is to identify resolvable lakes and reservoirs based on river network density and update river connectivity, geometry, and contributing areas accordingly—without requiring DEM or land-cover inputs typically used in traditional hydro-conditioning workflows.

------------------------------------------------------------

🌍 Motivation
-------------

Representing lakes and reservoirs consistently within river networks is challenging. Traditional approaches rely on:

- Digital Elevation Model (DEM) conditioning
- Flow-direction enforcement
- Water-body masking or land-cover classification

These approaches are often not available or are inconsistent when river networks are:

- Manually digitized (blue-line networks)
- Provided by external agencies or hydrographers
- Derived from proprietary or legacy workflows

Meanwhile, vector-based lake and reservoir datasets are widely available from satellite products and global inventories.

This workflow bridges this gap by directly integrating vector river networks and vector lake/reservoir datasets.

------------------------------------------------------------

🧠 Key Concept: Resolvable Lakes
--------------------------------

Not all lakes must be explicitly represented in a river network.

A lake or reservoir is considered *resolvable* if it is large enough—relative to the river network resolution—to meaningfully affect:

- Flow connectivity
- River routing structure
- Upstream contributing area distribution

Resolvable lakes typically:

- Intersect multiple river segments or subbasins
- Replace or modify river segments
- Introduce explicit lake-routing behavior

Non-resolvable lakes remain implicitly represented through subbasin areas and do not modify river topology.

------------------------------------------------------------

📦 Required Inputs
------------------

River Network (``riv``)
------------------------

A line-based river network with required attributes:

+---------------+--------------------------------------------+
| Column        | Description                                |
+===============+============================================+
| COMID         | Unique river segment identifier            |
+---------------+--------------------------------------------+
| NextDownCOMID | Downstream segment ID (-9999 for outlets)  |
+---------------+--------------------------------------------+
| length        | River segment length                       |
+---------------+--------------------------------------------+
| uparea        | Upstream contributing area                 |
+------------+-----------------------------------------------+

If uparea does not exists for a river network, it can be calculated based on unitarea and RiverLakeNetwork Utility.compute_uparea functionality.

Subbasins / Catchments (``cat``)
--------------------------------

Each subbasin must correspond exactly to one river COMID.

+----------+------------------------------+
| Column   | Description                  |
+==========+==============================+
| COMID    | Subbasin identifier          |
+----------+------------------------------+
| unitarea | Subbasin area                |
+----------+------------------------------+

Lakes and Reservoirs (``lake``)
--------------------------------

+----------+------------------------------+
| Column   | Description                  |
+==========+==============================+
| LakeCOMID| Unique lake identifier       |
+----------+------------------------------+
| unitarea | Lake surface area            |
+----------+------------------------------+

------------------------------------------------------------

⚙️ Workflow Overview
--------------------

1. Validate river–subbasin consistency
2. Identify resolvable lakes based on network density
3. Intersect lakes with river segments and subbasins
4. Modify river connectivity and segment attributes
5. Convert submerged river segments to zero-length links
6. Reassign downstream connectivity through lakes
7. Update affected subbasins (including coastal reclassification)
8. Recompute upstream contributing areas
9. Apply topology consistency checks

The workflow is iterative and can be refined depending on modeling needs.

------------------------------------------------------------

🎯 Applications
---------------

- Large-scale hydrological routing models
- Lake-aware river network preprocessing
- Harmonizing independently derived hydro datasets
- Regional to global water resources modeling

------------------------------------------------------------

📁 Examples
-----------

The repository includes several examples demonstrating lake integration and different configuration options:

* **Illustrative Example**

  A simple synthetic example demonstrating the basic workflow and lake integration concept.

  `Illustrative Example <https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case01_IllustrativeExample/IllustrativeExample.ipynb>`_

* **MERIT Hydro + HydroLAKES**

  Integration into MERIT-derived river networks.

  `MERIT Hydro + HydroLAKES Example <https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02C_Derived/MERITDerivedHydroLAKES.ipynb>`_

* **HDMA + HydroLAKES**

  Integration into HDMA river networks.

  `HDMA + HydroLAKES Example <https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02A_HDMA/HDMAHydroLAKES.ipynb>`_

* **MERITBasins + HydroLAKES**

  Integration into the MERITBasins river network.

  `MERITBasins + HydroLAKES Example <https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02B_MERIT/MERITBasinsHydroLAKES.ipynb>`_

* **Different Control Flags**

  Demonstration of different user-defined options and control flags for lake integration.

  `MERITBasins + HydroLAKES with Different Choices <https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case03_DifferentChoices/Case03_MERIT/MERITBasinsHydroLAKES.ipynb>`_

------------------------------------------------------------

🧾 Citation
-----------

If you use this package or methodology, please cite:

Gharari, S., Vanderkelen, I., Tefs, A., Mizukami, N., Kluzek, E., Stadnyk, T., Lawrence, D., & Clark, M. P. (2024).
*A flexible framework for simulating the water balance of lakes and reservoirs from local to global scales: mizuRoute-Lake.*
Water Resources Research, 60(5), e2022WR032400.
https://doi.org/10.1029/2022WR032400