"""Application metadata for Faisal Clinical Laboratory.

Single source of truth for the application name, version, and author.
Imported wherever the title or version needs to be displayed.
"""

APP_NAME: str = "Faisal Clinical Laboratory"
APP_VERSION: str = "0.8.0"
APP_AUTHOR: str = "Zaib Utman"


def get_window_title() -> str:
    """Return the formatted main-window title.

    Example:
        "Faisal Clinical Laboratory v0.1.0"
    """
    return f"{APP_NAME} v{APP_VERSION}"
