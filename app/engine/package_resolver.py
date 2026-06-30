"""Package resolution for Faisal Clinical Laboratory.

Defines :class:`PackageResolver`, which loads package definitions from
``data/packages.json`` and resolves a package id into an ordered, de-duplicated
list of the test ids it contains. Resolution never raises: an unknown package
returns an empty list, and a missing or malformed file is transparently
restored to the built-in defaults so the application never crashes
(Version 0.7.0).

The default definitions reference only test ids that already exist in
``data/tests.json`` -- no new laboratory tests are invented here.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# data/packages.json lives at the project root (this file is in app/engine/).
_DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
_PACKAGES_FILE: Path = _DATA_DIR / "packages.json"

# Default package -> ordered member test ids. Every id below exists in
# data/tests.json; none are invented and none repeat within a package.
DEFAULT_PACKAGES: dict[str, list[str]] = {
    "lipid_profile": ["cholesterol", "triglycerides", "hdl", "ldl"],
    "medical_tests": ["cbc", "blood_group", "rbs", "hbsag", "hcv", "hiv", "urine_re"],
    "vh": ["hbsag", "hcv"],
    "rft_lft": ["urea", "creatinine", "uric_acid", "sgpt", "sbr", "alp"],
    "lft": ["sgpt", "sbr", "alp"],
}


class PackageResolver:
    """Resolve package ids into ordered, unique lists of test ids.

    Definitions are read from ``data/packages.json`` on construction. A
    missing, empty, or malformed file is replaced with the built-in
    defaults so resolution always has valid data to work with.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path: Path = Path(path) if path is not None else _PACKAGES_FILE
        self._packages: dict[str, list[str]] = dict(DEFAULT_PACKAGES)
        self.load()

    # ── Persistence ──────────────────────────────────────────────────

    def load(self) -> dict[str, list[str]]:
        """Load package definitions, restoring defaults on any problem.

        Missing/empty/malformed file -> defaults are written and used.
        The in-memory definitions are always left valid.
        """
        if not self._path.exists():
            self._restore_defaults("missing")
            return self._packages

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("packages root is not an object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Malformed packages restored to defaults (%s): %s",
                self._path.name,
                exc,
            )
            self._restore_defaults("malformed")
            return self._packages

        if not data:
            # An empty file is populated from the defaults (Task 008).
            self._restore_defaults("empty")
            return self._packages

        self._packages = self._normalize(data)
        logger.info(
            "Packages loaded: %s (%d package(s))",
            self._path.name,
            len(self._packages),
        )
        return self._packages

    def _restore_defaults(self, reason: str) -> None:
        """Reset definitions to the defaults, persist them, and log once."""
        self._packages = dict(DEFAULT_PACKAGES)
        self._write(self._packages)
        logger.info("Packages restored to defaults (%s): %s", reason, self._path.name)

    def _write(self, packages: dict[str, list[str]]) -> None:
        """Write ``packages`` to disk as UTF-8 JSON (no logging)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(packages, fh, indent=4, ensure_ascii=False)

    @staticmethod
    def _normalize(data: dict) -> dict[str, list[str]]:
        """Coerce loaded data into ``{str: [str, ...]}`` form, skipping junk."""
        normalized: dict[str, list[str]] = {}
        for key, value in data.items():
            if isinstance(value, list):
                normalized[str(key)] = [str(v) for v in value]
        return normalized

    # ── API ──────────────────────────────────────────────────────────

    def resolve(self, package_id: str) -> list[str]:
        """Resolve ``package_id`` to an ordered, unique list of test ids.

        Returns an empty list for an unknown package. Never raises.
        """
        try:
            members = self._packages.get(package_id, [])
            if not isinstance(members, list):
                return []
            seen: set[str] = set()
            ordered: list[str] = []
            for raw in members:
                test_id = str(raw).strip()
                if test_id and test_id not in seen:
                    seen.add(test_id)
                    ordered.append(test_id)
            logger.info("Package resolved: %s -> %d test(s)", package_id, len(ordered))
            return ordered
        except Exception as exc:  # never propagate a resolution failure
            logger.warning("Package resolution failed for '%s': %s", package_id, exc)
            return []

    def package_ids(self) -> list[str]:
        """Return the known package ids."""
        return list(self._packages.keys())
