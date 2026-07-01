"""Laboratory Settings dialog for Faisal Clinical Laboratory.

Defines :class:`SettingsDialog`, the window that lets a laboratory owner
rebrand the software -- name, contact details, logo, signature, footer, report
numbering, and theme -- without touching any source code (Version 1.7.0).

The dialog edits settings only. It never builds reports, generates PDFs, or
prints. :class:`~app.engine.settings_manager.SettingsManager` remains the sole
source of truth: values are read from it on open and, on Save, written back
through it. Cancel discards; Restore Defaults repopulates the fields from
``DEFAULT_SETTINGS`` in memory only -- nothing is persisted until Save is
pressed.
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QComboBox,
    QWidget,
)

from app.engine.settings_manager import DEFAULT_SETTINGS, SettingsManager

# Project root: this file is app/dialogs/settings_dialog.py.
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Theme display labels mapped to the values stored in settings.
_THEMES: tuple[tuple[str, str], ...] = (
    ("Light", "light"),
    ("Dark", "dark"),
    ("Blue", "blue"),
    ("Green", "green"),
)

_IMAGE_FILTER: str = "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_PREVIEW_W: int = 240
_PREVIEW_H: int = 96


class SettingsDialog(QDialog):
    """Modal editor for laboratory settings.

    Args:
        settings_manager: The shared :class:`SettingsManager`. Read on open;
            written only when Save succeeds.
        parent: Optional parent widget.
    """

    def __init__(
        self,
        settings_manager: SettingsManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings_manager

        self.setWindowTitle("Laboratory Settings")
        self.resize(640, 620)
        self.setMinimumSize(560, 560)
        self.setSizeGripEnabled(True)

        self._build_ui()
        # Populate from the current settings (the single source of truth).
        self._load_values(self._settings.settings)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_branding_tab(), "Branding")
        tabs.addTab(self._build_reports_tab(), "Reports")
        root.addWidget(tabs, stretch=1)

        root.addLayout(self._build_buttons())

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._address_edit = QLineEdit()
        self._phone_edit = QLineEdit()
        self._email_edit = QLineEdit()
        self._website_edit = QLineEdit()
        self._website_edit.setPlaceholderText("https://example.com")
        self._license_edit = QLineEdit()

        form.addRow("Laboratory Name:", self._name_edit)
        form.addRow("Address:", self._address_edit)
        form.addRow("Phone:", self._phone_edit)
        form.addRow("Email:", self._email_edit)
        form.addRow("Website:", self._website_edit)
        form.addRow("License Number:", self._license_edit)
        return tab

    def _build_branding_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Logo row: path edit + Browse + preview.
        self._logo_edit = QLineEdit()
        self._logo_edit.setPlaceholderText("No logo selected")
        self._logo_preview = self._make_preview()
        self._logo_edit.textChanged.connect(
            lambda: self._update_preview(self._logo_preview, self._logo_edit.text())
        )
        layout.addLayout(
            self._image_field("Logo", self._logo_edit, self._logo_preview, self._browse_logo)
        )

        # Signature row: path edit + Browse + preview.
        self._sig_edit = QLineEdit()
        self._sig_edit.setPlaceholderText("No signature selected")
        self._sig_preview = self._make_preview()
        self._sig_edit.textChanged.connect(
            lambda: self._update_preview(self._sig_preview, self._sig_edit.text())
        )
        layout.addLayout(
            self._image_field("Signature", self._sig_edit, self._sig_preview, self._browse_signature)
        )

        # Footer (multiline).
        layout.addWidget(QLabel("Footer Text:"))
        self._footer_edit = QTextEdit()
        self._footer_edit.setPlaceholderText("Shown at the bottom of every report")
        self._footer_edit.setMaximumHeight(90)
        layout.addWidget(self._footer_edit)

        layout.addStretch(1)
        return tab

    def _build_reports_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)

        self._prefix_edit = QLineEdit()
        self._prefix_edit.setPlaceholderText("RPT")

        self._number_spin = QSpinBox()
        self._number_spin.setMinimum(1)
        self._number_spin.setMaximum(1_000_000_000)

        self._theme_combo = QComboBox()
        for label, value in _THEMES:
            self._theme_combo.addItem(label, value)

        form.addRow("Report Prefix:", self._prefix_edit)
        form.addRow("Next Report Number:", self._number_spin)
        form.addRow("Theme:", self._theme_combo)
        return tab

    def _build_buttons(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        restore_btn = QPushButton("Restore Defaults")
        restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_btn.clicked.connect(self._on_restore)

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        bar.addWidget(restore_btn)
        bar.addStretch(1)
        bar.addWidget(save_btn)
        bar.addWidget(cancel_btn)
        return bar

    # ── Small UI helpers ──────────────────────────────────────────────

    @staticmethod
    def _make_preview() -> QLabel:
        """Create a bordered image-preview label with a placeholder."""
        preview = QLabel("No image selected")
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setFixedSize(_PREVIEW_W, _PREVIEW_H)
        preview.setStyleSheet(
            "border:1px solid #cccccc; background:#fafafa; color:#888888;"
        )
        return preview

    def _image_field(self, label, edit, preview, on_browse) -> QVBoxLayout:
        """Build a labelled 'path + Browse' row above its preview."""
        box = QVBoxLayout()
        box.setSpacing(6)
        box.addWidget(QLabel(f"{label}:"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(edit, stretch=1)
        browse = QPushButton("Browse")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(on_browse)
        row.addWidget(browse)
        box.addLayout(row)

        box.addWidget(preview)
        return box

    # ── Value load / restore ──────────────────────────────────────────

    def _load_values(self, s: dict) -> None:
        """Populate every field from a settings mapping (no persistence)."""
        self._name_edit.setText(str(s.get("laboratory_name", "")))
        self._address_edit.setText(str(s.get("address", "")))
        self._phone_edit.setText(str(s.get("phone", "")))
        self._email_edit.setText(str(s.get("email", "")))
        self._website_edit.setText(str(s.get("website", "")))
        self._license_edit.setText(str(s.get("license_number", "")))

        self._logo_edit.setText(str(s.get("logo", "")))
        self._sig_edit.setText(str(s.get("signature", "")))
        self._footer_edit.setPlainText(str(s.get("footer", "")))

        self._prefix_edit.setText(str(s.get("report_prefix", "")))
        try:
            counter = int(s.get("report_counter", 0) or 0)
        except (TypeError, ValueError):
            counter = 0
        self._number_spin.setValue(max(1, counter + 1))

        theme = str(s.get("theme", "light")).lower()
        index = self._theme_combo.findData(theme)
        self._theme_combo.setCurrentIndex(index if index >= 0 else 0)

        # textChanged already refreshed previews, but force a pass in case the
        # text did not actually change (e.g. restoring identical defaults).
        self._update_preview(self._logo_preview, self._logo_edit.text())
        self._update_preview(self._sig_preview, self._sig_edit.text())

    def _on_restore(self) -> None:
        """Repopulate the UI from defaults; does NOT save (Save persists)."""
        self._load_values(DEFAULT_SETTINGS)

    # ── Browsing & preview ────────────────────────────────────────────

    def _browse_logo(self) -> None:
        self._browse_into(self._logo_edit, "Select Logo")

    def _browse_signature(self) -> None:
        self._browse_into(self._sig_edit, "Select Signature")

    def _browse_into(self, edit: QLineEdit, title: str) -> None:
        """Open a file dialog and store the chosen image (relative if possible)."""
        selected, _filter = QFileDialog.getOpenFileName(
            self, title, str(_PROJECT_ROOT), _IMAGE_FILTER
        )
        if selected:
            edit.setText(self._to_relative(selected))

    def _update_preview(self, preview: QLabel, path_text: str) -> None:
        """Render ``path_text`` into ``preview`` -- placeholder on any problem.

        Never raises: an empty, missing, or unreadable image simply shows a
        text placeholder instead of a pixmap.
        """
        text = (path_text or "").strip()
        if not text:
            preview.setPixmap(QPixmap())
            preview.setText("No image selected")
            return

        resolved = self._resolve(text)
        if not resolved.is_file():
            preview.setPixmap(QPixmap())
            preview.setText("Image not found")
            return

        pixmap = QPixmap(str(resolved))
        if pixmap.isNull():
            preview.setPixmap(QPixmap())
            preview.setText("Cannot preview image")
            return

        preview.setText("")
        preview.setPixmap(
            pixmap.scaled(
                _PREVIEW_W - 8,
                _PREVIEW_H - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ── Path helpers ──────────────────────────────────────────────────

    @staticmethod
    def _to_relative(path: str) -> str:
        """Return ``path`` relative to the project root when it lives inside it."""
        p = Path(path)
        try:
            return str(p.resolve().relative_to(_PROJECT_ROOT))
        except ValueError:
            return str(p)

    @staticmethod
    def _resolve(stored: str) -> Path:
        """Resolve a stored (possibly relative) image path to an absolute one."""
        p = Path(stored)
        return p if p.is_absolute() else _PROJECT_ROOT / p

    # ── Save / validation ─────────────────────────────────────────────

    def _on_save(self) -> None:
        """Validate, persist through the SettingsManager, and accept."""
        values, error = self._collect_and_validate()
        if error is not None:
            QMessageBox.warning(self, "Laboratory Settings", error)
            return

        for key, value in values.items():
            self._settings.set(key, value)
        self._settings.save()
        self.accept()

    def _collect_and_validate(self) -> tuple[dict, str | None]:
        """Gather field values and validate them.

        Returns ``(values, None)`` when valid, or ``({}, message)`` on the
        first validation failure.
        """
        prefix = self._prefix_edit.text().strip()
        if not prefix:
            return {}, "Report Prefix cannot be empty."

        number = self._number_spin.value()  # QSpinBox guarantees >= 1
        if number < 1:
            return {}, "Next Report Number must be an integer of 1 or more."

        email = self._email_edit.text().strip()
        if email and not _EMAIL_RE.match(email):
            return {}, "Please enter a valid email address, or leave it blank."

        website = self._website_edit.text().strip()
        if website and not website.startswith(("http://", "https://")):
            return {}, "Website must begin with http:// or https:// (or be blank)."

        logo = self._logo_edit.text().strip()
        if logo and not self._resolve(logo).is_file():
            return {}, "The selected logo file does not exist."

        signature = self._sig_edit.text().strip()
        if signature and not self._resolve(signature).is_file():
            return {}, "The selected signature file does not exist."

        values = {
            "laboratory_name": self._name_edit.text().strip(),
            "address": self._address_edit.text().strip(),
            "phone": self._phone_edit.text().strip(),
            "email": email,
            "website": website,
            "license_number": self._license_edit.text().strip(),
            "footer": self._footer_edit.toPlainText().strip(),
            "logo": logo,
            "signature": signature,
            "theme": self._theme_combo.currentData(),
            "report_prefix": prefix,
            # UI shows the *next* number; the counter stores one less.
            "report_counter": number - 1,
        }
        return values, None
