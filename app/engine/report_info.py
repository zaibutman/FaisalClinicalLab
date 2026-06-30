"""Report metadata data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReportInfo:
    """Report identification and timestamps."""

    report_id: str
    created_at: str
    printed_at: str = ""
    status: str = "Pending"
    remarks: str = ""
    technician: str = ""

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "printed_at": self.printed_at,
            "status": self.status,
            "remarks": self.remarks,
            "technician": self.technician,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReportInfo:
        return cls(
            report_id=data.get("report_id", ""),
            created_at=data.get("created_at", ""),
            printed_at=data.get("printed_at", ""),
            status=data.get("status", "Pending"),
            remarks=data.get("remarks", ""),
            technician=data.get("technician", ""),
        )
