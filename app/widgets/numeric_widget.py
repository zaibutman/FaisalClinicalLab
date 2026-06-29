"""Numeric result widget (single numeric value with unit and range)."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit

from app.widgets.base_test_widget import BaseTestWidget


class NumericTestWidget(BaseTestWidget):
    """A single-value numeric test (e.g. ESR, Cholesterol).

    Shows a result field plus read-only unit and reference-range labels.
    """

    def __init__(
        self,
        name: str,
        unit: str = "",
        reference_range: str = "",
        parent=None,
    ) -> None:
        super().__init__(name, parent)
        self._unit = unit

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        self.result_edit = QLineEdit()
        self.result_edit.setPlaceholderText("Enter result")
        form.addRow("Result:", self.result_edit)

        if unit:
            form.addRow("Unit:", QLabel(unit))
        form.addRow("Reference Range:", QLabel(reference_range or "—"))

        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "numeric",
            "name": self.test_name,
            "result": self.result_edit.text().strip(),
        }
