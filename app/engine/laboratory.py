"""Laboratory information data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LaboratoryInfo:
    """Laboratory identification and contact details."""

    name: str
    address: str
    phone: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LaboratoryInfo:
        return cls(
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
        )
