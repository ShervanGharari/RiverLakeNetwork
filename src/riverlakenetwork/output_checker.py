import pandas as pd
from collections import defaultdict


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
