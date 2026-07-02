"""Professional A4 PDF rendering engine for Faisal Clinical Laboratory.

Defines :class:`PDFGenerator`, the presentation layer that turns a single
:class:`~app.engine.lab_report.LabReport` into a polished, multi-page A4
laboratory report. It sits at the end of the pipeline::

    UI -> ReportBuilder -> LabReport -> PDFGenerator -> PDF file

The generator is intentionally narrow:

* Its **only** medical/structural sources are the :class:`LabReport` it is
  handed and the injected :class:`SettingsManager`. It never inspects widgets,
  the MainWindow, the MedicalKnowledge database, or the ReferenceEngine.
* It **never recomputes** anything. Units, reference ranges, and flags are
  rendered exactly as the report stores them -- no evaluation, no flagging.
* It is built on **reportlab only** and imports no PySide6, so it can run
  headless (tests, batch export, a future print engine).

Robustness is a first-class requirement: a missing logo, footer, or signature
is skipped gracefully, long text wraps, long result tables break across pages
automatically, and the engine never raises for cosmetic gaps.
"""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.paths import get_paths

if TYPE_CHECKING:  # type hints only -- no runtime coupling, no PySide6
    from app.engine.lab_report import LabReport
    from app.engine.laboratory import LaboratoryInfo
    from app.engine.patient import PatientInfo
    from app.engine.report_info import ReportInfo
    from app.engine.settings_manager import SettingsManager

logger = logging.getLogger(__name__)

# ── Palette (medical, minimal, mostly grayscale) ──────────────────────────
_INK = colors.HexColor("#1A1A1A")          # near-black body text
_HEADER_FILL = colors.HexColor("#E8E8E8")  # light gray table header
_GROUP_FILL = colors.HexColor("#F2F2F2")   # grouped-test banner
_SECTION_FILL = colors.HexColor("#F7F7F7")  # urine sub-section banner
_GRID = colors.HexColor("#BFBFBF")          # table gridlines
_MUTED = colors.HexColor("#555555")         # secondary text (footer, labels)

# ── Page geometry ─────────────────────────────────────────────────────────
_PAGE = A4
_LEFT = _RIGHT = 18 * mm
_TOP = 38 * mm   # reserves the header band drawn on every page
_BOTTOM = 32 * mm  # reserves the footer band drawn on every page

# Test-table column proportions (sum == 1.0): Test, Result, Unit, Range, Flag.
_COL_FRACTIONS = (0.28, 0.18, 0.12, 0.30, 0.12)

# SBR component labels (as the report stores them) -> reference-range keys.
# Used only to line up each grouped SBR row with its stored range; no medical
# value is computed here.
_SBR_RANGE_KEYS: dict[str, str] = {
    "Total Bilirubin": "SBR(TOTAL)",
    "Direct Bilirubin": "SBR(DIRECT)",
    "Indirect Bilirubin": "SBR(INDIRECT)",
}

# Result types whose result is a flat ``{label: value}`` mapping.
_FLAT_GROUPED = ("cbc", "semen")


