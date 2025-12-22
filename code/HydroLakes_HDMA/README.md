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

## 📁 Data Used in This Work

This project relies on the following datasets:

### 1. MERIT-Derived Global River Flows (Lin et al., 2019)
- **Description**: A global reconstruction of naturalized river flows over 2.94 million reaches using the MERIT hydrography.
- **Citation**:  
  Lin, P., Pan, M., Beck, H.E., Yang, Y., Yamazaki, D., Frasson, R., et al. (2019).  
  *Global reconstruction of naturalized river flows at 2.94 million reaches*.  
  *Water Resources Research*, 55(8), 6499–6516.  
  https://doi.org/10.1029/2019WR025287  
  > *Note: A bug-fixed version of this dataset was used in this work.*

### 2. HydroLAKES (Version 1)
- **Description**: A global database of lakes with information on their shoreline, volume, and other attributes.
- **Citation**:  
  Messager, M.L., Lehner, B., Grill, G., Nedeva, I., & Schmitt, O. (2016).  
  *Estimating the volume and age of water stored in global lakes using a geo-statistical approach*.  
  *Nature Communications*, 7, 13603.  
  https://doi.org/10.1038/ncomms13603
