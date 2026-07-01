"""Report history discovery for Faisal Clinical Laboratory.

Defines :class:`ReportHistory`, a lightweight, UI-independent manager that
discovers every saved report on disk and returns compact metadata entries
(Version 1.6.0).

This is **not** a database, a search engine, or patient search. It is only a
scanner:

* It walks the reports directory **recursively**, so a flat ``reports/`` today
  and a future ``reports/2026/07/`` hierarchy are both discovered without any
  change here.
* It imports **no PySide6** and owns no serialization. Each file is loaded via
  :meth:`ReportStorage.load` -- the single source of truth for the on-disk
  format -- so no JSON parsing is duplicated in this module.
* It **never crashes** on bad data: an unreadable or corrupted report is
  skipped and scanning continues.

It is intentionally minimal so it can become the foundation for future
Search, Recent Reports, Patient History, Daily / Monthly reports, and an
eventual database migration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.engine.lab_report import LabReport
from app.engine.report_storage import ReportStorage

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Compact, display-ready metadata for one saved report.

    Holds only what a history list needs -- never the full report. Load the
    complete :class:`LabReport` on demand via :meth:`ReportStorage.load` using
    :attr:`filepath`.
    """

    filepath: str
    report_id: str
    patient_name: str
    patient_age: str
    doctor: str
    date: str
    created_at: str
    test_count: int


class ReportHistory:
    """Discover saved reports and return lightweight metadata entries.

    Args:
        reports_dir: Directory to scan (recursively). Defaults to the same
            reports directory used by :class:`ReportStorage`. Injectable for
            testing.
        storage: Optional :class:`ReportStorage` to reuse for loading. A
            default instance is created if none is supplied.
    """

    def __init__(
        self,
        reports_dir: Path | str | None = None,
        storage: ReportStorage | None = None,
    ) -> None:
        self._storage: ReportStorage = storage or ReportStorage()
        self._reports_dir: Path = (
            Path(reports_dir)
            if reports_dir is not None
            else self._storage.reports_dir
        )

    @property
    def reports_dir(self) -> Path:
        """Return the directory this history scans."""
        return self._reports_dir

    # ── Public API ────────────────────────────────────────────────────

    def get_reports(self) -> list[HistoryEntry]:
        """Return every discoverable report as a :class:`HistoryEntry`.

        Scans :attr:`reports_dir` and all subdirectories for ``*.json`` files,
        loads each one's metadata via :class:`ReportStorage`, and returns the
        entries sorted newest first. Files that cannot be read or parsed are
        skipped; scanning always continues.
        """
        entries: list[HistoryEntry] = []
        for path in self._iter_report_files():
            entry = self._build_entry(path)
            if entry is not None:
                entries.append(entry)

        # created_at is written as "YYYY-MM-DD HH:MM:SS", so a plain reverse
        # string sort is chronological (newest first). Empty timestamps sort
        # last, which keeps well-formed reports on top.
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries

    # ── Internals ─────────────────────────────────────────────────────

    def _iter_report_files(self):
        """Yield every ``*.json`` path under the reports directory, recursively.

        Returns nothing (an empty iterator) if the directory does not exist.
        """
        if not self._reports_dir.is_dir():
            return
        for path in sorted(self._reports_dir.rglob("*.json")):
            if path.is_file():
                yield path

    def _build_entry(self, path: Path) -> HistoryEntry | None:
        """Load ``path`` and reduce it to a :class:`HistoryEntry`.

        Returns ``None`` (and skips the file) if it cannot be loaded or parsed
        -- the history never crashes on a bad report.
        """
        try:
            report: LabReport = self._storage.load(path)
        except Exception as exc:  # unreadable / corrupted -- skip and continue
            logger.warning("Skipped unreadable report %s: %s", path.name, exc)
            return None

        patient = report.patient
        info = report.report_info
        return HistoryEntry(
            filepath=str(path),
            report_id=info.report_id,
            patient_name=patient.name,
            patient_age=patient.age,
            doctor=patient.doctor,
            date=patient.date,
            created_at=info.created_at,
            test_count=len(report.test_results),
        )
