"""Semen analysis result widget -- simple fields only."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit

from app.widgets.base_test_widget import BaseTestWidget

_SEMEN_FIELDS: tuple[str, ...] = (
    "Volume",
    "Colour",
    "Sperm Count",
    "Motility",
    "Morphology",
)


class SemenWidget(BaseTestWidget):
    """Semen analysis with a flat set of text fields."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name, parent)
        self._fields: dict[str, QLineEdit] = {}

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)
        for label in _SEMEN_FIELDS:
            edit = QLineEdit()
            self._fields[label] = edit
            form.addRow(f"{label}:", edit)
        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "semen",
            "name": self.test_name,
            "result": {label: edit.text().strip() for label, edit in self._fields.items()},
        }
