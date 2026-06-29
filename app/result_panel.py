"""Laboratory Results area for Faisal Clinical Laboratory.

Defines :class:`ResultArea`, a vertically scrollable container that holds
the result widgets created by the widget factory. It shows a centered
"No tests added." placeholder when empty, inserts widgets in click order,
and tracks them by test id so duplicates can be rejected and individual
widgets removed.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.widgets.base_test_widget import BaseTestWidget

logger = logging.getLogger(__name__)

_PLACEHOLDER_TEXT: str = "No tests added."


class ResultArea(QWidget):
    """Scrollable, ordered collection of result widgets keyed by test id."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Insertion-ordered map of test_id -> widget (dict preserves order).
        self._widgets: dict[str, BaseTestWidget] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(10)
        self.scroll.setWidget(self._content)
        layout.addWidget(self.scroll)

        self._placeholder = QLabel(_PLACEHOLDER_TEXT)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._rebuild()

    # ── Public API ──────────────────────────────────────────────────
    def contains(self, test_id: str) -> bool:
        """Return True if a widget for ``test_id`` is already present."""
        return test_id in self._widgets

    def add_widget(self, widget: BaseTestWidget) -> bool:
        """Append ``widget`` to the area.

        Returns False (and does nothing) if a widget with the same
        ``test_id`` already exists -- duplicate clicks are ignored.
        """
        if widget.test_id in self._widgets:
            return False
        self._widgets[widget.test_id] = widget
        self._rebuild()
        return True

    def remove_widget(self, test_id: str) -> None:
        """Remove the widget for ``test_id``; restore placeholder if empty."""
        widget = self._widgets.pop(test_id, None)
        if widget is None:
            return
        widget.setParent(None)
        widget.deleteLater()
        self._rebuild()

    def widget_count(self) -> int:
        """Return the number of result widgets currently shown."""
        return len(self._widgets)

    # ── Internals ───────────────────────────────────────────────────
    def _rebuild(self) -> None:
        """Re-lay out the content: placeholder when empty, else widgets."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            taken = item.widget()
            if taken is not None:
                taken.setParent(None)

        if not self._widgets:
            self._content_layout.addStretch(1)
            self._content_layout.addWidget(
                self._placeholder, 0, Qt.AlignmentFlag.AlignHCenter
            )
            self._content_layout.addStretch(1)
            self._placeholder.show()
        else:
            for widget in self._widgets.values():
                self._content_layout.addWidget(widget)
                widget.show()
            self._content_layout.addStretch(1)
