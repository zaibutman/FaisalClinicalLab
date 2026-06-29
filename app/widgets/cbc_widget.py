"""CBC (Blood Complete Picture) result widget -- UI only."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit

from app.widgets.base_test_widget import BaseTestWidget

# Order preserved for display and report output.
_CBC_FIELDS: tuple[str, ...] = (
    "Hemoglobin",
    "TLC",
    "Neutrophils",
    "Lymphocytes",
    "Monocytes",
    "Eosinophils",
    "Basophils",
    "RBC",
    "HCT",
    "MCV",
    "MCH",
    "Platelets",
)


class CBCWidget(BaseTestWidget):
    """Multi-parameter CBC widget. No validation in this task."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name, parent)
        self._fields: dict[str, QLineEdit] = {}

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)
        for label in _CBC_FIELDS:
            edit = QLineEdit()
            self._fields[label] = edit
            form.addRow(f"{label}:", edit)
        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "cbc",
            "name": self.test_name,
            "result": {label: edit.text().strip() for label, edit in self._fields.items()},
        }
