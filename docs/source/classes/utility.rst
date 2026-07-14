Utility
-------

.. class:: Utility()

Helper class providing utility functions for river network preprocessing and analysis.

The ``Utility`` class contains general-purpose functions used for river network preparation, including calculation of upstream contributing area and identification of immediate upstream connectivity. These functions can be used independently or as supporting tools within the RiverLakeNetwork workflow.


compute_uparea
~~~~~~~~~~~~~~

.. method:: Utility.compute_uparea(riv, mapping={"id": "COMID", "next_id": "NextDownCOMID", "unitarea": "unitarea"}, out_col="uparea")

Calculate upstream contributing area (``uparea``) for each river segment based on river network topology.

The function accumulates local contributing areas following the downstream connectivity of the river network. It is designed for directed acyclic river networks where each river segment has a unique downstream connection.

Parameters
^^^^^^^^^^

``riv``
    River network table represented as a pandas DataFrame.

``mapping``
    Dictionary defining the column mapping:

    - ``id``: Unique river segment identifier.
    - ``next_id``: Downstream river segment identifier.
    - ``unitarea``: Local contributing area associated with each river segment.

    Default mapping:

    ::

        {
            "id": "COMID",
            "next_id": "NextDownCOMID",
            "unitarea": "unitarea"
        }

``out_col``
    Name of the output column containing the calculated upstream contributing area. Default is ``"uparea"``.

Returns
^^^^^^^

``pandas.DataFrame``
    A copy of the input river network with the calculated upstream contributing area stored in ``out_col``.


Notes
^^^^^

- Existing columns with the same name as ``out_col`` are removed and recalculated.
- Downstream identifiers that do not exist within the provided river network are treated as terminal segments.
- Negative downstream identifiers (e.g., ``-9999``) are interpreted as no downstream connection.


Example
^^^^^^^

::
    
    from riverlakenetwork import Utility

    rivers = Utility.compute_uparea(
        rivers,
        mapping={
            "id": "COMID",
            "next_id": "NextDownCOMID",
            "unitarea": "unitarea"
        },
        out_col="uparea"
    )



add_immediate_upstream
~~~~~~~~~~~~~~~~~~~~~~

.. method:: Utility.add_immediate_upstream(df, mapping={"id": "COMID", "next_id": "NextDownCOMID"})

Add immediate upstream connectivity information to a river network table.

This function identifies all directly connected upstream river segments for each river segment and adds this information to the input DataFrame. The river network is represented as a directed graph where edges describe the connectivity between upstream and downstream segments.

The function creates connectivity attributes that describe the number and identity of immediately upstream segments.

Parameters
^^^^^^^^^^

``df``
    River network attribute table containing river segment identifiers and downstream connectivity information.

``mapping``
    Dictionary defining the column mapping:

    - ``id``: Unique river segment identifier.
    - ``next_id``: Downstream river segment identifier.

    Default mapping:

    ::

        {
            "id": "COMID",
            "next_id": "NextDownCOMID"
        }


Returns
^^^^^^^

``pandas.DataFrame``
    A copy of the input river network with additional upstream connectivity columns:

    - ``maxup``: Number of immediate upstream river segments.
    - ``up1``, ``up2``, ..., ``upN``: Identifiers of immediate upstream river segments.


Notes
^^^^^

- Existing upstream connectivity columns (``maxup``, ``up1``, ``up2``, ...) are removed before recalculation.
- Downstream identifiers with negative values are treated as terminal segments.
- First-order river segments have ``maxup = 0`` because they do not receive flow from upstream segments.
- The ordering of upstream segments follows the graph traversal order and is not guaranteed to represent a specific spatial order.


Example
^^^^^^^

::

    from riverlakenetwork import Utility

    rivers = Utility.add_immediate_upstream(
        rivers,
        mapping={
            "id": "COMID",
            "next_id": "NextDownCOMID"
        }
    )