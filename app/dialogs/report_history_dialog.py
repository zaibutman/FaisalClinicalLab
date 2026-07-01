"""Report History dialog for Faisal Clinical Laboratory.

Defines :class:`ReportHistoryDialog`, a modal window that lists every saved
report discovered by :class:`~app.engine.report_history.ReportHistory` and lets
the user pick one to open (Version 1.6.0).

It is a pure chooser: it receives already-discovered
:class:`~app.engine.report_history.HistoryEntry` rows, displays them, filters
them live, and -- on Open or a double click -- exposes the selected report's
filepath via :meth:`selected_filepath` and accepts. It performs no disk access,
no JSON parsing, and no report loading itself; the surrounding MainWindow owns
that flow.
"""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.engine.report_history import HistoryEntry

_MIN_WIDTH: int = 900
_MIN_HEIGHT: int = 600

# Column order for the history table.
_COLUMNS: tuple[str, ...] = (
    "Report ID",
    "Patient",
    "Age",
    "Doctor",
    "Date",
    "Tests",
    "Created",
)

# Role used to stash each row's report filepath on its first cell.
_FILEPATH_ROLE = Qt.ItemDataRole.UserRole


class ReportHistoryDialog(QDialog):
    """Modal list of saved reports with live search and an Open action.

    Args:
        entries: Discovered history rows (already sorted newest first by the
            engine). Displayed in the order given.
        parent: Optional parent widget.

    After the dialog is accepted, :meth:`selected_filepath` returns the chosen
    report's filepath; it returns ``None`` if the dialog was cancelled.
    """

    def __init__(
        self,
        entries: Iterable[HistoryEntry],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._entries: list[HistoryEntry] = list(entries)
        self._selected_filepath: str | None = None

        self.setWindowTitle("Report History")
        self.resize(_MIN_WIDTH, _MIN_HEIGHT)
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self.setSizeGripEnabled(True)

        self._build_ui()
        self._populate()

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Assemble the search box (top), table (center), and buttons (bottom)."""
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search patient...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        root.addWidget(self._search)

        root.addWidget(self._build_table(), stretch=1)

        root.addLayout(self._build_buttons())

    def _build_table(self) -> QTableWidget:
        """Build the report table (read-only, whole-row selection)."""
        table = QTableWidget(0, len(_COLUMNS), self)
        table.setHorizontalHeaderLabels(_COLUMNS)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.cellDoubleClicked.connect(self._on_row_activated)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Let the Patient and Doctor columns absorb extra width.
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self._table = table
        return table

    def _build_buttons(self) -> QHBoxLayout:
        """Build the bottom Open / Cancel button row."""
        bar = QHBoxLayout()
        bar.addStretch(1)

        self._open_btn = QPushButton("Open")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setDefault(True)
        self._open_btn.clicked.connect(self._on_open)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        bar.addWidget(self._open_btn)
        bar.addWidget(cancel_btn)
        return bar

    # ── Population & filtering ─────────────────────────────────────────

    def _populate(self) -> None:
        """Fill the table from the entries, one row per report."""
        self._table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            values = (
                entry.report_id,
                entry.patient_name,
                entry.patient_age,
                entry.doctor,
                entry.date,
                str(entry.test_count),
                entry.created_at,
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(_FILEPATH_ROLE, entry.filepath)
                self._table.setItem(row, col, item)

    def _apply_filter(self, text: str) -> None:
        """Hide rows that do not match ``text`` (case-insensitive).

        Matches only Patient, Doctor, and Report ID -- never the report JSON.
        """
        query = text.strip().lower()
        for row, entry in enumerate(self._entries):
            haystack = (
                f"{entry.patient_name} {entry.doctor} {entry.report_id}".lower()
            )
            self._table.setRowHidden(row, bool(query) and query not in haystack)

    # ── Selection handling ────────────────────────────────────────────

    def _on_row_activated(self, row: int, _column: int) -> None:
        """Open the double-clicked ``row``."""
        self._accept_row(row)

    def _on_open(self) -> None:
        """Open the currently selected row, if any (ignored when none)."""
        self._accept_row(self._table.currentRow())

    def _accept_row(self, row: int) -> None:
        """Record the filepath for ``row`` and accept, if the row is valid."""
        if row < 0 or self._table.isRowHidden(row):
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        filepath = item.data(_FILEPATH_ROLE)
        if not filepath:
            return
        self._selected_filepath = str(filepath)
        self.accept()

    # ── Public API ────────────────────────────────────────────────────

    def selected_filepath(self) -> str | None:
        """Return the chosen report's filepath, or ``None`` if cancelled."""
        return self._selected_filepath
