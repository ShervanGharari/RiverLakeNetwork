Examples
========

Example 1
---------

The first example demonstrates the use of ``BurnLakes`` for processing
**multi-segment lakes and reservoirs only**, without including
single-segment lakes and reservoirs. All other input parameters are set
to their default values.

.. code-block:: python

    model = BurnLakes(
        InputData=InputData,
    )


Example 2
---------

This example demonstrates the use of ``BurnLakes`` for processing
multi-segment lakes and reservoirs only, while enforcing that
**each river segment intersects at least one lake or reservoir**.
This ensures that no segment directly connects an upstream lake
to a downstream lake without intersection.

.. code-block:: python

    model = BurnLakes(
        InputData=InputData,
        EnforceOneLakePerSegment=True,
    )


Example 3
---------

This example enables the processing of **single-segment lakes and reservoirs**
in addition to multi-segment systems.

.. code-block:: python

    model = BurnLakes(
        InputData=InputData,
        SingleSegmentProcessing=True,
    )


Example 4
---------

This example enables single-segment lake processing and specifies
**custom upstream/downstream positioning** for selected lake IDs.

Lakes with ``None`` values will be assigned positions based on the
``SingleSegmentGlobalPosition`` setting (which is "down" by default).

.. code-block:: python

    model = BurnLakes(
        InputData=InputData,
        SingleSegmentProcessing=True,
        SingleSegmentIdPosition={
            83279: "up",
            84896: "up",
            87073: None,  # assigned using SingleSegmentGlobalPosition
            86960: None,
        },
    )


Example 5
---------

This example enables single-segment processing but restricts it to a
specified set of lake IDs. The global position is set to ``"up"``.

.. code-block:: python

    model = BurnLakes(
        InputData=InputData,
        SingleSegmentProcessing=True,
        SingleSegmentIdPosition={
            83279: "up",
            84896: "up",
            87073: None,  # assigned using SingleSegmentGlobalPosition
            86960: None,
        },
        SingleSegmentRestrictToIdPosition=True,
        SingleSegmentGlobalPosition="up",
    )