class PDFGenerator:
    """Render a :class:`LabReport` to a professional A4 PDF.

    Args:
        settings_manager: Source for asset resolution and any future
            presentation settings. Laboratory *content* is taken from the
            report's own :class:`LaboratoryInfo` snapshot so an archived report
            always reprints with the details it was created under.
    """

    def __init__(self, settings_manager: SettingsManager) -> None:
        self._settings = settings_manager
        # Read-only ``data/`` directory (bundled assets), from the centralized
        # helper, used to resolve relative asset paths such as logos.
        self._data_dir = get_paths().data_dir

    # ── Public API ────────────────────────────────────────────────────

    def generate(self, report: LabReport, output_path: Path | str) -> Path:
        """Render ``report`` to ``output_path`` and return the written path.

        Builds an A4 portrait document with a repeating letterhead and footer
        and an automatically paginated result table. Never raises for missing
        optional assets (logo/footer/signature).
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lab = report.laboratory
        info = report.report_info

        doc = SimpleDocTemplate(
            str(path),
            pagesize=_PAGE,
            leftMargin=_LEFT,
            rightMargin=_RIGHT,
            topMargin=_TOP,
            bottomMargin=_BOTTOM,
            title=f"Lab Report {info.report_id}".strip(),
            author=lab.name or "",
        )

        story: list = []
        story.append(self._patient_block(report.patient, info))
        story.append(Spacer(1, 8))
        story.append(self._results_table(report.test_results))

        draw_page = partial(self._draw_furniture, lab=lab, info=info)
        doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)

        logger.info("PDF generated: %s (%d test(s))",
                    path.name, len(report.test_results))
        return path

    # ── Per-page header & footer (drawn on the canvas) ─────────────────

    def _draw_furniture(self, canvas, doc, lab: LaboratoryInfo, info: ReportInfo) -> None:
        """Draw the letterhead and footer on every page."""
        try:
            self._draw_header(canvas, lab)
            self._draw_footer(canvas, lab, info)
        except Exception as exc:  # furniture must never sink a report
            logger.warning("Page furniture render issue: %s", exc)

    def _draw_header(self, canvas, lab: LaboratoryInfo) -> None:
        """Render the laboratory letterhead within the top margin."""
        width, height = _PAGE
        top = height - 22

        text_x = _LEFT
        logo = self._image_reader(lab.logo)
        if logo is not None:
            logo_w, logo_h = 58, 50
            canvas.drawImage(
                logo, _LEFT, top - logo_h, width=logo_w, height=logo_h,
                preserveAspectRatio=True, mask="auto", anchor="nw",
            )
            text_x = _LEFT + logo_w + 12

        if lab.name:
            canvas.setFillColor(_INK)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(text_x, top - 14, lab.name)

        # Contact lines, each assembled from only the fields that are present.
        lines = [
            lab.address,
            self._join("  |  ", ("Phone: " + lab.phone) if lab.phone else "",
                       ("Email: " + lab.email) if lab.email else ""),
            self._join("  |  ", ("Web: " + lab.website) if lab.website else "",
                       ("License: " + lab.license_number) if lab.license_number else ""),
        ]
        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica", 8.5)
        y = top - 30
        for line in lines:
            if line:
                canvas.drawString(text_x, y, line)
                y -= 11

        # Divider just above the body.
        rule_y = height - _TOP + 12
        canvas.setStrokeColor(_GRID)
        canvas.setLineWidth(1)
        canvas.line(_LEFT, rule_y, width - _RIGHT, rule_y)

    def _draw_footer(self, canvas, lab: LaboratoryInfo, info: ReportInfo) -> None:
        """Render the footer band: footer text, signature, page no., date."""
        width, _height = _PAGE
        divider_y = _BOTTOM - 6
        canvas.setStrokeColor(_GRID)
        canvas.setLineWidth(0.8)
        canvas.line(_LEFT, divider_y, width - _RIGHT, divider_y)

        # Laboratory footer line (optional), centered just below the divider.
        if lab.footer:
            canvas.setFillColor(_MUTED)
            canvas.setFont("Helvetica", 7.5)
            canvas.drawCentredString(width / 2, divider_y - 12, lab.footer)

        # Signature block on the right (image optional; line + label always).
        sig_right = width - _RIGHT
        sig_left = sig_right - 130
        signature = self._image_reader(lab.signature)
        if signature is not None:
            canvas.drawImage(
                signature, sig_left, 40, width=130, height=26,
                preserveAspectRatio=True, mask="auto", anchor="sw",
            )
        canvas.setStrokeColor(_MUTED)
        canvas.setLineWidth(0.6)
        canvas.line(sig_left, 38, sig_right, 38)
        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(sig_right, 28, "Authorized Signature")

        # Generated date (from the report) on the left; page number centered.
        if info.created_at:
            canvas.drawString(_LEFT, 28, f"Generated: {info.created_at}")
        canvas.drawCentredString(width / 2, 16, f"Page {canvas.getPageNumber()}")

    # ── Patient information block ──────────────────────────────────────

    def _patient_block(self, patient: PatientInfo, info: ReportInfo) -> Table:
        """Build the patient/report metadata grid as a borderless table."""
        label = self._style("label", 8, _MUTED, bold=True)
        value = self._style("value", 9, _INK)
        title = self._style("ptitle", 9, _INK, bold=True)

        # (label, value) pairs laid out two-per-row.
        pairs = [
            ("Report ID", info.report_id),
            ("Status", info.status),
            ("Patient Name", patient.name),
            ("Referring Doctor", patient.doctor),
            ("Age", patient.age),
            ("Collection Date", patient.date),
            ("Gender", patient.gender),
            ("Created Date", info.created_at),
            ("Phone", patient.phone),
            ("", ""),
        ]

        rows = [[self._p("PATIENT INFORMATION", title), "", "", ""]]
        for i in range(0, len(pairs), 2):
            la, va = pairs[i]
            lb, vb = pairs[i + 1]
            rows.append([
                self._p(la, label), self._p(va, value),
                self._p(lb, label), self._p(vb, value),
            ])

        content = _PAGE[0] - _LEFT - _RIGHT
        widths = [content * f for f in (0.18, 0.32, 0.18, 0.32)]
        table = Table(rows, colWidths=widths, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_FILL),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return table

    # ── Results table ─────────────────────────────────────────────────

    def _results_table(self, results: list) -> Table:
        """Build the paginated result table from ``LabReport.test_results``."""
        header = self._style("th", 8.5, _INK, bold=True)
        data = [[
            self._p("Test", header), self._p("Result", header),
            self._p("Unit", header), self._p("Reference Range", header),
            self._p("Flag", header),
        ]]
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_FILL),
            ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]

        row = 1
        for result in results:
            for cells, kind in self._rows_for(result):
                data.append(cells)
                if kind == "group":
                    style.append(("SPAN", (0, row), (-1, row)))
                    style.append(("BACKGROUND", (0, row), (-1, row), _GROUP_FILL))
                elif kind == "section":
                    style.append(("SPAN", (0, row), (-1, row)))
                    style.append(("BACKGROUND", (0, row), (-1, row), _SECTION_FILL))
                row += 1

        if not results:
            data.append([self._p("No tests recorded.", self._style("muted", 8, _MUTED)),
                         "", "", "", ""])
            style.append(("SPAN", (0, row), (-1, row)))

        content = _PAGE[0] - _LEFT - _RIGHT
        widths = [content * f for f in _COL_FRACTIONS]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle(style))
        return table

    def _rows_for(self, tr: Any) -> list[tuple[list, str]]:
        """Return the table rows for one :class:`TestResult`.

        Dispatch is by the result's stored ``test_type`` with an isinstance
        fallback, so a grouped result is always rendered as rows -- never as
        raw JSON. Each tuple is ``(cells, kind)`` where ``kind`` drives styling.
        """
        ttype = (tr.test_type or "").lower()
        result = tr.result

        if ttype == "sbr" or (ttype == "" and self._looks_like_sbr(result)):
            return self._sbr_rows(tr)
        if ttype == "urine" or (ttype == "" and self._is_nested(result)):
            return self._urine_rows(tr)
        if ttype in _FLAT_GROUPED or (ttype == "" and isinstance(result, dict)):
            return self._flat_group_rows(tr)
        return self._simple_row(tr)

    def _simple_row(self, tr: Any) -> list[tuple[list, str]]:
        """One row for a scalar-valued test (numeric, dropdown, blood group)."""
        cell = self._style("cell", 8.5, _INK)
        return [([
            self._p(tr.test_name, self._style("cellb", 8.5, _INK, bold=True)),
            self._p(self._fmt(tr.result), cell),
            self._p(tr.unit, cell),
            self._p(self._range_text(tr.reference_range), cell),
            self._p(self._flag_text(tr.flag), cell),
        ], "data")]

    def _flat_group_rows(self, tr: Any) -> list[tuple[list, str]]:
        """Grouped rows for a flat ``{label: value}`` result (CBC, semen)."""
        rows: list[tuple[list, str]] = [self._group_header(tr.test_name)]
        result = tr.result if isinstance(tr.result, dict) else {}
        cell = self._style("cell", 8.5, _INK)
        for label, value in result.items():
            rows.append(([
                self._p("    " + str(label), cell),
                self._p(self._fmt(value), cell),
                self._p(tr.unit, cell),
                self._p("", cell),
                self._p("", cell),
            ], "data"))
        return rows

    def _urine_rows(self, tr: Any) -> list[tuple[list, str]]:
        """Grouped rows for a nested ``{section: {label: value}}`` result."""
        rows: list[tuple[list, str]] = [self._group_header(tr.test_name)]
        result = tr.result if isinstance(tr.result, dict) else {}
        cell = self._style("cell", 8.5, _INK)
        section_style = self._style("sect", 8.5, _MUTED, bold=True)
        for section, fields in result.items():
            rows.append(([self._p(str(section), section_style), "", "", "", ""], "section"))
            if isinstance(fields, dict):
                for label, value in fields.items():
                    rows.append(([
                        self._p("    " + str(label), cell),
                        self._p(self._fmt(value), cell),
                        self._p("", cell), self._p("", cell), self._p("", cell),
                    ], "data"))
        return rows

    def _sbr_rows(self, tr: Any) -> list[tuple[list, str]]:
        """Grouped rows for SBR: Total / Direct / Indirect, each with its flag."""
        rows: list[tuple[list, str]] = [self._group_header(tr.test_name)]
        result = tr.result if isinstance(tr.result, dict) else {}
        ranges = tr.reference_range if isinstance(tr.reference_range, dict) else {}
        flags = tr.flag if isinstance(tr.flag, dict) else {}
        cell = self._style("cell", 8.5, _INK)
        for label, value in result.items():
            component = _SBR_RANGE_KEYS.get(label)
            rng = self._range_text(ranges.get(component)) if component else ""
            rows.append(([
                self._p("    " + str(label), cell),
                self._p(self._fmt(value), cell),
                self._p(tr.unit, cell),
                self._p(rng, cell),
                self._p(self._flag_text(flags.get(label, "")), cell),
            ], "data"))
        return rows

    def _group_header(self, name: str) -> tuple[list, str]:
        """A banner row carrying a grouped test's name."""
        return ([self._p(name, self._style("grp", 9, _INK, bold=True)),
                 "", "", "", ""], "group")

    # ── Value formatting (display only -- never recomputes) ────────────

    @staticmethod
    def _fmt(value: Any) -> str:
        """Render a scalar result value as display text."""
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _flag_text(flag: Any) -> str:
        """Render a flag exactly as stored (no evaluation)."""
        if flag is None or isinstance(flag, dict):
            return ""
        return str(flag)

    @staticmethod
    def _range_text(reference_range: Any) -> str:
        """Render a reference range as stored.

        Accepts the catalog's shapes verbatim: a plain string, or a list of
        equivalent phrasings (the first usable one is shown). Mappings and
        empties render as an empty cell. Nothing is parsed or computed.
        """
        if isinstance(reference_range, str):
            return reference_range.strip()
        if isinstance(reference_range, (list, tuple)):
            for variant in reference_range:
                if isinstance(variant, str) and variant.strip():
                    return variant.strip()
        return ""

    # ── reportlab helpers ──────────────────────────────────────────────

    @staticmethod
    def _style(name: str, size: float, color, *, bold: bool = False) -> ParagraphStyle:
        """Build a small paragraph style for a table cell."""
        return ParagraphStyle(
            name,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            leading=size + 2,
            textColor=color,
            alignment=TA_LEFT,
        )

    @staticmethod
    def _p(text: Any, style: ParagraphStyle) -> Paragraph:
        """Wrap ``text`` in a Paragraph (XML-escaped) so long values wrap."""
        return Paragraph(escape("" if text is None else str(text)), style)

    @staticmethod
    def _join(sep: str, *parts: str) -> str:
        """Join only the non-empty ``parts`` with ``sep``."""
        return sep.join(p for p in parts if p)

    def _image_reader(self, path: Any) -> ImageReader | None:
        """Return an :class:`ImageReader` for ``path``, or ``None`` if unusable.

        Relative paths are resolved against the working directory and the
        project ``data/`` directory. Any failure (missing file, bad image)
        yields ``None`` so the caller continues without the asset.
        """
        if not path or not isinstance(path, str):
            return None
        try:
            candidate = Path(path)
            if not candidate.is_absolute():
                for base in (Path.cwd(), self._data_dir):
                    resolved = base / candidate
                    if resolved.exists():
                        candidate = resolved
                        break
            if not candidate.exists():
                return None
            return ImageReader(str(candidate))
        except Exception as exc:
            logger.warning("Could not load image '%s': %s", path, exc)
            return None

    # ── Small predicates for the isinstance fallbacks ──────────────────

    @staticmethod
    def _is_nested(result: Any) -> bool:
        """True when ``result`` is a ``{section: {label: value}}`` mapping."""
        return isinstance(result, dict) and any(
            isinstance(v, dict) for v in result.values()
        )

    @staticmethod
    def _looks_like_sbr(result: Any) -> bool:
        """True when ``result`` looks like an SBR component mapping."""
        return isinstance(result, dict) and any(
            k in _SBR_RANGE_KEYS for k in result
        )
