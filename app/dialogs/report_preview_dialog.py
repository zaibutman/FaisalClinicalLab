"""Report Preview dialog for Faisal Clinical Laboratory.

Defines :class:`ReportPreviewDialog`, a modal window that previews an
*already generated* PDF inside the application (Version 1.2.0). It is a pure
viewer: it never builds a report and never writes, prints, or chooses files.
The Print and Save toolbar actions only emit signals -- :attr:`print_requested`
and :attr:`save_requested` -- so the surrounding application can decide what to
do later.

The viewer degrades gracefully across environments:

* If ``QtPdf`` / ``QtPdfWidgets`` are present, a native ``QPdfView`` is used.
* Otherwise it falls back to ``QWebEngineView``.
* If neither is available, a plain message is shown -- the dialog still opens
  and never crashes.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

_DIALOG_WIDTH: int = 1200
_DIALOG_HEIGHT: int = 850
_ZOOM_STEP: int = 20
_ZOOM_MIN: int = 25
_ZOOM_MAX: int = 400
_ZOOM_DEFAULT: int = 100

_NO_BACKEND_MESSAGE: str = "This system cannot preview PDF files."


class ReportPreviewDialog(QDialog):
    """Modal preview of a generated PDF with a viewer toolbar.

    Signals:
        print_requested(): emitted when the Print button is pressed. The dialog
            performs no printing itself.
        save_requested():  emitted when the Save PDF button is pressed. The
            dialog performs no saving itself.
    """

    print_requested = Signal()
    save_requested = Signal()

    def __init__(self, pdf_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Report Preview")
        self.resize(_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.setMinimumSize(640, 480)
        self.setSizeGripEnabled(True)

        # Viewer backend state. Populated by _create_viewer().
        self._backend: str = "none"
        self._zoom: int = _ZOOM_DEFAULT
        self._pdf_path: Path | None = None
        self._doc = None          # QPdfDocument (qtpdf backend)
        self._view = None         # QPdfView (qtpdf backend)
        self._web = None          # QWebEngineView (web backend)
        self._QPdfView = None     # cached enum holders
        self._QPdfDocument = None

        self._build_ui()
        # Load immediately so the dialog shows content the moment it opens.
        self.load_pdf(pdf_path)

    # ── UI construction ───────────────────────────────────────────────

    def _build_ui(self) -> None:
        """Assemble the toolbar (top) and the PDF viewer (center)."""
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_toolbar())

        viewer = self._create_viewer()
        root.addWidget(viewer, stretch=1)

    def _build_toolbar(self) -> QHBoxLayout:
        """Build the action toolbar row."""
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._print_btn = self._tool_button("Print", self._on_print)
        self._save_btn = self._tool_button("Save PDF", self._on_save)
        bar.addWidget(self._print_btn)
        bar.addWidget(self._save_btn)

        bar.addSpacing(16)
        bar.addWidget(self._tool_button("Zoom In", self._on_zoom_in))
        bar.addWidget(self._tool_button("Zoom Out", self._on_zoom_out))
        bar.addWidget(self._tool_button("Fit Width", self.fit_width))
        bar.addWidget(self._tool_button("Fit Page", self.fit_page))

        self._zoom_label = QLabel(f"{self._zoom}%")
        self._zoom_label.setMinimumWidth(70)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar.addWidget(self._zoom_label)

        bar.addStretch(1)
        bar.addWidget(self._tool_button("Close", self.close))
        return bar

    def _tool_button(self, text: str, handler) -> QPushButton:
        """Create a toolbar push button wired to ``handler``."""
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(handler)
        return button

    def _create_viewer(self) -> QWidget:
        """Create the best available PDF viewer widget.

        Tries QtPdf, then QWebEngineView, then a plain message label. Returns
        the widget to place in the center of the dialog and records the chosen
        backend on ``self._backend``.
        """
        # 1) Native Qt PDF viewer.
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtPdfWidgets import QPdfView

            self._QPdfDocument = QPdfDocument
            self._QPdfView = QPdfView
            self._doc = QPdfDocument(self)
            self._view = QPdfView(self)
            self._view.setDocument(self._doc)
            self._view.setPageMode(QPdfView.PageMode.MultiPage)
            self._backend = "qtpdf"
            return self._view
        except Exception:  # QtPdf not installed/usable -- try the next backend
            self._doc = self._view = None

        # 2) Chromium-based fallback.
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self._web = QWebEngineView(self)
            settings = self._web.settings()
            attr = settings.WebAttribute
            settings.setAttribute(attr.PluginsEnabled, True)
            if hasattr(attr, "PdfViewerEnabled"):
                settings.setAttribute(attr.PdfViewerEnabled, True)
            self._backend = "web"
            return self._web
        except Exception:  # neither backend available
            self._web = None

        # 3) No backend -- show a graceful message; the dialog still opens.
        self._backend = "none"
        label = QLabel(_NO_BACKEND_MESSAGE)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    # ── Public API ────────────────────────────────────────────────────

    def load_pdf(self, path: Path | str) -> None:
        """Load ``path`` into the active viewer.

        Logs ``PDF loaded`` on success and ``Preview failed`` on any error or
        when no viewer backend is available. Never raises.
        """
        self._pdf_path = Path(path)
        try:
            if self._backend == "qtpdf":
                self._doc.load(str(self._pdf_path))
                if self._doc.status() == self._QPdfDocument.Status.Ready:
                    self.set_zoom(_ZOOM_DEFAULT)
                    logger.info("PDF loaded")
                else:
                    logger.warning("Preview failed: document not ready")
            elif self._backend == "web":
                from PySide6.QtCore import QUrl

                self._web.load(QUrl.fromLocalFile(str(self._pdf_path)))
                logger.info("PDF loaded")
            else:
                logger.warning("Preview failed: no PDF preview backend")
        except Exception as exc:
            logger.warning("Preview failed: %s", exc)

    def set_zoom(self, percent) -> None:
        """Set an absolute zoom level (in percent), clamped to a sane range."""
        try:
            value = int(percent)
        except (TypeError, ValueError):
            return
        value = max(_ZOOM_MIN, min(value, _ZOOM_MAX))
        self._zoom = value

        if self._backend == "qtpdf":
            self._view.setZoomMode(self._QPdfView.ZoomMode.Custom)
            self._view.setZoomFactor(value / 100.0)
        elif self._backend == "web":
            self._web.setZoomFactor(value / 100.0)

        self._set_zoom_label(f"{value}%")

    def fit_width(self) -> None:
        """Fit the page to the viewer width."""
        if self._backend == "qtpdf":
            self._view.setZoomMode(self._QPdfView.ZoomMode.FitToWidth)
            self._set_zoom_label("Fit Width")
        elif self._backend == "web":
            self._web.setZoomFactor(1.0)
            self._set_zoom_label("Fit Width")

    def fit_page(self) -> None:
        """Fit the whole page within the viewer."""
        if self._backend == "qtpdf":
            self._view.setZoomMode(self._QPdfView.ZoomMode.FitInView)
            self._set_zoom_label("Fit Page")
        elif self._backend == "web":
            self._web.setZoomFactor(1.0)
            self._set_zoom_label("Fit Page")

    # ── Button handlers ───────────────────────────────────────────────

    def _on_print(self) -> None:
        """Emit :attr:`print_requested` -- the dialog prints nothing itself."""
        self.print_requested.emit()

    def _on_save(self) -> None:
        """Emit :attr:`save_requested` -- the dialog saves nothing itself."""
        self.save_requested.emit()

    def _on_zoom_in(self) -> None:
        self.set_zoom(self._zoom + _ZOOM_STEP)

    def _on_zoom_out(self) -> None:
        self.set_zoom(self._zoom - _ZOOM_STEP)

    # ── Helpers / lifecycle ───────────────────────────────────────────

    def _set_zoom_label(self, text: str) -> None:
        label = getattr(self, "_zoom_label", None)
        if label is not None:
            label.setText(text)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
        """Release the document so the temporary file can be deleted."""
        try:
            if self._backend == "qtpdf" and self._doc is not None:
                self._doc.close()
        except Exception:
            pass
        super().closeEvent(event)
