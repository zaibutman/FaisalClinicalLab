"""Report builder for Faisal Clinical Laboratory.

Defines :class:`ReportBuilder`, the business-layer step that converts the
current application state -- the patient fields and the live result widgets --
into a single, complete :class:`~app.engine.lab_report.LabReport` object.

The builder sits between the UI and the data model::

    UI -> Widgets -> MedicalKnowledge -> ReferenceEngine -> ReportBuilder -> LabReport

It is deliberately ignorant of presentation: it knows nothing about PDFs,
printing, saving, or history. Its sole responsibility is construction. It
mirrors the conventions of the surrounding engine modules:

* It **never invents medical values.** Units and reference ranges come only
  from :class:`~app.engine.medical_knowledge.MedicalKnowledge`; laboratory
  details come only from :class:`~app.engine.settings_manager.SettingsManager`.
  Nothing is hardcoded.
* It **trusts the widget.** Each widget's :meth:`collect_data` is the sole
  authority for that test's entered result -- the builder never reaches into a
  widget's input fields.
* It **never flattens or converts** a widget's result. CBC, urine, semen, and
  SBR results are stored exactly as the widget returns them.

This module imports no PySide6 and no UI code, so it can be exercised headless.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.engine.lab_report import LabReport
from app.engine.patient import PatientInfo
from app.engine.report_info import ReportInfo
from app.engine.test_result import TestResult

if TYPE_CHECKING:  # type-hint only; avoids any runtime coupling
    from app.engine.medical_knowledge import MedicalKnowledge
    from app.engine.reference_engine import ReferenceEngine
    from app.engine.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# Maps the SBR widget's field labels (as returned by collect_data) to the
# component keys the ReferenceEngine understands. Keying the resulting flags by
# the widget's own labels lets a consumer line up result[label] with
# flag[label] without re-deriving anything.
_SBR_COMPONENTS: dict[str, str] = {
    "Total Bilirubin": "SBR(TOTAL)",
    "Direct Bilirubin": "SBR(DIRECT)",
    "Indirect Bilirubin": "SBR(INDIRECT)",
}

# Result types the engine can flag. Everything else (cbc, blood_group,
# dropdown, urine, semen) has no numeric reference logic, so its flag is left
# empty rather than invented.
_NUMERIC_TYPE: str = "numeric"
_SBR_TYPE: str = "sbr"


class ReportBuilder:
    """Assemble a :class:`LabReport` from patient data and result widgets.

    The three collaborators are injected so the builder can be unit-tested
    headless and so it owns no I/O of its own:

    * ``settings_manager`` -- the only source of laboratory details and the
      report-id sequence.
    * ``medical_knowledge`` -- the only source of units and reference ranges.
    * ``reference_engine`` -- decides High/Low/Normal flags for numeric results.
    """

    def __init__(
        self,
        settings_manager: SettingsManager,
        medical_knowledge: MedicalKnowledge,
        reference_engine: ReferenceEngine,
    ) -> None:
        self._settings_manager = settings_manager
        self._medical_knowledge = medical_knowledge
        self._reference_engine = reference_engine

    # ── Public API ────────────────────────────────────────────────────

    def build(
        self,
        patient_data: dict,
        result_widgets: list,
        report_id: str | None = None,
    ) -> LabReport:
        """Build a complete :class:`LabReport` from the current state.

        Args:
            patient_data: The patient fields (e.g. from ``PatientPanel``).
            result_widgets: The live result widgets, in display order. Each
                must expose ``test_id`` and a ``collect_data()`` method.
            report_id: The report id to stamp on the report. When ``None`` a
                fresh id is derived from the settings sequence via
                :meth:`next_report_id`. The caller (MainWindow) passes an
                existing id when re-saving an already-numbered report so no new
                number is assigned. The counter is never advanced here.

        Returns:
            A fully populated :class:`LabReport`. No files are written, nothing
            is printed, and no widget is modified.
        """
        patient = PatientInfo.from_dict(patient_data)
        laboratory = self._settings_manager.get_laboratory_info()
        report_info = self._build_report_info(report_id)

        test_results = [
            self._build_test_result(widget, patient.gender)
            for widget in result_widgets
        ]

        logger.info("Report built: %d test(s)", len(test_results))
        return LabReport(
            patient=patient,
            laboratory=laboratory,
            report_info=report_info,
            test_results=test_results,
        )

    # ── Report metadata ───────────────────────────────────────────────

    def _build_report_info(self, report_id: str | None = None) -> ReportInfo:
        """Build the :class:`ReportInfo`, using ``report_id`` when supplied.

        A ``None`` id means a brand-new report, so the next id in the settings
        sequence is derived. A supplied id is reused verbatim (re-saving an
        already-numbered report).
        """
        return ReportInfo(
            report_id=report_id or self.next_report_id(),
            created_at=self._now(),
            printed_at=None,
            status="Pending",
            remarks="",
            technician="",
        )

    def next_report_id(self) -> str:
        """Format the next report id from the current settings sequence.

        This is the single authority for the report-id format. It uses the
        existing ``report_prefix`` / ``report_counter`` settings. The counter is
        read but not advanced or persisted here -- advancing happens only in
        MainWindow after a successful save -- so the value reflects the next
        report to be created.
        """
        prefix = str(self._settings_manager.get("report_prefix", "RPT"))
        try:
            counter = int(self._settings_manager.get("report_counter", 0))
        except (TypeError, ValueError):
            counter = 0
        return f"{prefix}-{counter + 1:04d}"

    @staticmethod
    def _now() -> str:
        """Return the current local timestamp as ``YYYY-MM-DD HH:MM:SS``."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Test results ──────────────────────────────────────────────────

    def _build_test_result(self, widget: Any, gender: str) -> TestResult:
        """Convert one result widget into a :class:`TestResult`.

        The widget's ``collect_data()`` is the sole authority for the entered
        result; ``test_id`` is read from the widget's public identity. Units
        and reference ranges come from the medical knowledge database, and the
        flag from the reference engine.
        """
        data = widget.collect_data()
        test_id = widget.test_id
        test_type = data.get("type", "")
        result = data.get("result")

        return TestResult(
            test_id=test_id,
            test_name=data.get("name", ""),
            test_type=test_type,
            result=result,  # stored verbatim; never flattened or converted
            unit=self._medical_knowledge.get_unit(test_id) or "",
            reference_range=self._reference_range_for(test_id),
            flag=self._flag_for(test_id, test_type, result, gender),
            comment="",
        )

    def _reference_range_for(self, test_id: str) -> Any:
        """Return the catalog reference range for ``test_id`` (``""`` if none).

        The value is returned in the catalog's own shape -- a list of variant
        strings, or a ``{component: [...]}`` mapping for SBR -- so nothing is
        invented or collapsed.
        """
        raw = self._medical_knowledge.get_reference_range(test_id)
        return raw if raw is not None else ""

    def _flag_for(
        self,
        test_id: str,
        test_type: str,
        result: Any,
        gender: str,
    ) -> Any:
        """Return the reference flag(s) for a result.

        Numeric tests yield a single flag string; SBR yields a per-component
        mapping. Every other type leaves the flag empty -- the builder never
        invents flag logic for qualitative or panel results.
        """
        if test_type == _NUMERIC_TYPE:
            return self._reference_engine.evaluate(test_id, result, sex=gender)
        if test_type == _SBR_TYPE:
            return self._sbr_flags(test_id, result, gender)
        return ""

    def _sbr_flags(self, test_id: str, result: Any, gender: str) -> Any:
        """Flag each SBR component individually, keyed by the widget's labels.

        Returns ``""`` if the widget did not return a component mapping. Each
        component is evaluated against its own catalog range; empty entries
        evaluate to an empty flag rather than a fabricated one.
        """
        if not isinstance(result, dict):
            return ""

        flags: dict[str, str] = {}
        for label, value in result.items():
            component = _SBR_COMPONENTS.get(label)
            if component is None:
                continue
            flags[label] = self._reference_engine.evaluate(
                test_id, value, sex=gender, component=component
            )
        return flags
