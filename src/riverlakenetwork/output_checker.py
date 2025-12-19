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
        self._check_lake_outlet_graph_simple()
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
            print(msg)
            # raise ValueError(msg)

    def _check_graph_with_lakes(self):
        """
        Ensure upstream(riv) ⊆ upstream(riv_org) for outlet COMIDs.

        Additionally:
        - Identify violating upstream segments
        - Scan up1..upN (based on maxup) for lake-related upstreams
        - Report LakeCOMIDs involved in violations
        """

        # Build upstream graphs
        up_new = self._build_upstream_graph(self.riv)
        up_org = self._build_upstream_graph(self.riv_org)

        riv = self.riv
        riv_org = self.riv_org

        # Index for fast lookup
        riv_idx = riv.set_index("COMID")
        riv_org_comids = set(riv_org["COMID"])

        # Outlet COMIDs in riv
        outlet_comids = set(
            riv.loc[
                riv["NextDownCOMID"].isna() | (riv["NextDownCOMID"] <= 0),
                "COMID",
            ]
        )

        # Only compare outlets existing in both datasets
        outlet_comids &= riv_org_comids

        violations = {}
        lake_comids_all = set()

        for comid in outlet_comids:
            new_up = up_new.get(comid, set())
            org_up = up_org.get(comid, set())

            if new_up.issubset(org_up):
                continue

            extra_up = new_up - org_up
            lake_upstream = {}

            # -----------------------------------------
            # Scan all upstream slots (up1..upN)
            # -----------------------------------------
            for upc in extra_up:
                if upc not in riv_idx.index:
                    continue

                row = riv_idx.loc[upc]
                nup = int(row.get("maxup", 0))

                for i in range(1, nup + 1):
                    col = f"up{i}"
                    if col not in row:
                        continue

                    up_up = row[col]
                    if pd.isna(up_up):
                        continue

                    up_up = int(up_up)

                    if up_up not in riv_idx.index:
                        continue

                    up_row = riv_idx.loc[up_up]
                    lake_comid = up_row.get("LakeCOMID", None)

                    if pd.notna(lake_comid) and lake_comid > 0:
                        lake_upstream.setdefault(upc, set()).add(int(lake_comid))
                        lake_comids_all.add(int(lake_comid))

            violations[comid] = {
                "extra_upstream": extra_up,
                "lake_related_upstream": lake_upstream,
            }

        # -----------------------------------------
        # Reporting
        # -----------------------------------------
        if violations:
            print("River network topology check failed.")
            print(f"- Checked outlet COMIDs: {len(outlet_comids)}")
            print(f"- Violations found: {len(violations)}\n")

            for comid, info in violations.items():
                print(f"Outlet COMID {comid}")
                print(f"  Extra upstream COMIDs: {sorted(info['extra_upstream'])}")

                if info["lake_related_upstream"]:
                    print("  Lake-related upstream segments:")
                    for u, lakes in info["lake_related_upstream"].items():
                        print(f"    COMID {u} → LakeCOMIDs {sorted(lakes)}")
                else:
                    print("  No lake-related upstream segments detected.")
                print()

            print("All LakeCOMIDs involved in violations:")
            print(sorted(lake_comids_all))

        #return violations, lake_comids_all

    def _check_lake_outlet_graph_simple(self):
        """
        Loop-based lake outlet topology check.

        For each exorheic lake:
        1. Check upstream(riv, non-lake) ⊆ upstream(riv_org)
        2. Ensure outlet has only lake as direct upstream
        3. Ensure outlet COMID appears only once in NextDownCOMID
        4. Collect violated LakeCOMIDs and report at the end
        """

        riv = self.riv
        riv_org = self.riv_org

        up_riv = self._build_upstream_graph(riv)
        up_org = self._build_upstream_graph(riv_org)

        riv_idx = riv.set_index("COMID")

        violations = []
        violated_lake_ids = set()

        # --------------------------------------------------
        # Loop over lake segments
        # --------------------------------------------------
        for _, lake_row in riv.iterrows():

            if lake_row.get("islake") != 1:
                continue

            if lake_row.get("exoheic") != 1:
                continue

            lake_comid = int(lake_row["COMID"])
            lake_id = lake_row.get("LakeCOMID")

            outlet = lake_row.get("NextDownCOMID")
            if pd.isna(outlet) or outlet <= 0:
                continue

            outlet = int(outlet)
            if outlet not in riv_idx.index:
                continue

            # --------------------------------------------------
            # Build upstream sets
            # --------------------------------------------------
            upstream_riv = up_riv.get(outlet, set())
            upstream_org = up_org.get(outlet, set())

            upstream_riv_non_lake = {
                c for c in upstream_riv
                if c in riv_idx.index and riv_idx.loc[c].get("islake") != 1
            }

            # --------------------------------------------------
            # Check 1: upstream subset condition
            # --------------------------------------------------
            if not upstream_riv_non_lake.issubset(upstream_org):
                violations.append({
                    "type": "upstream_mismatch",
                    "outlet_comid": outlet,
                    "lake_comid": lake_comid,
                    "lake_id": lake_id,
                    "extra_upstream": upstream_riv_non_lake - upstream_org,
                })
                violated_lake_ids.add(lake_id)

            # --------------------------------------------------
            # Check 2: outlet has only lake as direct upstream
            # --------------------------------------------------
            direct_up = riv.loc[riv["NextDownCOMID"] == outlet, "COMID"].tolist()

            non_lake_direct = [
                c for c in direct_up
                if c in riv_idx.index and riv_idx.loc[c].get("islake") != 1
            ]

            if non_lake_direct:
                violations.append({
                    "type": "multiple_direct_upstreams",
                    "outlet_comid": outlet,
                    "lake_comid": lake_comid,
                    "lake_id": lake_id,
                    "extra_upstreams": non_lake_direct,
                })
                violated_lake_ids.add(lake_id)

            # --------------------------------------------------
            # Check 3: outlet appears only once in NextDownCOMID
            # --------------------------------------------------
            count_down = (riv["NextDownCOMID"] == outlet).sum()

            if count_down > 1:
                violations.append({
                    "type": "outlet_not_unique",
                    "outlet_comid": outlet,
                    "lake_comid": lake_comid,
                    "lake_id": lake_id,
                    "count": int(count_down),
                })
                violated_lake_ids.add(lake_id)

        # --------------------------------------------------
        # Reporting
        # --------------------------------------------------
        if violations:
            print("\n⚠️ Lake outlet topology issues detected\n")

            for v in violations:
                print(f"Outlet COMID: {v['outlet_comid']}")
                print(f"Lake COMID:   {v['lake_comid']}")
                print(f"Lake ID:      {v['lake_id']}")
                print(f"Issue type:   {v['type']}")

                if "extra_upstream" in v:
                    print(f"Extra upstream (non-lake): {sorted(v['extra_upstream'])}")

                if "extra_upstreams" in v:
                    print(f"Unexpected direct upstreams: {sorted(v['extra_upstreams'])}")

                if "count" in v:
                    print(f"NextDownCOMID appears {v['count']} times")

                print("-" * 45)

            print("\n🚩 Violated LakeCOMIDs:")
            print(sorted(lid for lid in violated_lake_ids if pd.notna(lid)))

        else:
            print("✓ No lake outlet topology issues found.")

        A = sorted(lid for lid in violated_lake_ids if pd.notna(lid))
        print(A)
        print(violations)

        # return violations, sorted(lid for lid in violated_lake_ids if pd.notna(lid))



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