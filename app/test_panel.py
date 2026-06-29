"""Medical Test sidebar for Faisal Clinical Laboratory.

Defines :class:`TestPanel`, a scrollable, searchable sidebar that lists
the available laboratory tests grouped by category. Tests are loaded
entirely from ``data/tests.json`` -- nothing about the catalogue is
hardcoded here -- so future features (Widget Factory, Package Resolver,
Add New Test) can extend the data without touching this panel.

Clicking a test emits :attr:`TestPanel.test_selected` with the test id.
No result widgets or insertion logic are implemented yet (Version 0.3.0).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.styles import PRIMARY

logger = logging.getLogger(__name__)

# data/tests.json lives at the project root (this file is in app/).
_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
_TESTS_FILE: Path = _DATA_DIR / "tests.json"

_DEFAULT_CATEGORY: str = "Uncategorized"
_EMPTY_MESSAGE: str = "No tests available."


def _load_tests() -> list[dict[str, str]]:
    """Load the test catalogue from ``data/tests.json``.

    Expects a JSON array of objects that include at least ``id`` and
    ``name`` (plus typically ``category``, ``type`` and
    ``report_heading``). Returns an empty list if the file is missing,
    empty (e.g. ``{}`` or ``[]``), or malformed -- the panel then shows
    its empty-state message.

    Entries missing an ``id`` or ``name`` are skipped; a missing category
    falls back to "Uncategorized". All other keys are preserved verbatim
    so downstream consumers (Widget Factory, Package Resolver) can read
    fields such as ``type`` and ``report_heading`` straight off the
    records returned by :meth:`TestPanel.selected_test`.
    """
    try:
        raw = json.loads(_TESTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read tests.json (%s); treating as empty", exc)
        return []

    tests: list[dict[str, str]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            test_id = str(item.get("id", "")).strip()
            name = str(item.get("name", "")).strip()
            if not (test_id and name):
                continue
            record = dict(item)  # preserve type, report_heading, etc.
            record["id"] = test_id
            record["name"] = name
            record["category"] = str(item.get("category", "")).strip() or _DEFAULT_CATEGORY
            tests.append(record)
    return tests


class TestPanel(QWidget):
    """Searchable, scrollable sidebar of category-grouped test buttons.

    Signals:
        test_selected(str): emitted with the test id when a test is clicked.
    """

    test_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tests: list[dict[str, str]] = []
        # Parallel tracking for live filtering.
        self._buttons: list[tuple[QPushButton, dict[str, str]]] = []
        self._category_headers: dict[str, QLabel] = {}
        self._selected_id: str | None = None

        self._build_ui()
        self.load_tests()

    # ── Construction ────────────────────────────────────────────────
    def _build_ui(self) -> None:
        """Create the search box and the scrollable test container."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search tests...")
        self.search_edit.textChanged.connect(self.filter_tests)
        layout.addWidget(self.search_edit)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(4, 4, 4, 4)
        self._content_layout.setSpacing(6)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self._content)

        layout.addWidget(self.scroll)

    # ── Public API ──────────────────────────────────────────────────
    def load_tests(self) -> None:
        """Load tests from JSON and (re)build the sidebar contents."""
        self._tests = _load_tests()
        self._rebuild_list()
        logger.info("Loaded %d test(s)", len(self._tests))

    def reload_tests(self) -> None:
        """Reload the catalogue from disk, preserving nothing stale."""
        logger.info("Reloading tests from %s", _TESTS_FILE.name)
        self.clear_selection()
        self.search_edit.clear()
        self.load_tests()

    def filter_tests(self, text: str) -> None:
        """Show only tests whose name contains ``text`` (case-insensitive).

        Category headers with no visible tests are hidden too.
        """
        query = text.strip().lower()
        for button, test in self._buttons:
            button.setVisible(query in test["name"].lower())
        for category, header in self._category_headers.items():
            visible = any(
                not btn.isHidden() for btn, test in self._buttons
                if test["category"] == category
            )
            header.setVisible(visible)

    def selected_test(self) -> dict[str, str] | None:
        """Return the currently selected test dict, or ``None``."""
        if self._selected_id is None:
            return None
        return next((t for t in self._tests if t["id"] == self._selected_id), None)

    def clear_selection(self) -> None:
        """Forget the current selection."""
        self._selected_id = None

    # ── Internals ───────────────────────────────────────────────────
    def _rebuild_list(self) -> None:
        """Rebuild the scroll contents from ``self._tests``."""
        self._clear_content()
        self._buttons = []
        self._category_headers = {}

        if not self._tests:
            empty = QLabel(_EMPTY_MESSAGE)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(empty)
            return

        for category, tests in self._group_by_category(self._tests).items():
            header = QLabel(category)
            header.setStyleSheet(
                f"font-weight:700; color:{PRIMARY}; background:transparent;"
            )
            self._content_layout.addWidget(header)
            self._category_headers[category] = header

            for test in tests:
                self._content_layout.addWidget(self._make_test_button(test))

    @staticmethod
    def _group_by_category(
        tests: list[dict[str, str]],
    ) -> dict[str, list[dict[str, str]]]:
        """Group tests by category, preserving first-seen category order."""
        grouped: dict[str, list[dict[str, str]]] = {}
        for test in tests:
            grouped.setdefault(test["category"], []).append(test)
        return grouped

    def _make_test_button(self, test: dict[str, str]) -> QPushButton:
        """Create a horizontally-expanding button for a single test.

        The test's id/name/category are stored as Qt object properties so
        downstream features can read them straight off the widget.
        """
        # Escape '&' so Qt doesn't treat it as a mnemonic accelerator
        # (e.g. "Blood Group & Rh"); the real name is kept in the property.
        button = QPushButton(test["name"].replace("&", "&&"))
        button.setProperty("test_id", test["id"])
        button.setProperty("test_name", test["name"])
        button.setProperty("test_category", test["category"])
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(self._on_test_clicked)
        self._buttons.append((button, test))
        return button

    def _on_test_clicked(self) -> None:
        """Handle a test button click: record, log and emit the id."""
        button = self.sender()
        if button is None:
            return
        test_id = str(button.property("test_id"))
        self._selected_id = test_id
        logger.info("Test selected: %s", test_id)
        self.test_selected.emit(test_id)

    def _clear_content(self) -> None:
        """Remove and delete every widget currently in the scroll area.

        ``setParent(None)`` detaches each widget from the display
        immediately so a rebuild never briefly overlaps old and new
        contents; ``deleteLater`` then frees it on the next event loop.
        """
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
