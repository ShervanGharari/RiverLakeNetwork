## 🔥 Lake Burning into River Network Topology

This repository provides a Python-based workflow for **burning lakes and reservoirs into an existing river network topology**. It is tailored to work with user-provided shapefiles of river networks and lake polygons, enabling integration of lake features into the hydrological connectivity structure.

The main goal is to **approximate the effect of lakes/reservoirs on river networks** by adjusting the river geometry and topology to include resolvable lakes — those large enough to impact flow direction and catchment connectivity.

### 🧩 Key Features

- **Flexible Input**: Accepts any shapefiles for river and lake data.
- **Customized River Network**: Requires river segments to include the following attributes:
  - `ID`: unique identifier for each river segment
  - `nextDownID`: downstream segment ID
  - `unitarea`: local catchment area for the segment
  - `uparea`: accumulated upstream area
- **Lake Integration**:
  - Identifies resolvable lakes that intersect multiple river segments.
  - Simplifies and burns these lake features into the river network based on spatial rules.
  - Updates the topology (`nextDownID`, `ID`, etc.) to reflect new lake-routing behavior.
- **Adaptive Resolution**: Produces a lake-burned river network consistent with the spatial density of the original river data.

This tool is especially useful for hydrological modeling frameworks that require coherent topological routing through both river segments and lake bodies, ensuring that lakes act as proper flow regulators in the river system.

## 🧾 How to Cite

If you use this tool or build upon its approach, please cite the following publication, which forms the conceptual basis for lake representation and integration into river network topology:

> **Gharari, S., Vanderkelen, I., Tefs, A., Mizukami, N., Kluzek, E., Stadnyk, T., Lawrence, D., & Clark, M. P. (2024).**  
> _A flexible framework for simulating the water balance of lakes and reservoirs from local to global scales: mizuRoute‐Lake._  
> **Water Resources Research**, 60(5), e2022WR032400.  
> [https://doi.org/10.1029/2022WR032400](https://doi.org/10.1029/2022WR032400)

