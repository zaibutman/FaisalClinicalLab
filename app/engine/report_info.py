"""Report metadata data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReportInfo:
    """Report identification and timestamps."""

    report_id: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReportInfo:
        return cls(
            report_id=data.get("report_id", ""),
            created_at=data.get("created_at", ""),
        )
