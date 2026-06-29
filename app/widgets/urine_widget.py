"""Urine R/E result widget -- Physical / Chemical / Microscopic sections."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit

from app.styles import PRIMARY
from app.widgets.base_test_widget import BaseTestWidget

# Section -> ordered field names.
_SECTIONS: dict[str, tuple[str, ...]] = {
    "Physical": ("Colour", "Appearance"),
    "Chemical": ("Sugar", "Protein"),
    "Microscopic": ("Pus Cells", "RBCs", "Epithelial Cells"),
}


class UrineWidget(BaseTestWidget):
    """Urine analysis grouped into three sections of simple text fields."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name, parent)
        self._fields: dict[str, dict[str, QLineEdit]] = {}

        for section, labels in _SECTIONS.items():
            header = QLabel(section)
            header.setStyleSheet(
                f"font-weight:700; color:{PRIMARY}; background:transparent;"
            )
            self.body_layout.addWidget(header)

            form = QFormLayout()
            form.setHorizontalSpacing(12)
            form.setVerticalSpacing(6)
            self._fields[section] = {}
            for label in labels:
                edit = QLineEdit()
                self._fields[section][label] = edit
                form.addRow(f"{label}:", edit)
            self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "urine",
            "name": self.test_name,
            "result": {
                section: {label: edit.text().strip() for label, edit in fields.items()}
                for section, fields in self._fields.items()
            },
        }
