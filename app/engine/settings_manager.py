"""Application settings persistence for Faisal Clinical Laboratory.

Defines :class:`SettingsManager`, the single source of truth for
user-configurable settings stored in ``data/settings.json``. It loads
settings on construction, creates a default file when none exists,
and transparently recovers from a missing or malformed file so the
application never crashes because of bad settings (Version 0.6.0).

The manager also bridges the settings into the report engine via
:meth:`SettingsManager.get_laboratory_info`, which builds a populated
:class:`~app.engine.laboratory.LaboratoryInfo` from the stored values.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.engine.laboratory import LaboratoryInfo
from app.paths import get_paths

logger = logging.getLogger(__name__)

# settings.json is user-writable, so it lives under %LOCALAPPDATA% (never in the
# read-only install directory). The centralized helper is the single source.
_SETTINGS_FILE: Path = get_paths().settings_file

# Sensible placeholder defaults -- no real laboratory values are hardcoded.
DEFAULT_SETTINGS: dict = {
    "laboratory_name": "Clinical Laboratory",
    "address": "Address Line, City",
    "phone": "0000-0000000",
    "email": "info@example.com",
    "website": "www.example.com",
    "license_number": "",
    "footer": "Thank you for choosing our laboratory.",
    "logo": "",
    "signature": "",
    "theme": "light",
    "report_prefix": "RPT",
    "report_counter": 0,
}


class SettingsManager:
    """Load, persist, and serve application settings.

    Settings are read from ``data/settings.json`` on construction. A
    default file is created if it is missing, and a malformed file is
    logged and replaced with defaults. Loaded values are merged over the
    defaults so a partial file never produces missing keys.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self._path: Path = Path(path) if path is not None else _SETTINGS_FILE
        self._settings: dict = dict(DEFAULT_SETTINGS)
        self.load()

    # ── Persistence ──────────────────────────────────────────────────

    def load(self) -> dict:
        """Load settings from disk, recovering from any failure.

        Missing file -> defaults are written. Malformed JSON -> a
        warning is logged and defaults are restored. The in-memory
        settings are always left in a valid state.
        """
        if not self._path.exists():
            self._settings = dict(DEFAULT_SETTINGS)
            self._write(self._settings)
            logger.info("Settings defaults created: %s", self._path.name)
            return self._settings

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("settings root is not an object")
        except (json.JSONDecodeError, ValueError, OSError) as exc:
            logger.warning(
                "Malformed settings restored to defaults (%s): %s",
                self._path.name,
                exc,
            )
            self._settings = dict(DEFAULT_SETTINGS)
            self._write(self._settings)
            return self._settings

        # Merge loaded values over defaults so missing keys are filled.
        self._settings = {**DEFAULT_SETTINGS, **data}
        logger.info("Settings loaded: %s", self._path.name)
        return self._settings

    def save(self) -> None:
        """Persist the current settings to ``data/settings.json``."""
        self._write(self._settings)
        logger.info("Settings saved: %s", self._path.name)

    def _write(self, settings: dict) -> None:
        """Write ``settings`` to disk as UTF-8 JSON (no logging)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=4, ensure_ascii=False)

    # ── Accessors ────────────────────────────────────────────────────

    def get(self, key: str, default=None):
        """Return a single setting value, or ``default`` if absent."""
        return self._settings.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a single setting value in memory (call :meth:`save` to persist)."""
        self._settings[key] = value

    @property
    def settings(self) -> dict:
        """Return a copy of the current settings."""
        return dict(self._settings)

    # ── Engine integration ───────────────────────────────────────────

    def get_laboratory_info(self) -> LaboratoryInfo:
        """Build a populated :class:`LaboratoryInfo` from the settings.

        Reuses :meth:`LaboratoryInfo.from_dict` so the mapping logic is
        not duplicated.
        """
        return LaboratoryInfo.from_dict(
            {
                "name": self._settings.get("laboratory_name", ""),
                "address": self._settings.get("address", ""),
                "phone": self._settings.get("phone", ""),
                "email": self._settings.get("email", ""),
                "website": self._settings.get("website", ""),
                "logo": self._settings.get("logo", ""),
                "signature": self._settings.get("signature", ""),
                "footer": self._settings.get("footer", ""),
                "license_number": self._settings.get("license_number", ""),
            }
        )
