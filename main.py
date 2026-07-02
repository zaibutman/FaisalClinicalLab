"""Application entry point for Faisal Clinical Laboratory.

Bootstraps logging, creates the QApplication, applies the centralized
stylesheet, builds and centers the main window, optionally applies the
application icon, and starts the Qt event loop. Contains no business
logic (Version 0.1.0).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.paths import get_paths
from app.styles import load_stylesheet
from app.version import get_window_title

# All paths come from the centralized helper: writable data (logs) lives under
# %LOCALAPPDATA%, read-only resources (the icon) load from the bundle/project.
_PATHS = get_paths()
LOG_DIR: Path = _PATHS.logs_dir
LOG_FILE: Path = _PATHS.log_file
ICON_FILE: Path = _PATHS.assets_dir / "icon.ico"

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure file-based logging to ``<LocalAppData>/logs/application.log``."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def center_window(window: MainWindow) -> None:
    """Center ``window`` on the primary screen's available geometry."""
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    available = screen.availableGeometry()
    frame = window.frameGeometry()
    frame.moveCenter(available.center())
    window.move(frame.topLeft())


def main() -> int:
    """Run the application and return the Qt process exit code."""
    configure_logging()
    logger.info("Application started")

    # One-time, non-destructive migration of settings/reports from an older
    # beside-the-executable install into %LOCALAPPDATA%. Runs before any
    # SettingsManager/ReportStorage is constructed so migrated data is loaded.
    _PATHS.migrate_legacy_data()

    app = QApplication(sys.argv)
    app.setApplicationName(get_window_title())
    app.setStyleSheet(load_stylesheet())

    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))
        logger.info("Application icon applied: %s", ICON_FILE.name)

    window = MainWindow()
    if ICON_FILE.exists():
        window.setWindowIcon(QIcon(str(ICON_FILE)))
    center_window(window)
    window.show()

    exit_code = app.exec()

    logger.info("Application closed")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
