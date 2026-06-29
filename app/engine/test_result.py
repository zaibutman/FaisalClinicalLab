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

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TestResult:
        return cls(
            test_id=data.get("test_id", ""),
            test_name=data.get("test_name", ""),
            test_type=data.get("test_type", ""),
            result=data.get("result"),
        )
