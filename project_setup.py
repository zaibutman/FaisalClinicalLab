from pathlib import Path

# ==========================================================
# Faisal Clinical Laboratory
# Project Structure Generator
# Version: 1.0
# ==========================================================

PROJECT_NAME = "FaisalClinicalLab"

folders = [
    "app",
    "app/widgets",
    "data",
    "assets",
    "reports",
    "logs",
    "tests"
]

files = {
    "main.py": "",
    "requirements.txt": "",
    "README.md": "# Faisal Clinical Laboratory\n",
    ".gitignore": "__pycache__/\n*.pyc\nvenv/\n",

    "app/__init__.py": "",
    "app/main_window.py": "",
    "app/patient_panel.py": "",
    "app/test_panel.py": "",
    "app/result_panel.py": "",
    "app/widgets.py": "",
    "app/packages.py": "",
    "app/printer.py": "",
    "app/validation.py": "",
    "app/styles.py": "",
    "app/utils.py": "",

    "data/tests.json": "{}",
    "data/packages.json": "{}",
    "data/doctors.json": "[]",
    "data/settings.json": "{}",
}


def create_structure():
    root = Path.cwd()

    print("=" * 55)
    print("Creating Faisal Clinical Laboratory Project...")
    print("=" * 55)

    for folder in folders:
        path = root / folder
        path.mkdir(parents=True, exist_ok=True)
        print(f"[Folder] {folder}")

    for file_name, content in files.items():
        path = root / file_name
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            print(f"[File]   {file_name}")

    print("\nProject created successfully.")
    print("=" * 55)


if __name__ == "__main__":
    create_structure()