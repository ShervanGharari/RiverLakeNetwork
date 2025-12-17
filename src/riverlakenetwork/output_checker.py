import pandas as pd
from collections import defaultdict
import warnings


class OutputChecker:
    """
    Post-processing integrity checks for River–Lake–Catchment outputs.

    Main check:
    - For outlet COMIDs (NextDownCOMID <= 0),
      upstream connectivity in `riv` must be a subset of `riv_org`.
    """

    def __init__(self, riv, riv_org, cat=None, lake=None):
        self.riv = riv
        self.riv_org = riv_org
        self.cat = cat
        self.lake = lake
        self._check_graph()
        self._check_inoutflow_length()

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------
    @staticmethod
    def _build_upstream_graph(riv, comid_col="COMID", down_col="NextDownCOMID"):
        """
        Build upstream connectivity graph:
        downstream COMID -> set(upstream COMIDs)
        """
        upstream = defaultdict(set)
        for comid, down in zip(riv[comid_col], riv[down_col]):
            if pd.notna(down) and down > 0:
                upstream[down].add(comid)
        return upstream

    # --------------------------------------------------
    # Checks
    # --------------------------------------------------
    def _check_graph(self):
        """
        Ensure upstream(riv) ⊆ upstream(riv_org)
        for outlet COMIDs (NextDownCOMID <= 0).
        """
        up_new = self._build_upstream_graph(self.riv)
        up_org = self._build_upstream_graph(self.riv_org)
        # Identify outlet COMIDs in riv
        outlet_comids = set(
            self.riv.loc[
                (self.riv["NextDownCOMID"].isna()) |
                (self.riv["NextDownCOMID"] <= 0),
                "COMID"
            ]
        )
        # Only compare COMIDs existing in both datasets
        outlet_comids &= set(self.riv_org["COMID"])
        violations = {}
        for comid in outlet_comids:
            new_up = up_new.get(comid, set())
            org_up = up_org.get(comid, set())
            if not new_up.issubset(org_up):
                violations[comid] = {
                    "extra_upstream": new_up - org_up,
                    "riv_upstream": new_up,
                    "riv_org_upstream": org_up,
                }
        if violations:
            example = next(iter(violations))
            msg = (
                f"River network topology check failed.\n"
                f"- Checked outlet COMIDs: {len(outlet_comids)}\n"
                f"- Violations found: {len(violations)}\n\n"
                f"Example violation:\n"
                f"  COMID {example}\n"
                f"  Extra upstream in riv: {violations[example]['extra_upstream']}"
            )
            raise ValueError(msg)

    def _check_inoutflow_length(self, tol=1e-6):
        """
        Check in/outflow river segments with near-zero length.
        For riv segments with inoutflow == 1 and length <= tol,
        identify whether the segment connects an upstream lake
        to a downstream lake.
        """
        required = {"COMID", "NextDownCOMID", "inoutflow", "length"}
        missing = required - set(self.riv.columns)
        if missing:
            raise ValueError(f"Missing required columns in riv: {missing}")
        if self.lake is None or "LakeCOMID" not in self.lake.columns:
            raise ValueError("Lake dataframe with 'LakeCOMID' is required.")
        if "islake" not in self.riv.columns:
            raise ValueError("riv must contain 'islake' flag.")
        # Identify upstream columns (up1, up2, ...)
        up_cols = [c for c in self.riv.columns if c.lower().startswith("up")]
        # Identify problematic in/outflow links
        bad_links = self.riv[
            (self.riv["inoutflow"] == 1)
            & (
                self.riv["length"].isna()
                | (self.riv["length"] <= tol)
            )
        ]
        # print(bad_links)
        for _, row in bad_links.iterrows():
            comid = int(row["COMID"])
            # -------------------------------------------------
            # 1. Collect related COMIDs (up* + NextDownCOMID)
            # -------------------------------------------------
            related = set()
            down = row["NextDownCOMID"]
            if pd.notna(down) and down > 0:
                related.add(int(down))
            for col in up_cols:
                val = row[col]
                if pd.notna(val) and val > 0:
                    related.add(int(val))
            if not related:
                continue
            # -------------------------------------------------
            # 2. Slice riv once and keep only lake segments
            # -------------------------------------------------
            riv_slice = self.riv.loc[
                self.riv["COMID"].astype("Int64").isin(related)
                & (self.riv["islake"].astype("Int64") == 1)
            ]
            if riv_slice.empty:
                continue
            # -------------------------------------------------
            # 3. Resolve LakeCOMID from lake table
            # -------------------------------------------------
            lakes_comids = riv_slice["COMID"].astype(int).tolist()
            lake_slice = self.lake.loc[
                self.lake["COMID"].astype("Int64").isin(lakes_comids)
            ]
            lakes_ids = lake_slice["LakeCOMID"].astype(int).tolist()
            # -------------------------------------------------
            # 4. Warn only if lake–lake connector
            # -------------------------------------------------
            if len(lakes_comids) >= 2:
                print(
                    "\n[WARNING] Lake–lake in/outflow connector with near-zero length detected:\n"
                    f"  River COMID          : {comid}\n"
                    f"  length               : {row['length']}\n"
                    f"  Connected Lake IDs   : {lakes_ids}\n"
                    f"  Connected Lake COMIDs: {lakes_comids}\n"
                    "  Interpretation       : This river segment links two hydrologically\n"
                    "                         connected lakes that are represented as separate\n"
                    "                         features (e.g., Lake Michigan–Lake Huron).\n"
                    "  Recommended fix      : Merge or correct the lake geometries in the\n"
                    "                         lake shapefile and rerun the scripts.\n"
                )