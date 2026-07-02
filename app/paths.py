"""Centralized filesystem path management for Faisal Clinical Laboratory.

Single source of truth for every path the application reads from or writes to
(Windows user-data hotfix R2.1). No module should construct runtime paths on its
own -- they all go through :class:`AppPaths` / :func:`get_paths`.

Two roots, deliberately separated to follow Microsoft's Windows guidelines:

* ``application_dir`` -- **READ-ONLY** bundled resources (``data/``, ``assets/``,
  ``docs/``). In a PyInstaller build this is the bundle root (``sys._MEIPASS``,
  i.e. the ``_internal`` folder of a onedir build); running from source it is the
  project root. The application never writes here, so an install under
  ``C:\\Program Files`` -- where normal users cannot write -- works correctly.

* ``user_data_dir`` -- **WRITABLE** runtime data under ``%LOCALAPPDATA%`` on
  Windows (with cross-platform fallbacks for development). Holds ``logs/``,
  ``reports/`` and ``settings.json``. These directories are created
  automatically if missing.

The module also performs a one-time, non-destructive migration of an older
installation's settings/reports (which lived beside the executable in
Program Files) into ``user_data_dir`` -- copy only, never overwrite a newer
file, never delete the source, fully silent.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# The single writable-data folder name, used under %LOCALAPPDATA% (and fallbacks).
APP_FOLDER_NAME: str = "Faisal Clinical Laboratory"


class AppPaths:
    """Resolve and own every application path (read-only and writable).

    Instances are cheap and side-effect free to construct; directory creation
    and migration are explicit (:meth:`ensure_dirs`, :meth:`migrate_legacy_data`).
    Use :func:`get_paths` for the shared process-wide instance.
    """

    def __init__(self) -> None:
        self._application_dir: Path = self._resolve_application_dir()
        self._user_data_dir: Path = self._resolve_user_data_dir()

    # ── Resolution ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_application_dir() -> Path:
        """Return the read-only resource root (bundle root or project root)."""
        if getattr(sys, "frozen", False):
            # PyInstaller: bundled resources (data/, assets/, docs/) live under
            # sys._MEIPASS -- the _internal folder in a onedir build, or the
            # temporary extraction dir in a onefile build.
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                return Path(meipass)
            # Fallback: the folder that contains the executable.
            return Path(sys.executable).resolve().parent
        # Running from source: this file is app/paths.py, so the project root
        # is one level above the app package.
        return Path(__file__).resolve().parent.parent

    @staticmethod
    def _resolve_user_data_dir() -> Path:
        """Return the writable per-user data root (``%LOCALAPPDATA%`` on Windows)."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / APP_FOLDER_NAME
        # Cross-platform development fallbacks (no LOCALAPPDATA outside Windows).
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / APP_FOLDER_NAME
        return Path.home() / ".local" / "share" / APP_FOLDER_NAME

    # ── Read-only resource paths (Program Files) ──────────────────────

    @property
    def application_dir(self) -> Path:
        """Read-only bundle/project root containing application resources."""
        return self._application_dir

    @property
    def data_dir(self) -> Path:
        """Read-only ``data/`` directory (tests, packages, knowledge, doctors)."""
        return self._application_dir / "data"

    @property
    def assets_dir(self) -> Path:
        """Read-only ``assets/`` directory (icon and bundled images)."""
        return self._application_dir / "assets"

    @property
    def docs_dir(self) -> Path:
        """Read-only ``docs/`` directory (reference material)."""
        return self._application_dir / "docs"

    # ── Writable data paths (LocalAppData) ────────────────────────────

    @property
    def user_data_dir(self) -> Path:
        """Writable per-user data root under ``%LOCALAPPDATA%``."""
        return self._user_data_dir

    @property
    def logs_dir(self) -> Path:
        """Writable ``logs/`` directory."""
        return self._user_data_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        """Writable ``reports/`` directory (saved reports + History root)."""
        return self._user_data_dir / "reports"

    @property
    def settings_file(self) -> Path:
        """Writable ``settings.json`` (branding + report numbering)."""
        return self._user_data_dir / "settings.json"

    @property
    def log_file(self) -> Path:
        """Writable ``logs/application.log``."""
        return self.logs_dir / "application.log"

    # ── Directory creation ────────────────────────────────────────────

    def ensure_dirs(self) -> None:
        """Create the writable data directories if they do not already exist."""
        for directory in (self._user_data_dir, self.logs_dir, self.reports_dir):
            directory.mkdir(parents=True, exist_ok=True)

    # ── One-time legacy migration ─────────────────────────────────────

    def migrate_legacy_data(self) -> None:
        """Migrate settings/reports from an older beside-the-executable install.

        Idempotent and non-destructive: settings are copied only when no
        LocalAppData copy exists yet; each legacy report is copied only when a
        file of the same name is not already present. The source files in
        Program Files are never modified or deleted, and a newer LocalAppData
        file is never overwritten. Any failure is swallowed so migration can
        never prevent the application from starting.
        """
        try:
            self.ensure_dirs()
            self._migrate_settings()
            self._migrate_reports()
        except Exception as exc:  # migration must never block startup
            logger.warning("Legacy data migration skipped: %s", exc)

    def _legacy_settings_candidates(self) -> list[Path]:
        """Possible locations of a legacy ``settings.json`` (most likely first)."""
        app = self._application_dir
        return [
            app / "data" / "settings.json",   # R2 installer: _internal/data/
            app / "settings.json",            # _internal/settings.json
            app.parent / "settings.json",     # Program Files/<App>/settings.json
        ]

    def _legacy_reports_candidates(self) -> list[Path]:
        """Possible locations of a legacy ``reports/`` directory."""
        app = self._application_dir
        return [
            app / "reports",         # R2 installer: _internal/reports
            app.parent / "reports",  # Program Files/<App>/reports
        ]

    def _migrate_settings(self) -> None:
        """Copy a legacy settings file into LocalAppData exactly once."""
        target = self.settings_file
        if target.exists():
            return  # a LocalAppData copy already exists -- never overwrite it
        for source in self._legacy_settings_candidates():
            if source.is_file() and source.resolve() != target.resolve():
                shutil.copy2(source, target)
                logger.info("Migrated legacy settings from %s", source)
                return

    def _migrate_reports(self) -> None:
        """Copy legacy report files into LocalAppData without overwriting."""
        target_dir = self.reports_dir
        for source_dir in self._legacy_reports_candidates():
            if not source_dir.is_dir() or source_dir.resolve() == target_dir.resolve():
                continue
            for source in source_dir.rglob("*.json"):
                if not source.is_file():
                    continue
                destination = target_dir / source.name
                if destination.exists():
                    continue  # never overwrite an existing (newer) report
                shutil.copy2(source, destination)
                logger.info("Migrated legacy report %s", source.name)
            # Only migrate from the first existing legacy reports directory.
            return


# ── Process-wide singleton ────────────────────────────────────────────

_paths: AppPaths | None = None


def get_paths() -> AppPaths:
    """Return the shared :class:`AppPaths` instance (the single source of truth)."""
    global _paths
    if _paths is None:
        _paths = AppPaths()
    return _paths
