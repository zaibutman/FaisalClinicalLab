"""Laboratory report aggregate data model."""

from __future__ import annotations

from dataclasses import dataclass

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
