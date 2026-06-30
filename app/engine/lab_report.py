"""Laboratory report aggregate data model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.engine.laboratory import LaboratoryInfo
from app.engine.patient import PatientInfo
from app.engine.report_info import ReportInfo
from app.engine.test_result import TestResult


@dataclass
class LabReport:
    """Complete laboratory report aggregating all report components."""

    patient: PatientInfo
    laboratory: LaboratoryInfo
    report_info: ReportInfo
    test_results: list[TestResult]

    def to_dict(self) -> dict:
        return {
            "patient": self.patient.to_dict(),
            "laboratory": self.laboratory.to_dict(),
            "report_info": self.report_info.to_dict(),
            "test_results": [t.to_dict() for t in self.test_results],
        }

    @classmethod
    def from_dict(cls, data: dict) -> LabReport:
        return cls(
            patient=PatientInfo.from_dict(data.get("patient", {})),
            laboratory=LaboratoryInfo.from_dict(data.get("laboratory", {})),
            report_info=ReportInfo.from_dict(data.get("report_info", {})),
            test_results=[
                TestResult.from_dict(t) for t in data.get("test_results", [])
            ],
        )

    def to_json(self, filepath) -> None:
        """Serialize this report to a JSON file (UTF-8, indented)."""
        path = Path(filepath)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=4, ensure_ascii=False)

    @classmethod
    def from_json(cls, filepath) -> LabReport:
        """Load a report from a JSON file (UTF-8)."""
        path = Path(filepath)
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)
