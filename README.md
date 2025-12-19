# 🔥 Burning Lakes and Reservoirs into River Network Topology

This repository provides a **Python-based workflow for burning lakes and reservoirs into an existing river network topology**. The workflow integrates **vector-based river networks, lake/reservoir polygons, and subbasin polygons** to produce a **topologically consistent river–lake network** suitable for hydrological modeling.

The core objective is to **identify resolvable lakes and reservoirs given a river network density** and to modify river connectivity, geometry, and contributing areas accordingly—**without requiring access to the DEM or land-cover data** used to derive the original river network.

---

## 🌍 Motivation

Representing lakes and reservoirs consistently within river networks is challenging. Traditionally, this requires:
- DEM conditioning
- Flow-direction enforcement
- Water-body masking or land-cover classification

However, these inputs are often unavailable—especially when river networks are:
- Manually digitized (*blue lines*)
- Provided by agencies or hydrographers
- Derived from proprietary or legacy workflows

At the same time, **vector lake and reservoir datasets**—from satellite observations, land-cover products, or cartographic mapping—are widely available.

This workflow bridges that gap by **merging vector river networks and vector lake/reservoir datasets directly**, allowing both to be iteratively refined to reach a desired level of representation within a target modeling system.

---

## 🧠 Key Concept: Resolvable Lakes

Not all lakes should be explicitly represented in a river network.

A lake or reservoir is considered **resolvable** if it is large enough—relative to the river network density—to meaningfully affect:
- Flow connectivity
- River routing
- Upstream contributing areas

Resolvable lakes:
- Intersect multiple river segments or subbasins
- Replace or modify river segments
- Introduce explicit lake-routing behavior

Non-resolvable lakes remain implicitly represented through subbasin areas and do **not** alter river topology.

---

## 📦 Required Inputs (All Vector-Based)

### 1️⃣ River Network (`riv`)

A line-based river network dataset with the following required attributes:

| Column | Description |
|------|-------------|
| `COMID` | Unique river segment identifier |
| `NextDownID` | Downstream river segment ID (`-9999` for outlets) |
| `lengthm` | River segment length (meters) |
| `unitarea` | Local contributing area |
| `uparea` | Accumulated upstream contributing area |
| `geometry` | Line geometry (`None` allowed for coastal segments) |

#### Example `riv`

```
COMID, NextDownID, lengthm, unitarea, uparea, geometry
1, 3, 10, 10, 10, LINESTRING(...)
2, 3, 15, 20, 20, LINESTRING(...)
3, -9999, 9, 10, 40, LINESTRING(...)
4, -9999, 0, 20, 20, None
```

---

### 2️⃣ Subbasins / Catchments (`cat`)

A polygon dataset defining contributing areas for each river segment.

Each subbasin **must correspond exactly** to one river `COMID`.

| Column | Description |
|------|-------------|
| `COMID` | Subbasin ID (matches river `COMID`) |
| `unitarea` | Subbasin area |
| `geometry` | Polygon geometry |

#### Example `cat`

```
COMID, unitarea, geometry
1, 10, POLYGON(...)
2, 20, POLYGON(...)
3, 10, POLYGON(...)
4, 10, POLYGON(...)
```

---

### 3️⃣ Lakes and Reservoirs (`lake`) — Required

A polygon dataset representing lakes and reservoirs.

Each lake or reservoir must include:

| Column | Description |
|------|-------------|
| `LakeID` | Unique lake/reservoir identifier (e.g., 100, 200) |
| `unitarea` | Lake surface area |
| `geometry` | Polygon geometry |

#### Example `lake`

```
LakeID, unitarea, geometry
100, 50, POLYGON(...)
200, 120, POLYGON(...)
```

---

## 🔧 Installation

### Local Installation

```
git clone https://github.com/<username>/riverlakenetwork.git
cd riverlakenetwork
pip install .
```

Editable install:

```
pip install -e .
```

---

### PyPI Installation (Coming Soon)

```
pip install riverlakenetwork
```

---

## ⚙️ Workflow Overview

1. Validate river–subbasin consistency
2. Identify resolvable lakes based on river network density
3. Intersect lakes with river segments and subbasins
4. Modify river connectivity and lengths
5. Convert submerged river segments to zero-length segments
6. Reassign downstream connections to lakes
7. Reclassify affected subbasins as coastal
8. Recompute upstream contributing areas
9. Apply topology consistency checks and warnings

The workflow is **iterative by design**, allowing refinement until the desired representation is achieved.

---

## 🎯 Typical Applications

- Large-scale hydrological routing models
- Lake-aware river network preprocessing
- Harmonizing independently derived river and lake datasets
- Regional to global water resources modeling

---

## 📁 Examples

The repository includes several worked examples demonstrating how lakes and reservoirs are burned into different river network topologies and how resolvable lakes are identified based on river network density.

- **Example 1 – Marti Basins with HydroRIVERS and HydroLAKES**
  Demonstrates integration of HydroLAKES into a HydroRIVERS-based river network for the Marti basins.
  [./examples/Example01_MERITBasinsHydroLAKES.ipynb](./examples/Example01_MERITBasinsHydroLAKES.ipynb)

---

## 🧾 How to Cite

If you use this tool or build upon its approach, please cite the following publication, which forms the conceptual basis for lake representation and integration into river network topology:

> **Gharari, S., Vanderkelen, I., Tefs, A., Mizukami, N., Kluzek, E., Stadnyk, T., Lawrence, D., & Clark, M. P. (2024).**
> _A flexible framework for simulating the water balance of lakes and reservoirs from local to global scales: mizuRoute‐Lake._
> **Water Resources Research**, 60(5), e2022WR032400.
> [https://doi.org/10.1029/2022WR032400](https://doi.org/10.1029/2022WR032400)
