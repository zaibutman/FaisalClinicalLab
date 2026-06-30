"""Laboratory information data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LaboratoryInfo:
    """Laboratory identification and contact details."""

    name: str
    address: str
    phone: str
    email: str = ""
    website: str = ""
    logo: str = ""
    signature: str = ""
    footer: str = ""
    license_number: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "logo": self.logo,
            "signature": self.signature,
            "footer": self.footer,
            "license_number": self.license_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LaboratoryInfo:
        return cls(
            name=data.get("name", ""),
            address=data.get("address", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
            website=data.get("website", ""),
            logo=data.get("logo", ""),
            signature=data.get("signature", ""),
            footer=data.get("footer", ""),
            license_number=data.get("license_number", ""),
        )
