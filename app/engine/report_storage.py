"""Report persistence for Faisal Clinical Laboratory.

Defines :class:`ReportStorage`, the file-level helper that saves and loads a
:class:`~app.engine.lab_report.LabReport` as JSON on disk (Version 1.4.0).

It is deliberately thin and UI-independent:

* It **owns no serialization.** Saving and loading delegate to the report's
  own :meth:`LabReport.to_json` / :meth:`LabReport.from_json`, so there is a
  single source of truth for the on-disk format.
* It imports **no PySide6** and shows no dialogs -- the MainWindow owns all
  user interaction. This module only touches the filesystem.
* It **never overwrites a name silently:** :meth:`create_filename` returns a
  name that does not already exist in the target directory.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.engine.lab_report import LabReport
from app.paths import get_paths

logger = logging.getLogger(__name__)

# Saved reports are user-writable, so the default directory lives under
# %LOCALAPPDATA% (never in the read-only install directory).
_DEFAULT_REPORTS_DIR: Path = get_paths().reports_dir

# Characters that are illegal in Windows filenames (a superset of POSIX's).
_ILLEGAL_CHARS: str = '<>:"/\\|?*'


class ReportStorage:
    """Save and load lab reports as JSON files.

    Args:
        reports_dir: Default directory for generated filenames and saves.
            Defaults to ``<project>/reports``. Injectable for testing.
    """

    def __init__(self, reports_dir: Path | str | None = None) -> None:
        self._reports_dir: Path = (
            Path(reports_dir) if reports_dir is not None else _DEFAULT_REPORTS_DIR
        )

    @property
    def reports_dir(self) -> Path:
        """Return the default reports directory."""
        return self._reports_dir

    # ── Filesystem operations ─────────────────────────────────────────

    def save(self, report: LabReport, filepath: Path | str) -> Path:
        """Write ``report`` to ``filepath`` as JSON and return the path.

        The parent directory (e.g. ``reports/``) is created automatically if
        it does not exist. Serialization is delegated entirely to
        :meth:`LabReport.to_json` -- no format logic lives here. Any OS error
        (permission denied, invalid path, disk full) propagates to the caller
        to surface; this layer never shows dialogs.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        report.to_json(path)
        return path

    def load(self, filepath: Path | str) -> LabReport:
        """Load and return a :class:`LabReport` from ``filepath``.

        Delegates to :meth:`LabReport.from_json`; no parsing logic is
        duplicated here.
        """
        return LabReport.from_json(Path(filepath))

    @staticmethod
    def exists(filepath: Path | str) -> bool:
        """Return True if ``filepath`` already exists as a file."""
        return Path(filepath).is_file()

    # ── Filename generation ───────────────────────────────────────────

    def create_filename(
        self,
        report: LabReport,
        directory: Path | str | None = None,
    ) -> str:
        """Build a safe, non-colliding default filename for ``report``.

        Format: ``REPORTID_PATIENTNAME_DATE.json`` (spaces -> underscores,
        illegal characters removed). If a file with that name already exists in
        ``directory`` (default: the reports directory), a numeric suffix is
        appended so an existing report is never overwritten silently.
        """
        target_dir = Path(directory) if directory is not None else self._reports_dir

        parts = [
            self._sanitize(report.report_info.report_id),
            self._sanitize(report.patient.name),
            self._sanitize(report.patient.date),
        ]
        stem = "_".join(p for p in parts if p) or "report"

        candidate = f"{stem}.json"
        counter = 2
        while (target_dir / candidate).exists():
            candidate = f"{stem}_{counter}.json"
            counter += 1
        return candidate

    @staticmethod
    def _sanitize(text: str) -> str:
        """Return ``text`` safe for a filename segment.

        Removes illegal/control characters, turns spaces into underscores, and
        collapses runs of underscores. Returns ``""`` for empty input.
        """
        if not text:
            return ""
        cleaned = "".join(
            "_" if (ch in _ILLEGAL_CHARS or ord(ch) < 32) else ch
            for ch in text.strip()
        )
        cleaned = cleaned.replace(" ", "_")
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        return cleaned.strip("_")
