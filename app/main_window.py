"""Main application window for Faisal Clinical Laboratory.

Defines :class:`MainWindow`, the top-level QMainWindow that lays out the
four primary sections of the application shell. This module builds layout
and containers only -- no business logic, data handling, or interactive
behavior is implemented at this stage (Version 0.1.0).
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.dialogs.report_history_dialog import ReportHistoryDialog
from app.dialogs.report_preview_dialog import ReportPreviewDialog
from app.dialogs.settings_dialog import SettingsDialog
from app.engine.lab_report import LabReport
from app.engine.medical_knowledge import MedicalKnowledge
from app.engine.package_resolver import PackageResolver
from app.engine.reference_engine import ReferenceEngine
from app.engine.report_builder import ReportBuilder
from app.engine.report_history import ReportHistory
from app.engine.report_storage import ReportStorage
from app.engine.settings_manager import SettingsManager
from app.patient_panel import PatientPanel
from app.printing.pdf_generator import PDFGenerator
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
        # Persists a LabReport to disk as JSON (Task 012A).
        self._report_storage = ReportStorage()
        # The most recently opened report becomes the current report (Task 012B).
        self._current_report: LabReport | None = None

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
        return self._report_builder.build(
            patient_data, result_widgets, report_id=self._active_report_id()
        )

    def _active_report_id(self) -> str:
        """Return the report id to stamp when building the current report.

        Re-uses the id of the report already loaded/saved in this session
        (:attr:`_current_report`) so that re-saving, previewing, or printing
        never mints a new number. Only a brand-new composition (no current
        report) gets the next id from the settings sequence -- and even then the
        counter is not advanced until the save actually succeeds.
        """
        if self._current_report is not None:
            return self._current_report.report_info.report_id
        return self._report_builder.next_report_id()

    def preview_report(self) -> None:
        """Build the current report, render it to a temp PDF, and preview it.

        Reuses :meth:`build_report` and the existing :class:`PDFGenerator`. The
        PDF is written to a private temporary file that is deleted once the
        preview dialog closes -- no orphan files are left behind. This method
        opens no save or print dialogs; the dialog's Print/Save buttons only
        emit signals (Task 011B).
        """
        tmp_path: Path | None = None
        try:
            report = self.build_report()

            handle = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            handle.close()
            tmp_path = Path(handle.name)

            PDFGenerator(self._settings_manager).generate(report, tmp_path)

            logger.info("Preview opened")
            dialog = ReportPreviewDialog(tmp_path, self)
            dialog.exec()
            logger.info("Preview closed")
        except Exception as exc:
            logger.warning("Preview failed: %s", exc)
        finally:
            self._delete_temp_pdf(tmp_path)

    @staticmethod
    def _delete_temp_pdf(tmp_path: Path | None) -> None:
        """Remove the temporary preview PDF, ignoring any failure."""
        if tmp_path is None:
            return
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    def save_report(self) -> Path | None:
        """Build the current report and save it to disk as JSON.

        Reuses :meth:`build_report` and the existing :class:`ReportStorage`
        (which delegates to ``LabReport.to_json``). Opens a Save dialog
        defaulting to ``reports/`` with a generated filename. Returns the
        written path, or ``None`` if the user cancels. Never raises -- any
        filesystem error is reported via a message box.

        Report numbering is automatic: a brand-new report is stamped with the
        next id in the settings sequence, and the counter is advanced *only*
        after the file is written successfully. Re-saving an already-numbered
        report reuses its id and never advances the counter.
        """
        # A brand-new composition has no current report; re-saving does.
        is_new_report = self._current_report is None
        report = self.build_report()
        if is_new_report:
            logger.info("Report number assigned")

        default_dir = self._report_storage.reports_dir
        default_dir.mkdir(parents=True, exist_ok=True)
        default_name = self._report_storage.create_filename(report)
        default_path = str(default_dir / default_name)

        logger.info("Save dialog opened")
        selected, _filter = QFileDialog.getSaveFileName(
            self, "Save Report", default_path, "JSON Files (*.json)"
        )
        if not selected:
            logger.info("Save cancelled")
            return None

        path = Path(selected)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")

        try:
            saved = self._report_storage.save(report, path)
        except (PermissionError, OSError) as exc:
            logger.warning("Save failed: %s", exc)
            QMessageBox.critical(
                self, "Save Report", f"The report could not be saved:\n{exc}"
            )
            return None
        except Exception as exc:  # never crash on an unexpected error
            logger.warning("Save failed: %s", exc)
            QMessageBox.critical(
                self, "Save Report", f"An unexpected error occurred:\n{exc}"
            )
            return None

        logger.info("Report saved: %s", saved.name)

        # Save succeeded: this report is now the current report, so a later
        # re-save reuses its id. Only a newly-numbered report advances the
        # counter -- and only now, after a confirmed write, so a failed or
        # cancelled save can never skip or duplicate a number.
        self._current_report = report
        if is_new_report:
            self._advance_report_counter()

        QMessageBox.information(
            self, "Save Report", f"Report saved successfully:\n{saved}"
        )
        return saved

    def _advance_report_counter(self) -> None:
        """Persist the next report number after a successful new-report save.

        Stores ``report_counter`` as the number just used (the report id was
        formed from ``counter + 1``), so the next new report gets the following
        number. Goes through the shared :class:`SettingsManager` -- the single
        source of truth -- and never skips or reuses a value.
        """
        try:
            counter = int(self._settings_manager.get("report_counter", 0))
        except (TypeError, ValueError):
            counter = 0
        self._settings_manager.set("report_counter", counter + 1)
        self._settings_manager.save()
        logger.info("Report number advanced")

    def open_report(self) -> LabReport | None:
        """Open a saved report JSON and restore it into the application.

        Opens a file dialog (defaulting to ``reports/``), loads the chosen file
        via :class:`ReportStorage`, and rebuilds the UI through
        :meth:`restore_report`. Returns the loaded report, or ``None`` on
        cancel or error. Never raises -- failures are shown via a message box.
        """
        default_dir = self._report_storage.reports_dir
        start = str(default_dir) if default_dir.exists() else ""

        logger.info("Open dialog opened")
        selected, _filter = QFileDialog.getOpenFileName(
            self, "Open Report", start, "JSON Files (*.json)"
        )
        if not selected:
            logger.info("Open cancelled")
            return None

        try:
            report = self._report_storage.load(selected)
            self.restore_report(report)
        except (FileNotFoundError, OSError) as exc:
            logger.warning("Open failed: %s", exc)
            QMessageBox.critical(
                self, "Open Report", f"The file could not be opened:\n{exc}"
            )
            return None
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Open failed: %s", exc)
            QMessageBox.critical(
                self, "Open Report", f"The file is not a valid report:\n{exc}"
            )
            return None
        except Exception as exc:  # never crash on an unexpected error
            logger.warning("Open failed: %s", exc)
            QMessageBox.critical(
                self, "Open Report", f"An unexpected error occurred:\n{exc}"
            )
            return None

        logger.info("Report loaded")
        return report

    def open_report_history(self) -> LabReport | None:
        """Browse saved reports and open the one the user selects.

        Discovers every saved report via :class:`ReportHistory` (recursive,
        metadata only), shows :class:`ReportHistoryDialog`, and -- on selection
        -- loads the chosen file through the existing :class:`ReportStorage` and
        rebuilds the UI via :meth:`restore_report`. No loading or restoration
        logic is duplicated here. Returns the loaded report, or ``None`` on
        cancel or error. Never raises.
        """
        history = ReportHistory(storage=self._report_storage)
        dialog = ReportHistoryDialog(history.get_reports(), self)

        logger.info("History opened")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            logger.info("History cancelled")
            return None

        filepath = dialog.selected_filepath()
        if not filepath:
            logger.info("History cancelled")
            return None

        try:
            report = self._report_storage.load(filepath)
            self.restore_report(report)
        except Exception as exc:  # never crash on a bad/removed report
            QMessageBox.critical(
                self, "Report History", f"The report could not be opened:\n{exc}"
            )
            return None

        logger.info("History loaded")
        return report

    def open_settings(self) -> None:
        """Open the Laboratory Settings dialog and reload settings on save.

        The dialog edits and persists through the shared
        :class:`SettingsManager` (the single source of truth). On accept, the
        manager is reloaded so collaborators that read it -- notably the report
        builder and PDF generator -- immediately see the new values. This method
        builds no report and prints nothing.
        """
        dialog = SettingsDialog(self._settings_manager, self)

        logger.info("Settings opened")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._settings_manager.load()
            logger.info("Settings updated")
        else:
            logger.info("Settings cancelled")

    def restore_report(self, report: LabReport) -> None:
        """Rebuild the entire UI from a loaded :class:`LabReport`.

        This is the single restoration pipeline -- future features (Recent
        Reports, History, Auto Recovery, Database) must reuse it. The report is
        the sole source of truth: patient fields and every result widget are
        populated verbatim from it. No reference flagging, unit lookup, or
        package expansion happens here -- nothing is recalculated.
        """
        # Patient fields -- restored exactly as stored.
        self.patient_panel.set_patient_data(report.patient.to_dict())

        # Start from a clean results area and sidebar selection.
        self._clear_result_area()
        self.test_panel.clear_selection()

        # Recreate each widget in the stored order and fill in its values.
        for test_result in report.test_results:
            widget = self._create_widget_from_result(test_result)
            if widget is None:
                logger.info(
                    "No widget for type '%s' (test %s); skipped during restore",
                    test_result.test_type, test_result.test_id,
                )
                continue
            self._restore_widget_value(widget, test_result)
            widget.removed.connect(self._on_widget_removed)
            self.result_area.add_widget(widget)

        # The loaded report becomes the current report.
        self._current_report = report

    # ── Restoration helpers (report is the only source of truth) ──────

    def _clear_result_area(self) -> None:
        """Remove every widget currently in the results area."""
        for test_id in list(self.result_area._widgets.keys()):
            self.result_area.remove_widget(test_id)

    def _create_widget_from_result(self, test_result):
        """Build a result widget for a stored ``TestResult`` via the factory.

        The widget definition is assembled from the report itself (not the
        catalog), so a report opens even if the test catalog has since changed.
        Returns ``None`` for types the factory does not handle.
        """
        definition = {
            "id": test_result.test_id,
            "name": test_result.test_name,
            "type": test_result.test_type,
            "unit": test_result.unit,
            "reference_range": self._range_display(test_result.reference_range),
        }
        return create_widget(definition)

    def _restore_widget_value(self, widget, test_result) -> None:
        """Populate ``widget`` from ``test_result.result`` exactly as stored.

        Dispatches on the stored test type. The result is written straight into
        each widget's inputs -- no value is recomputed or re-flagged.
        """
        test_type = test_result.test_type
        result = test_result.result

        if test_type == "numeric":
            widget.result_edit.setText(self._as_text(result))
        elif test_type == "dropdown":
            self._select_combo_text(widget.result_combo, result)
        elif test_type == "blood_group":
            self._select_combo_text(widget.group_combo, result)
        elif test_type in ("cbc", "semen", "sbr"):
            if isinstance(result, dict):
                for label, value in result.items():
                    edit = widget._fields.get(label)
                    if edit is not None:
                        edit.setText(self._as_text(value))
        elif test_type == "urine":
            if isinstance(result, dict):
                for section, fields in result.items():
                    section_fields = widget._fields.get(section)
                    if isinstance(fields, dict) and isinstance(section_fields, dict):
                        for label, value in fields.items():
                            edit = section_fields.get(label)
                            if edit is not None:
                                edit.setText(self._as_text(value))

    @staticmethod
    def _select_combo_text(combo, value) -> None:
        """Select ``value`` in ``combo``, adding it if not already present."""
        text = "" if value is None else str(value)
        index = combo.findText(text, Qt.MatchFlag.MatchExactly)
        if index < 0:
            combo.addItem(text)
            index = combo.findText(text, Qt.MatchFlag.MatchExactly)
        combo.setCurrentIndex(index)

    @staticmethod
    def _as_text(value) -> str:
        """Render a stored scalar value as widget text."""
        return "" if value is None else str(value)

    @staticmethod
    def _range_display(reference_range) -> str:
        """Reduce a stored reference range to a display string for a widget."""
        if isinstance(reference_range, str):
            return reference_range
        if isinstance(reference_range, (list, tuple)):
            for variant in reference_range:
                if isinstance(variant, str) and variant.strip():
                    return variant
        return ""

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
