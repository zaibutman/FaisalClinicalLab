"""Blood Group result widget."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout

from app.widgets.base_test_widget import BaseTestWidget

_BLOOD_GROUPS: tuple[str, ...] = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")


class BloodGroupWidget(BaseTestWidget):
    """Select an ABO/Rh blood group from a fixed list."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(name, parent)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        self.group_combo = QComboBox()
        self.group_combo.addItems(list(_BLOOD_GROUPS))
        form.addRow("Blood Group:", self.group_combo)

        self.body_layout.addLayout(form)

    def collect_data(self) -> dict:
        return {
            "type": "blood_group",
            "name": self.test_name,
            "result": self.group_combo.currentText(),
        }
