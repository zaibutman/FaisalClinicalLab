"""Widget factory: map a test definition to its result widget.

The factory is the single place that knows how to turn a test definition
(loaded from ``data/tests.json``) into a concrete result widget. Dispatch
is driven entirely by ``test_definition["type"]`` so new tests are added
by editing JSON, not this code. ``package`` types return ``None`` until
package expansion is implemented in a later task.
"""

from __future__ import annotations

import logging

from app.widgets.base_test_widget import BaseTestWidget
from app.widgets.blood_group_widget import BloodGroupWidget
from app.widgets.cbc_widget import CBCWidget
from app.widgets.dropdown_widget import DropdownTestWidget
from app.widgets.numeric_widget import NumericTestWidget
from app.widgets.sbr_widget import SBRWidget
from app.widgets.semen_widget import SemenWidget
from app.widgets.urine_widget import UrineWidget

logger = logging.getLogger(__name__)


def create_widget(test_definition: dict) -> BaseTestWidget | None:
    """Return the result widget for ``test_definition``, or ``None``.

    ``None`` is returned for ``package`` types (not yet implemented) and
    for any unrecognised type. The created widget's ``test_id`` is set
    from the definition so its ``removed`` signal can identify it.
    """
    test_type = test_definition.get("type", "")
    name = test_definition.get("name", "")

    if test_type == "numeric":
        widget: BaseTestWidget = NumericTestWidget(
            name,
            test_definition.get("unit", ""),
            test_definition.get("reference_range", ""),
        )
    elif test_type == "dropdown":
        widget = DropdownTestWidget(name, test_definition.get("options"))
    elif test_type == "cbc":
        widget = CBCWidget(name)
    elif test_type == "blood_group":
        widget = BloodGroupWidget(name)
    elif test_type == "urine":
        widget = UrineWidget(name)
    elif test_type == "semen":
        widget = SemenWidget(name)
    elif test_type == "sbr":
        widget = SBRWidget(name)
    elif test_type == "package":
        return None  # package expansion not implemented yet
    else:
        logger.warning("Unknown widget type '%s' for test '%s'", test_type, name)
        return None

    widget.test_id = test_definition.get("id", "")
    return widget
