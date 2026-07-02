"""Patient Information panel for Faisal Clinical Laboratory.

Defines :class:`PatientPanel`, a self-contained widget holding the
patient's identifying fields (name, gender, referring doctor, date).
The panel exposes a small public API -- :meth:`get_patient_data`,
:meth:`set_patient_data` and :meth:`clear` -- and emits granular change
signals so downstream panels (e.g. CBC reference ranges) can react to
edits. The panel holds no medical/business logic itself (Version 0.2.0).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.paths import get_paths

logger = logging.getLogger(__name__)

# doctors.json is a read-only bundled resource; the centralized helper resolves
# data/ inside the install (Program Files) or the source tree.
_DOCTORS_FILE: Path = get_paths().data_dir / "doctors.json"

_GENDERS: tuple[str, ...] = ("Male", "Female")
_DEFAULT_DOCTOR: str = "Select Doctor"
_MAX_NAME_LENGTH: int = 100
_DATE_FORMAT: str = "yyyy-MM-dd"


def _load_doctors() -> list[str]:
    """Load referring-doctor names from ``data/doctors.json``.

    Accepts either a JSON array of strings or an array of objects with a
    ``"name"`` key. Returns an empty list if the file is missing, empty,
    or malformed (the caller substitutes a default entry).
    """
    try:
        raw = json.loads(_DOCTORS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read doctors.json (%s); using default", exc)
        return []

    doctors: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                doctors.append(item.strip())
            elif isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                if name:
                    doctors.append(name)
    return doctors


class PatientPanel(QWidget):
    """Widget for entering and retrieving patient information.

    Signals:
        name_changed(str):   emitted when the patient name text changes.
        gender_changed(str): emitted when the selected gender changes.
        doctor_changed(str): emitted when the selected doctor changes.
        date_changed(str):   emitted (as ``YYYY-MM-DD``) when the date changes.
    """

    name_changed = Signal(str)
    gender_changed = Signal(str)
    doctor_changed = Signal(str)
    date_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._connect_signals()
        logger.info("PatientPanel initialized")

    # ── Construction ────────────────────────────────────────────────
    def _build_ui(self) -> None:
        """Create the four labelled fields in a single horizontal row."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Patient name.
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter patient name")
        self.name_edit.setMaxLength(_MAX_NAME_LENGTH)
        layout.addLayout(self._field("Patient Name", self.name_edit), stretch=3)

        # Gender.
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(_GENDERS)
        layout.addLayout(self._field("Gender", self.gender_combo), stretch=1)

        # Referring doctor.
        self.doctor_combo = QComboBox()
        self._populate_doctors()
        layout.addLayout(self._field("Referring Doctor", self.doctor_combo), stretch=2)

        # Date (defaults to today, calendar popup, editable).
        self.date_edit = QDateEdit()
        self.date_edit.setDisplayFormat(_DATE_FORMAT)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        layout.addLayout(self._field("Date", self.date_edit), stretch=1)

    def _field(self, label_text: str, widget: QWidget) -> QVBoxLayout:
        """Return a vertical (label-above-input) column for one field."""
        column = QVBoxLayout()
        column.setSpacing(4)
        label = QLabel(label_text)
        column.addWidget(label)
        column.addWidget(widget)
        column.addStretch(0)
        return column

    def _populate_doctors(self) -> None:
        """Fill the doctor combo from JSON, or a single default entry."""
        doctors = _load_doctors()
        if doctors:
            self.doctor_combo.addItems(doctors)
        else:
            self.doctor_combo.addItem(_DEFAULT_DOCTOR)

    def _connect_signals(self) -> None:
        """Wire widget changes to the panel's public change signals."""
        self.name_edit.textChanged.connect(self.name_changed)
        self.gender_combo.currentTextChanged.connect(self.gender_changed)
        self.doctor_combo.currentTextChanged.connect(self.doctor_changed)
        self.date_edit.dateChanged.connect(
            lambda qdate: self.date_changed.emit(qdate.toString(_DATE_FORMAT))
        )

    # ── Public API ──────────────────────────────────────────────────
    def get_patient_data(self) -> dict[str, str]:
        """Return the current patient data as a plain dict."""
        return {
            "name": self.name_edit.text().strip(),
            "gender": self.gender_combo.currentText(),
            "doctor": self.doctor_combo.currentText(),
            "date": self.date_edit.date().toString(_DATE_FORMAT),
        }

    def set_patient_data(self, data: dict[str, str]) -> None:
        """Populate the panel from a patient-data dict.

        Missing keys are ignored; unknown gender/doctor values are added
        to their combo so the data round-trips faithfully. The date is
        parsed from ``YYYY-MM-DD`` and falls back to today if invalid.
        """
        if not isinstance(data, dict):
            return

        self.name_edit.setText(str(data.get("name", "")))
        self._select_or_add(self.gender_combo, data.get("gender"))
        self._select_or_add(self.doctor_combo, data.get("doctor"))

        date_text = str(data.get("date", ""))
        qdate = QDate.fromString(date_text, _DATE_FORMAT)
        self.date_edit.setDate(qdate if qdate.isValid() else QDate.currentDate())

    def clear(self) -> None:
        """Reset every field to its default state."""
        self.name_edit.clear()
        self.gender_combo.setCurrentIndex(0)
        self.doctor_combo.setCurrentIndex(0)
        self.date_edit.setDate(QDate.currentDate())
        logger.info("PatientPanel cleared")

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _select_or_add(combo: QComboBox, value: object) -> None:
        """Select ``value`` in ``combo``, appending it if not present."""
        if value is None:
            return
        text = str(value)
        index = combo.findText(text, Qt.MatchFlag.MatchExactly)
        if index < 0:
            combo.addItem(text)
            index = combo.findText(text, Qt.MatchFlag.MatchExactly)
        combo.setCurrentIndex(index)
