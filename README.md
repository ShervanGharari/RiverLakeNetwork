# RiverLakeNetwork: A Python Package for Integrating Lakes and Reservoirs into River Networks

This repository provides a **Python-based workflow for integrating lakes and reservoirs into existing river network topologies**. It combines **vector river networks, lake/reservoir polygons, and subbasin polygons** to produce a **topologically consistent river–lake system** suitable for river and lake routing applications.

The primary objective is to **identify resolvable lakes and reservoirs based on river network density** and update river connectivity, geometry, and contributing areas accordingly—**without requiring DEM or land-cover inputs** typically used in traditional hydro-conditioning workflows. This approach avoids the over-representation or under-representation of lakes and reservoirs within existing river network topologies.

---

## Motivation

Representing lakes and reservoirs consistently within river networks is a long-standing challenge. Existing river networks are commonly derived from DEMs, while lake and reservoir datasets are generated from different sources, including satellite observations, land-cover products, or locally mapped datasets.

RiverLakeNetwork provides a workflow that directly integrates vector river networks with vector lake and reservoir datasets, allowing both components to be iteratively refined toward a consistent hydrological representation.

---

## Key Concept: Resolvable Lakes

Not all lakes need to be explicitly represented within a river network.

A lake or reservoir is considered **resolvable** when it is sufficiently represented at the resolution of the river network and can meaningfully influence flow connectivity. The `BurnLakes` class identifies both **multi-segment** and **single-segment** resolvable lakes and reservoirs based on spatial relationships, river network topology, upstream and downstream connectivity, and other network characteristics.

Non-resolvable lakes remain implicitly represented through subbasin areas and do **not modify river network topology**.

---

## Inputs (Vector-Based)

### River Network (`riv`)

A line-based river network with the following required attributes:

| Column       | Description                                        |
| ------------ | -------------------------------------------------- |
| `COMID`      | Unique river segment identifier                    |
| `NextDownID` | Downstream segment ID (`-9999` for outlets)        |
| `length`     | River segment length                               |
| `uparea`     | Upstream accumulated contributing area             |

The upstream contributing area (``uparea``) attribute in ``riv`` is required for the workflow. If it is not available, it can be calculated from the river network topology and catchment unit areas using the RiverLakeNetwork ``Utility.compute_uparea`` function.

---

### Subbasins / Catchments (`cat`)

A polygon dataset defining contributing areas for each river segment.

Each subbasin must correspond exactly to one river `COMID`.

| Column     | Description                                 |
| ---------- | ------------------------------------------- |
| `COMID`    | Subbasin identifier (matches river `COMID`) |
| `unitarea` | Subbasin area                               |

---

### Lakes and Reservoirs (`lake`)

A polygon dataset representing lakes and reservoirs.

| Column     | Description                                         |
| ---------- | --------------------------------------------------- |
| `LakeID`   | Unique lake/reservoir identifier                    |
| `unitarea` | Lake surface area (consistent units with subbasins) |

---

## Installation

### Local installation

```bash
git clone https://github.com/ShervanGharari/RiverLakeNetwork.git
cd RiverLakeNetwork
pip install .
```

Editable install:

```bash
pip install -e .
```

---

### PyPI installation (planned)

```bash
pip install riverlakenetwork
```

---

## Examples

* **Illustrative Example**

  A simple synthetic example demonstrating the basic workflow and the concept of lake integration. ![link](https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case01_IllustrativeExample/IllustrativeExample.ipynb>)

* **HDMA + HydroLAKES**

  Integration of HydroLAKES into an HDMA river network. ![link](https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02A_HDMA/HDMAHydroLAKES.ipynb>)

* **MERITBasins + HydroLAKES**

  Integration of HydroLAKES into the MERITBasins river network. ![link](https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02B_MERIT/MERITBasinsHydroLAKES.ipynb)

* **MERIT Hydro + HydroLAKES**

  Integration of HydroLAKES into a MERIT-derived river network. ![link](https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case02_MultipleRiverNetwork/Case02C_Derived/MERITDerivedHydroLAKES.ipynb)

* **Different Control Flags**

  Demonstration of different user-defined options and control flags for controlling lake identification and integration. ![link](https://github.com/ShervanGharari/RiverLakeNetwork/blob/main/examples/Case03_DifferentChoices/Case03_MERIT/MERITBasinsHydroLAKES.ipynb)

![Example comparison](https://github.com/ShervanGharari/RiverLakeNetwork/blob/rename/examples/Case02_MultipleRiverNetwork/Case02X_Figure/Figure.png)

---

## How to Cite

> Gharari, S., Vanderkelen, I., Tefs, A., Mizukami, N., Kluzek, E., Stadnyk, T., Lawrence, D., & Clark, M. P. (2024).
> *A flexible framework for simulating the water balance of lakes and reservoirs from local to global scales: mizuRoute‐Lake.*
> Water Resources Research, 60(5), e2022WR032400.
> https://doi.org/10.1029/2022WR032400
