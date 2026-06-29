"""SBR (Serum Bilirubin) result widget."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLineEdit

from app.widgets.base_test_widget import BaseTestWidget

_SBR_FIELDS: tuple[str, ...] = (
    "Total Bilirubin",
    "Direct Bilirubin",
    "Indirect Bilirubin",
)


class SBRWidget(BaseTestWidget):
    """Serum bilirubin fractions in a single widget."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name, parent)
        self._fields: dict[str, QLineEdit] = {}

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)
        for label in _SBR_FIELDS:
            edit = QLineEdit()
            self._fields[label] = edit
            form.addRow(f"{label}:", edit)
        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "sbr",
            "name": self.test_name,
            "result": {label: edit.text().strip() for label, edit in self._fields.items()},
        }
