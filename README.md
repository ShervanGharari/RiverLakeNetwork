# 🔥 Burning Lakes and Reservoirs into River Network Topology

This repository provides a **Python-based workflow for integrating lakes and reservoirs into an existing river network topology**. It combines **vector river networks, lake/reservoir polygons, and subbasin polygons** to produce a **topologically consistent river–lake system** suitable for hydrological modeling.

The primary objective is to **identify resolvable lakes and reservoirs based on river network density** and to update river connectivity, geometry, and contributing areas accordingly—**without requiring DEM or land-cover inputs** typically used in traditional hydro-conditioning workflows.

---

## 🌍 Motivation

Representing lakes and reservoirs consistently within river networks is a long-standing challenge. Conventional approaches typically rely on:

* DEM conditioning
* Flow-direction enforcement
* Water-body masking or land-cover classification

However, these datasets are often unavailable or incompatible, especially when river networks are:

* Manually digitized (*blue-line networks*)
* Provided by external agencies or hydrographers
* Derived from proprietary or legacy workflows

At the same time, **vector-based lake and reservoir datasets** (e.g., satellite-derived products or cartographic inventories) are widely available.

This workflow bridges this gap by **directly integrating vector river networks and vector lake/reservoir datasets**, allowing both to be iteratively refined toward a consistent hydrological representation.

---

## 🧠 Key Concept: Resolvable Lakes

Not all lakes need to be explicitly represented in a river network.

A lake or reservoir is considered **resolvable** when it is large enough—relative to the river network resolution—to meaningfully influence:

* Flow connectivity
* River routing structure
* Upstream contributing area distribution

Resolvable lakes typically:

* Intersect multiple river segments or subbasins
* Replace or modify river segments
* Introduce explicit lake-routing behavior

Non-resolvable lakes remain implicitly represented through subbasin areas and do **not modify river topology**.

---

## 📦 Required Inputs (Vector-Based)

### 1️⃣ River Network (`riv`)

A line-based river network with the following required attributes:

| Column       | Description                                        |
| ------------ | -------------------------------------------------- |
| `COMID`      | Unique river segment identifier                    |
| `NextDownID` | Downstream segment ID (`-9999` for outlets)        |
| `lengthm`    | River segment length (meters)                      |
| `unitarea`   | Local contributing area                            |
| `uparea`     | Upstream accumulated contributing area             |
| `geometry`   | Line geometry (may be `None` for coastal segments) |

---

### 2️⃣ Subbasins / Catchments (`cat`)

A polygon dataset defining contributing areas for each river segment.

Each subbasin must correspond exactly to one river `COMID`.

| Column     | Description                                 |
| ---------- | ------------------------------------------- |
| `COMID`    | Subbasin identifier (matches river `COMID`) |
| `unitarea` | Subbasin area                               |
| `geometry` | Polygon geometry                            |

---

### 3️⃣ Lakes and Reservoirs (`lake`)

A polygon dataset representing lakes and reservoirs.

| Column     | Description                                         |
| ---------- | --------------------------------------------------- |
| `LakeID`   | Unique lake/reservoir identifier                    |
| `unitarea` | Lake surface area (consistent units with subbasins) |
| `geometry` | Polygon geometry                                    |

---

## 🔧 Installation

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

## ⚙️ Workflow Overview

1. Validate river–subbasin consistency
2. Identify resolvable lakes based on network density
3. Intersect lakes with river segments and subbasins
4. Modify river connectivity and segment attributes
5. Convert submerged river segments to zero-length links
6. Reassign downstream connectivity through lakes
7. Update affected subbasins (including coastal reclassification)
8. Recompute upstream contributing areas
9. Apply topology consistency checks

The workflow is **iterative**, allowing refinement of lake representation depending on modeling needs.

---

## 🎯 Applications

* Large-scale hydrological routing models
* Lake-aware river network preprocessing
* Harmonizing independently derived hydro datasets
* Regional to global water resources modeling

---

## 📁 Examples

The repository includes several worked examples demonstrating lake integration across different river network products:

* **Example 1 – MERIT Hydro + HydroLAKES**
  Integration of HydroLAKES into a MERIT-derived river network
  [`./examples/Example01_MERITDerivedHydroLAKES.ipynb`](./examples/Example01_MERITDerivedHydroLAKES.ipynb)

* **Example 2 – HDMA + HydroLAKES**
  Integration into an HDMA river network
  [`./examples/Example02_HDMAHydroLAKES.ipynb`](./examples/Example02_HDMAHydroLAKES.ipynb)

* **Example 3 – MERITBasins + HydroLAKES**
  Integration into MERITBasins network
  [`./examples/Example03_MERITBasinsHydroLAKES.ipynb`](./examples/Example03_MERITBasinsHydroLAKES.ipynb)

![Example comparison](./examples/Plots/Figure_2.png)

---

## 🧾 How to Cite

If you use this tool or its methodology, please cite:

> Gharari, S., Vanderkelen, I., Tefs, A., Mizukami, N., Kluzek, E., Stadnyk, T., Lawrence, D., & Clark, M. P. (2024).
> *A flexible framework for simulating the water balance of lakes and reservoirs from local to global scales: mizuRoute‐Lake.*
> Water Resources Research, 60(5), e2022WR032400.
> https://doi.org/10.1029/2022WR032400
