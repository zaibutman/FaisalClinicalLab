"""Base class for laboratory result widgets.

Every result widget shown in the Laboratory Results area derives from
:class:`BaseTestWidget`. The base provides the common chrome -- a titled
card with a remove (``✕``) button and a ``removed`` signal -- and defines
the :meth:`collect_data` contract that the future ReportBuilder will rely
on exclusively. Subclasses build their own input fields and implement
:meth:`collect_data`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.styles import BORDER, ERROR, PANEL, PRIMARY


class BaseTestWidget(QFrame):
    """A titled result card with a remove button.

    Attributes:
        test_id:   stable test id (assigned by the widget factory).
        test_name: human-readable test name shown as the card title.

    Signals:
        removed(str): emitted with ``test_id`` when the ✕ button is clicked.
    """

    removed = Signal(str)

    def __init__(self, test_name: str, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.test_id: str = ""  # set by the factory after construction
        self.test_name: str = test_name

        self.setObjectName("ResultCard")
        self.setStyleSheet(
            f"QFrame#ResultCard {{ background:{PANEL}; border:1px solid {BORDER};"
            f" border-radius:8px; }}"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 8)
        outer.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel(test_name)
        title.setStyleSheet(
            f"font-weight:700; font-size:15px; color:{PRIMARY}; background:transparent;"
        )
        header.addWidget(title)
        header.addStretch(1)

        self._remove_btn = QPushButton("✕")  # ✕
        self._remove_btn.setFixedSize(26, 24)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setToolTip("Remove this test")
        self._remove_btn.setStyleSheet(
            f"QPushButton {{ background:{ERROR}; color:white; border:none;"
            f" border-radius:4px; padding:0; font-weight:700; }}"
            f" QPushButton:hover {{ background:#B71C1C; }}"
        )
        self._remove_btn.clicked.connect(self._on_remove)
        header.addWidget(self._remove_btn)
        outer.addLayout(header)

        # Subclasses add their fields to this layout.
        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(4)
        outer.addLayout(self.body_layout)

    def _on_remove(self) -> None:
        """Emit :attr:`removed` so the owner can detach this widget."""
        self.removed.emit(self.test_id)

    def collect_data(self) -> dict:
        """Return this widget's collected data.

        Must be overridden by subclasses. The returned dict always carries
        at least ``type``, ``name`` and ``result`` keys.
        """
        raise NotImplementedError
