# Lake and River Network Correction for MERIT-Hydro using HydroLakes

This Python script processes and integrates HydroLakes data with the MERIT-Hydro river and catchment dataset. It performs geometric intersection, filtering, and correction of river networks to identify resolvable lakes and reservoirs, and updates river segment connectivity accordingly.

---

## 📌 Overview

The script carries out the following:

- Reads configuration from a `Config.yaml` file containing paths and options.
- Loads MERIT-Basins data: river (`riv`), catchment (`cat`), and coast (`cst`) GeoPackage files.
- Reads and filters HydroLakes polygons based on the extent of MERIT-Basins tiles.
- Identifies **resolvable lakes**:
  - Intersects river segments with lakes.
  - Keeps only lakes intersecting multiple segments.
  - Removes small lakes or ambiguous intersections.
  - Assigns unique COMIDs to lakes and saves them as `resolvable_lakes.gpkg`.
- Modifies river and catchment geometries to exclude lake areas.
- Updates river network topology by adjusting upstream/downstream connectivity based on inflow/outflow rules for lakes.

---

## 🛠️ Dependencies

Make sure you have the following Python packages installed:

```bash
pip install geopandas shapely pandas numpy matplotlib pyyaml networkx git+https://github.com/ShervanGharari/hydrant.git@dev
```

---

## 🛠️ Dependencies

Make sure you have the following Python packages installed:

```bash
pip install geopandas shapely pandas numpy matplotlib pyyaml networkx git+https://github.com/ShervanGharari/hydrant.git@dev
```