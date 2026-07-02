# Building Faisal Clinical Laboratory (Windows Executable)

This document describes how to package the application into a standalone
Windows executable using **PyInstaller**. Packaging does not change any
application behaviour — the executable launches exactly like `python main.py`.

---

## Prerequisites

- **Windows 10/11 (64-bit)**
- **Python 3.14** (the project is developed and packaged on 3.14.6)
- The project's virtual environment with all dependencies installed:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` includes the build-only dependency **PyInstaller 6.21.0**
in addition to the runtime dependencies (PySide6, reportlab).

---

## How to build

From the project root, run the build script with the virtual-environment
Python:

```bat
.venv\Scripts\python.exe build.py
```

The script will:

1. remove any previous `build/` directory
2. remove any previous `dist/` directory
3. remove `__pycache__/` directories (excluding `.venv`)
4. run PyInstaller against `faisal_lab.spec`
5. print **BUILD SUCCEEDED** (with the executable path) or **BUILD FAILED**

A build takes roughly 1–2 minutes on a typical machine.

---

## How to rebuild

Just run the same command again — the script always cleans previous artifacts
first, so every build is fresh:

```bat
.venv\Scripts\python.exe build.py
```

If you prefer to invoke PyInstaller directly:

```bat
.venv\Scripts\python.exe -m PyInstaller --noconfirm faisal_lab.spec
```

---

## How to clean

To remove build artifacts **without** rebuilding:

```bat
.venv\Scripts\python.exe build.py --clean
```

This deletes `build/`, `dist/`, and `__pycache__/` directories.

---

## Where the executable appears

After a successful build:

```
dist\FaisalClinicalLaboratory\FaisalClinicalLaboratory.exe
```

Run that `.exe` to launch the application. **Python is not required** on the
target machine — everything needed is bundled.

To deliver the application, copy the **entire**
`dist\FaisalClinicalLaboratory\` folder (the `.exe` alone is not sufficient).

---

## Expected folder structure

The build produces a **onedir** bundle:

```
dist\
└── FaisalClinicalLaboratory\
    ├── FaisalClinicalLaboratory.exe      ← launch this
    └── _internal\
        ├── data\                          ← tests.json, packages.json,
        │                                     medical_knowledge.json,
        │                                     settings.json, doctors.json
        ├── reports\                        ← saved reports (default location)
        ├── docs\                           ← Master Test Catalog
        ├── assets\                         ← icon / logo / signature placeholders
        ├── logs\                           ← application.log (created at runtime)
        ├── PySide6\                        ← Qt libraries + plugins (incl. QtPdf)
        ├── reportlab\                      ← PDF engine + fonts
        └── python314.dll, *.pyd, *.dll ...  ← Python runtime + bundled libs
```

### Why onedir (not onefile)

The application persists state on disk:

- `data/settings.json` — holds the **report counter** and laboratory branding
- `reports/` — saved reports and the folder that **History** scans

A **onefile** build unpacks everything to a temporary directory that is deleted
when the app exits, which would reset report numbering, lose settings, and leave
History empty on every launch. A **onedir** build keeps a real, persistent
`_internal\` folder next to the executable, so all state survives restarts.
Reliability is the priority, so **onedir** is used.

Because the application resolves its data/report paths relative to its own
module location, bundling `data/`, `reports/`, and `docs/` at the bundle root
makes the existing path logic work with **no source-code changes**.

### Notes

- **QtWebEngine is intentionally excluded.** It is only the fallback PDF preview
  backend; the primary **QtPdf** backend is bundled, so preview and printing work
  fully. Excluding WebEngine keeps the bundle small and reliable.
- Writable state (`settings.json`, `reports\`, `logs\`) is stored under
  `_internal\`. Install the app in a **user-writable** location (e.g. a folder in
  the user profile or a portable drive), not under `C:\Program Files`, so it can
  save reports and update settings.
- If `assets\icon.ico` exists it is used as the executable icon; otherwise the
  build proceeds with the default icon.
