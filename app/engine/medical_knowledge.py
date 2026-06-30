"""Medical knowledge database for Faisal Clinical Laboratory.

Defines :class:`MedicalKnowledge`, the read-only single source of truth for
the laboratory's medical data (units, reference ranges, dropdown options, and
the CBC / urine / semen field layouts). All values originate from the Master
Test Catalog and are stored verbatim in ``data/medical_knowledge.json``.

This module is pure Python -- it imports no UI, no widgets, and no report
builder -- so it can be shared by the Widget Factory, Result Widgets, Package
Resolver, Report Builder, printing, and future engines (Version 0.8.0).

The database is authoritative for *medical* content only. Structural fields
(id, name, category, report_heading, widget_type) mirror ``data/tests.json``,
which remains the file that drives the UI. The two files are kept separate on
purpose and are never merged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# data/medical_knowledge.json lives at the project root (this file is in app/engine/).
_DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
_KNOWLEDGE_FILE: Path = _DATA_DIR / "medical_knowledge.json"


class MedicalKnowledge:
    """Load and serve the laboratory's medical knowledge database.

    The database is read once on construction. A missing or malformed file is
    logged and treated as empty so the application never crashes -- callers
    receive empty results rather than exceptions, and no medical values are
    ever fabricated to fill a gap.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path: Path = Path(path) if path is not None else _KNOWLEDGE_FILE
        self._tests: dict[str, dict] = {}
        self._packages: dict[str, dict] = {}
        self._meta: dict = {}
        self.load()

    # ── Loading ──────────────────────────────────────────────────────

    def load(self) -> None:
        """Load the database from disk, tolerating a missing/malformed file."""
        if not self._path.exists():
            logger.warning("Medical knowledge file missing: %s", self._path.name)
            self._tests, self._packages, self._meta = {}, {}, {}
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("knowledge root is not an object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Malformed medical knowledge file (%s): %s", self._path.name, exc)
            self._tests, self._packages, self._meta = {}, {}, {}
            return

        tests = data.get("tests", {})
        packages = data.get("packages", {})
        self._tests = tests if isinstance(tests, dict) else {}
        self._packages = packages if isinstance(packages, dict) else {}
        self._meta = data.get("_meta", {}) if isinstance(data.get("_meta", {}), dict) else {}
        logger.info(
            "Medical knowledge loaded: %s (%d test(s), %d package(s))",
            self._path.name,
            len(self._tests),
            len(self._packages),
        )

    def reload(self) -> None:
        """Re-read the database from disk, discarding the cached copy."""
        logger.info("Reloading medical knowledge from %s", self._path.name)
        self.load()

    # ── Test lookups ─────────────────────────────────────────────────

    def has_test(self, test_id: str) -> bool:
        """Return True if ``test_id`` exists in the database."""
        return test_id in self._tests

    def get_test(self, test_id: str) -> dict | None:
        """Return the full entry for ``test_id``, or ``None`` if unknown."""
        return self._tests.get(test_id)

    def get_all_tests(self) -> dict[str, dict]:
        """Return a shallow copy of the ``id -> entry`` test mapping."""
        return dict(self._tests)

    def get_reference_range(self, test_id: str) -> Any:
        """Return the stored reference range(s) for ``test_id``.

        Returns the value exactly as stored in the catalog database: a list of
        strings for most tests, a ``{component: [ranges]}`` mapping for SBR, or
        ``None`` when the catalog provides no reference range for the test.
        """
        test = self._tests.get(test_id)
        if test is None:
            return None
        return test.get("reference_range")

    def get_unit(self, test_id: str) -> str:
        """Return the unit for ``test_id``, or ``""`` if none is recorded."""
        test = self._tests.get(test_id)
        if test is None:
            return ""
        return test.get("unit", "")

    def get_dropdown_options(self, test_id: str) -> list[str]:
        """Return the catalog-observed dropdown options for ``test_id``.

        Returns an empty list when the test is unknown or the catalog does not
        enumerate options for it. Options are returned in catalog order.
        """
        test = self._tests.get(test_id)
        if test is None:
            return []
        options = test.get("dropdown_options", [])
        return list(options) if isinstance(options, list) else []

    # ── Panel field layouts ──────────────────────────────────────────

    def get_cbc_fields(self) -> list[dict]:
        """Return the ordered CBC parameter list, or ``[]`` if unavailable."""
        return self._panel_fields("cbc", "cbc_fields")

    def get_urine_fields(self) -> list[dict]:
        """Return the ordered urine parameter list, or ``[]`` if unavailable."""
        return self._panel_fields("urine_re", "urine_fields")

    def get_semen_fields(self) -> list[dict]:
        """Return the ordered semen parameter list, or ``[]`` if unavailable."""
        return self._panel_fields("semen", "semen_fields")

    def _panel_fields(self, test_id: str, key: str) -> list[dict]:
        """Return the ordered field list ``key`` from panel test ``test_id``."""
        test = self._tests.get(test_id)
        if test is None:
            return []
        fields = test.get(key, [])
        return list(fields) if isinstance(fields, list) else []

    # ── Packages ─────────────────────────────────────────────────────

    def get_package(self, package_id: str) -> dict | None:
        """Return the catalog package entry for ``package_id``, or ``None``."""
        return self._packages.get(package_id)

    def get_all_packages(self) -> dict[str, dict]:
        """Return a shallow copy of the ``id -> entry`` package mapping."""
        return dict(self._packages)
