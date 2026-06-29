"""Main application window for Faisal Clinical Laboratory.

Defines :class:`MainWindow`, the top-level QMainWindow that lays out the
four primary sections of the application shell. This module builds layout
and containers only -- no business logic, data handling, or interactive
behavior is implemented at this stage (Version 0.1.0).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.patient_panel import PatientPanel
from app.test_panel import TestPanel
from app.version import get_window_title

logger = logging.getLogger(__name__)

# Fixed shell geometry for Version 0.1.0.
_WINDOW_WIDTH: int = 1400
_WINDOW_HEIGHT: int = 850


class MainWindow(QMainWindow):
    """Top-level window hosting the application's four shell sections.

    Layout overview::

        ┌────────────────────────────────────────────┐
        │ Patient Information (top)                    │
        ├──────────────┬─────────────────────────────┤
        │ Medical      │ Laboratory Results           │
        │ Tests (left) │ (center)                     │
        ├──────────────┴─────────────────────────────┤
        │ Actions (bottom)                             │
        └────────────────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(get_window_title())
        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setMinimumSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)

        self._build_ui()
        logger.info("MainWindow initialized")

    def _build_ui(self) -> None:
        """Assemble the central widget and the four shell sections."""
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Top: Patient Information (full width).
        root_layout.addWidget(self._build_patient_section())

        # Middle: Medical Tests (left) + Laboratory Results (center).
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(12)
        middle_layout.addWidget(self._build_tests_section(), stretch=1)
        middle_layout.addWidget(self._build_results_section(), stretch=3)
        root_layout.addLayout(middle_layout, stretch=1)

        # Bottom: Actions (full width).
        root_layout.addWidget(self._build_actions_section())

    def _build_patient_section(self) -> QGroupBox:
        """Build the top 'Patient Information' container hosting PatientPanel."""
        group = QGroupBox("Patient Information")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)

        self.patient_panel = PatientPanel(group)
        layout.addWidget(self.patient_panel)

        return group

    def _build_tests_section(self) -> QGroupBox:
        """Build the left 'Medical Tests' container hosting TestPanel."""
        group = QGroupBox("Medical Tests")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)

        self.test_panel = TestPanel(group)
        layout.addWidget(self.test_panel)

        return group

    def _build_results_section(self) -> QGroupBox:
        """Build the center 'Laboratory Results' container.

        Shows a placeholder label until tests are added in a later task.
        """
        group = QGroupBox("Laboratory Results")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)

        placeholder = QLabel("No tests added.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)

        return group

    def _build_actions_section(self) -> QGroupBox:
        """Build the bottom 'Actions' container (empty for now)."""
        group = QGroupBox("Actions")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        return group

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        """Log a clean shutdown when the window is closed."""
        logger.info("MainWindow closed")
        super().closeEvent(event)
