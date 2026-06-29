"""Centralized application theme for Faisal Clinical Laboratory.

Defines the color palette and a single Qt stylesheet that gives the
application a clean, professional medical-software appearance. The
stylesheet is applied once at the QApplication level by ``main.py``.
"""

# ── Color palette ──────────────────────────────────────────────────────
PRIMARY: str = "#0F4C81"
BACKGROUND: str = "#F5F7FA"
PANEL: str = "#FFFFFF"
TEXT: str = "#212121"
BORDER: str = "#D9D9D9"
SUCCESS: str = "#2E8B57"
WARNING: str = "#FFC107"
ERROR: str = "#D32F2F"

# Derived shades used for hover / pressed / focus states.
_PRIMARY_HOVER: str = "#13598F"
_PRIMARY_PRESSED: str = "#0C3E6A"
_DISABLED_BG: str = "#E6E9EE"
_DISABLED_TEXT: str = "#9AA0A6"


def load_stylesheet() -> str:
    """Return the complete application Qt stylesheet.

    Covers the core widget set used by the shell: QWidget, QMainWindow,
    QPushButton, QLabel, QGroupBox, QLineEdit, QComboBox, QScrollArea and
    QDateEdit. The result is intended to be passed to
    ``QApplication.setStyleSheet``.
    """
    return f"""
    /* ── Base ── */
    QWidget {{
        background-color: {BACKGROUND};
        color: {TEXT};
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 14px;
    }}

    QMainWindow {{
        background-color: {BACKGROUND};
    }}

    /* ── Group boxes (section containers) ── */
    QGroupBox {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 8px;
        margin-top: 14px;
        padding: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 6px;
        color: {PRIMARY};
        font-size: 15px;
        font-weight: 700;
    }}

    /* ── Labels ── */
    QLabel {{
        background-color: transparent;
        color: {TEXT};
    }}

    /* ── Buttons ── */
    QPushButton {{
        background-color: {PRIMARY};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-weight: 600;
        min-height: 20px;
    }}
    QPushButton:hover {{
        background-color: {_PRIMARY_HOVER};
    }}
    QPushButton:pressed {{
        background-color: {_PRIMARY_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {_DISABLED_BG};
        color: {_DISABLED_TEXT};
    }}

    /* ── Text inputs ── */
    QLineEdit, QComboBox, QDateEdit {{
        background-color: {PANEL};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 6px 10px;
        min-height: 20px;
        selection-background-color: {PRIMARY};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
        border: 1px solid {PRIMARY};
    }}
    QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled {{
        background-color: {_DISABLED_BG};
        color: {_DISABLED_TEXT};
    }}

    /* ── Combo / date drop-downs ── */
    QComboBox::drop-down, QDateEdit::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 24px;
        border-left: 1px solid {BORDER};
    }}
    QComboBox QAbstractItemView {{
        background-color: {PANEL};
        color: {TEXT};
        border: 1px solid {BORDER};
        selection-background-color: {PRIMARY};
        selection-color: #FFFFFF;
    }}

    /* ── Scroll areas ── */
    QScrollArea {{
        background-color: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    QScrollBar:vertical {{
        background: {BACKGROUND};
        width: 12px;
        margin: 0px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        min-height: 28px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {PRIMARY};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
