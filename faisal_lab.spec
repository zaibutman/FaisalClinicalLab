# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Faisal Clinical Laboratory (Task R1).

Builds a ONEDIR Windows executable that behaves exactly like ``python main.py``.

Why onedir (not onefile):
    The application persists state on disk -- ``data/settings.json`` (which
    holds the report counter and laboratory branding) and the ``reports/``
    folder (saved reports + History discovery). A onefile build unpacks to a
    temporary directory that is deleted on exit, which would reset numbering,
    lose settings, and leave History empty on every launch. A onedir build
    keeps a real, persistent folder next to the executable, so all state
    survives restarts. Reliability wins.

Why no source changes are needed:
    Every module resolves its data/reports paths relative to its own
    ``__file__`` (e.g. ``Path(__file__).resolve().parents[2] / "data"``). In a
    frozen onedir build PyInstaller sets each module's ``__file__`` inside the
    bundle root (``_internal``), so bundling ``data/``, ``reports/`` and
    ``docs/`` at that root makes the existing path logic resolve correctly with
    no code modification.

QtWebEngine is excluded on purpose: it is only the *fallback* PDF backend in
the preview dialog. The primary QtPdf backend is bundled, so preview and print
work fully; excluding WebEngine avoids a very large, fragile dependency
(QtWebEngineProcess) without changing observable behavior.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

# ── Runtime data bundled at the bundle root (mirrors the source layout) ──────
# Read-only catalog/config plus the writable output folders. The trailing
# name is the destination directory *inside* the bundle root.
datas = [
    ("data", "data"),      # tests.json, packages.json, medical_knowledge.json,
                           # settings.json, doctors.json
    ("reports", "reports"),  # default save location + History scan root
    ("docs", "docs"),        # Master Test Catalog (reference material)
    ("assets", "assets"),    # icon / logo / signature placeholders
]
binaries = []
hiddenimports = [
    # Imported lazily inside methods, so make the collection explicit.
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPrintSupport",
]

# ReportLab ships font metrics / data used by the PDF engine -- bundle them all.
rl_datas, rl_binaries, rl_hiddenimports = collect_all("reportlab")
datas += rl_datas
binaries += rl_binaries
hiddenimports += rl_hiddenimports

# Optional application icon (only if the project actually provides one).
_icon_path = Path("assets") / "icon.ico"
icon = str(_icon_path) if _icon_path.exists() else None


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,      # onedir: binaries live alongside, not in the EXE
    name="FaisalClinicalLaboratory",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,              # GUI app -- no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FaisalClinicalLaboratory",
)
