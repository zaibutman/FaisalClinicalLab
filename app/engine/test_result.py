"""Laboratory test result data model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TestResult:
    """A single laboratory test result."""

    test_id: str
    test_name: str
    test_type: str
    result: Any
    unit: str = ""
    reference_range: str = ""
    flag: str = ""
    comment: str = ""

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "result": self.result,
            "unit": self.unit,
            "reference_range": self.reference_range,
            "flag": self.flag,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestResult:
        return cls(
            test_id=data.get("test_id", ""),
            test_name=data.get("test_name", ""),
            test_type=data.get("test_type", ""),
            result=data.get("result"),
            unit=data.get("unit", ""),
            reference_range=data.get("reference_range", ""),
            flag=data.get("flag", ""),
            comment=data.get("comment", ""),
        )
