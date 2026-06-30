"""Patient information data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PatientInfo:
    """Patient demographics and identification."""

    name: str
    gender: str
    doctor: str
    date: str
    age: str = ""
    phone: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "doctor": self.doctor,
            "date": self.date,
            "age": self.age,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PatientInfo:
        return cls(
            name=data.get("name", ""),
            gender=data.get("gender", ""),
            doctor=data.get("doctor", ""),
            date=data.get("date", ""),
            age=data.get("age", ""),
            phone=data.get("phone", ""),
        )
