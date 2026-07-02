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
    """Center ``window`` on the primary screen's available geometry.

    If the window is larger than the available area (e.g. a 1400x850 default on
    a 1366x768 laptop), it is first shrunk to fit so the native title bar is
    never pushed off-screen, then clamped fully inside the work area. The
    window stays resizable and maximizable.
    """
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    available = screen.availableGeometry()

    # Shrink to fit the work area if the default size is too large for it,
    # accounting for the window-frame decorations (title bar + borders) so the
    # whole window fits and the native title bar stays fully reachable.
    frame = window.frameGeometry()
    deco_w = max(0, frame.width() - window.width())
    deco_h = max(0, frame.height() - window.height())
    fitted_w = min(window.width(), available.width() - deco_w)
    fitted_h = min(window.height(), available.height() - deco_h)
    if fitted_w != window.width() or fitted_h != window.height():
        window.resize(fitted_w, fitted_h)

    frame = window.frameGeometry()
    frame.moveCenter(available.center())
    # Keep the whole frame (including the title bar) inside the work area.
    top_left = frame.topLeft()
    top_left.setX(max(available.left(), min(top_left.x(), available.right() - frame.width() + 1)))
    top_left.setY(max(available.top(), min(top_left.y(), available.bottom() - frame.height() + 1)))
    window.move(top_left)


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
    # Show first so the window-frame decorations are realized, then fit/center
    # using accurate frame geometry (keeps the native title bar fully on-screen).
    window.show()
    center_window(window)

    exit_code = app.exec()

    logger.info("Application closed")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
