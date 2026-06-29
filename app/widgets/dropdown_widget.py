"""Dropdown result widget (qualitative / ICT tests)."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout

from app.widgets.base_test_widget import BaseTestWidget

_DEFAULT_OPTIONS: tuple[str, ...] = ("Reactive", "Non Reactive")


class DropdownTestWidget(BaseTestWidget):
    """A qualitative test whose result is chosen from a fixed list."""

    def __init__(self, name: str, options=None, parent=None) -> None:
        super().__init__(name, parent)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        self.result_combo = QComboBox()
        self.result_combo.addItems(list(options) if options else list(_DEFAULT_OPTIONS))
        form.addRow("Result:", self.result_combo)

        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "dropdown",
            "name": self.test_name,
            "result": self.result_combo.currentText(),
        }
