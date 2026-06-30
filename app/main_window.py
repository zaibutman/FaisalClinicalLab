"""Main application window for Faisal Clinical Laboratory.

Defines :class:`MainWindow`, the top-level QMainWindow that lays out the
four primary sections of the application shell. This module builds layout
and containers only -- no business logic, data handling, or interactive
behavior is implemented at this stage (Version 0.1.0).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app.engine.lab_report import LabReport
from app.engine.medical_knowledge import MedicalKnowledge
from app.engine.package_resolver import PackageResolver
from app.engine.reference_engine import ReferenceEngine
from app.engine.report_builder import ReportBuilder
from app.engine.settings_manager import SettingsManager
from app.patient_panel import PatientPanel
from app.result_panel import ResultArea
from app.test_panel import TestPanel
from app.version import get_window_title
from app.widgets.widget_factory import create_widget

logger = logging.getLogger(__name__)

# Minimum shell geometry. The window is freely resizable and maximizable
# above this floor -- it is a minimum, not a fixed size.
_MIN_WINDOW_WIDTH: int = 1400
_MIN_WINDOW_HEIGHT: int = 850


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
        self.resize(_MIN_WINDOW_WIDTH, _MIN_WINDOW_HEIGHT)
        self.setMinimumSize(_MIN_WINDOW_WIDTH, _MIN_WINDOW_HEIGHT)

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
        # 2:5 gives the tests sidebar a little more width than a flat 1:3
        # while still letting the results area take the remaining space.
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(14)
        middle_layout.addWidget(self._build_tests_section(), stretch=2)
        middle_layout.addWidget(self._build_results_section(), stretch=5)
        root_layout.addLayout(middle_layout, stretch=1)

        # Bottom: Actions (full width).
        root_layout.addWidget(self._build_actions_section())

        # Resolves package ids -> ordered member test ids (Task 008).
        self._package_resolver = PackageResolver()

        # Business-layer collaborators for assembling a LabReport (Task 010).
        # MedicalKnowledge is shared with the ReferenceEngine so both read the
        # same loaded catalog.
        self._settings_manager = SettingsManager()
        self._medical_knowledge = MedicalKnowledge()
        self._reference_engine = ReferenceEngine(self._medical_knowledge)
        self._report_builder = ReportBuilder(
            self._settings_manager,
            self._medical_knowledge,
            self._reference_engine,
        )

        # Wire test selection -> result widget insertion.
        self.test_panel.test_selected.connect(self._on_test_selected)

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
        """Build the center 'Laboratory Results' container hosting ResultArea."""
        group = QGroupBox("Laboratory Results")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)

        self.result_area = ResultArea(group)
        layout.addWidget(self.result_area)

        return group

    def _build_actions_section(self) -> QGroupBox:
        """Build the bottom 'Actions' container (empty for now).

        Pinned to a fixed height so it never steals vertical space from the
        results area as the window grows.
        """
        group = QGroupBox("Actions")
        group.setFixedHeight(76)
        layout = QHBoxLayout(group)
        layout.setContentsMargins(12, 18, 12, 12)
        return group

    def _on_test_selected(self, test_id: str) -> None:
        """Handle a sidebar click: add a single test, or expand a package.

        A package click resolves to its member tests and adds a widget for
        each one that is not already present (Task 008). A single-test click
        keeps the prior behavior: duplicate clicks are ignored and tests
        with no widget (unknown types) are skipped.
        """
        definition = self.test_panel.get_test(test_id)
        if definition is None:
            logger.warning("No definition found for test id: %s", test_id)
            return

        if definition.get("type") == "package":
            self._on_package_selected(test_id)
            return

        if self.result_area.contains(test_id):
            logger.info("Duplicate test click ignored: %s", test_id)
            return
        if self._add_widget_for(test_id):
            logger.info("Added result widget: %s", test_id)

    def _on_package_selected(self, package_id: str) -> None:
        """Resolve ``package_id`` and add a widget for each missing member.

        Existing widgets are never duplicated and package order is preserved.
        Individual widget creation is intentionally not logged here.
        """
        member_ids = self._package_resolver.resolve(package_id)
        for member_id in member_ids:
            if not self.result_area.contains(member_id):
                self._add_widget_for(member_id)
        logger.info("Package added: %s (%d test(s))", package_id, len(member_ids))

    def _add_widget_for(self, test_id: str) -> bool:
        """Create and insert the result widget for ``test_id``.

        Returns True if a widget was added. Returns False when the test has
        no definition or no widget for its type. Duplicate suppression is the
        caller's responsibility.
        """
        definition = self.test_panel.get_test(test_id)
        if definition is None:
            logger.warning("No definition found for test id: %s", test_id)
            return False

        widget = create_widget(definition)
        if widget is None:
            logger.info(
                "No widget for type '%s' (test %s); skipped",
                definition.get("type"), test_id,
            )
            return False

        widget.removed.connect(self._on_widget_removed)
        return self.result_area.add_widget(widget)

    def build_report(self) -> LabReport:
        """Assemble a :class:`LabReport` from the current application state.

        Collects the patient fields and the live result widgets (in display
        order) and hands them to the :class:`ReportBuilder`. This method only
        builds and returns the report object -- it shows no dialogs and does
        no printing or saving (Task 010).
        """
        patient_data = self.patient_panel.get_patient_data()
        # ResultArea exposes no public iterator yet; read its insertion-ordered
        # map directly to preserve the order tests were added in.
        result_widgets = list(self.result_area._widgets.values())
        return self._report_builder.build(patient_data, result_widgets)

    def _on_widget_removed(self, test_id: str) -> None:
        """Remove the result widget for ``test_id`` from the area."""
        self.result_area.remove_widget(test_id)
        logger.info("Removed result widget: %s", test_id)

    def changeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        """Log maximize / restore transitions (and nothing noisier)."""
        if event.type() == QEvent.Type.WindowStateChange:
            was_maximized = bool(event.oldState() & Qt.WindowState.WindowMaximized)
            if self.isMaximized() and not was_maximized:
                logger.info("Window maximized")
            elif was_maximized and not self.isMaximized() and not self.isMinimized():
                logger.info("Window restored")
        super().changeEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        """Log a clean shutdown when the window is closed."""
        logger.info("MainWindow closed")
        super().closeEvent(event)
