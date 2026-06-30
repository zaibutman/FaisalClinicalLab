"""Reference range engine for Faisal Clinical Laboratory.

Defines :class:`ReferenceEngine`, which interprets the free-text reference
ranges stored in the medical knowledge database and decides whether a numeric
result is *High*, *Low*, or *Normal*. The engine is the single place that
understands the many ways the Master Test Catalog writes a range, e.g.::

    "80-------140 mg/dl"          two-sided    -> (80.0, 140.0)
    "More Than 35 mg/dl"          lower bound  -> (35.0, None)
    "Less Than 150 mg/dl"         upper bound  -> (None, 150.0)
    "UP TO 40 U/L"                upper bound  -> (None, 40.0)
    "Male 3.0--6.8  Female 3.0--5.7"  sex-split, selected by patient sex
    {"SBR(TOTAL)": [...], "SBR(DIRECT)": [...]}   per-component mapping

This module is pure Python -- it imports no UI, no widgets, and no report
builder -- so it can be shared by the result widgets, the report builder, and
printing (Version 0.9.0). It mirrors the conventions of
:mod:`app.engine.medical_knowledge` and :mod:`app.engine.package_resolver`:

* It **never invents medical values.** Every bound it returns is parsed
  verbatim from a string the catalog already stores. When a range cannot be
  parsed, the engine returns no flag rather than guessing.
* It **never raises.** A malformed value, an unparseable range, or an unknown
  test yields an empty flag so the application keeps running.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.engine.medical_knowledge import MedicalKnowledge

logger = logging.getLogger(__name__)

# ── Flag constants ───────────────────────────────────────────────────────
# These are the only values evaluate() emits. NONE means "no judgement was
# possible" (unknown test, no catalog range, non-numeric result, or a range
# the engine could not parse) -- it is never a medical statement.
FLAG_HIGH: str = "High"
FLAG_LOW: str = "Low"
FLAG_NORMAL: str = "Normal"
FLAG_NONE: str = ""

# A single non-negative number, e.g. 80, 3.0, .5, 140. No sign is matched on
# purpose: reference values are never negative, and the catalog separates the
# two ends of a range with runs of dashes ("80-------140") that must not be
# read as a minus sign on the upper bound.
_NUMBER = re.compile(r"\d*\.?\d+")

# Phrases that mark a one-sided range. Order matters: the longer/explicit
# variants are listed first so "greater than or equal" is matched before
# "greater than".
_LOWER_ONLY = ("more than", "greater than", "atleast", "at least", "above", "minimum")
_UPPER_ONLY = ("less than", "lessthan", "up to", "upto", "below", "under", "maximum", "max")


class ReferenceEngine:
    """Flag laboratory results against the catalog's reference ranges.

    The engine reads ranges through a :class:`MedicalKnowledge` instance
    (injected for testability, constructed by default). It performs no I/O of
    its own and holds no result state -- :meth:`evaluate` is a pure function of
    its arguments and the loaded catalog.
    """

    def __init__(self, knowledge: MedicalKnowledge | None = None) -> None:
        self._knowledge: MedicalKnowledge = knowledge or MedicalKnowledge()

    # ── Public API ───────────────────────────────────────────────────────

    def evaluate(
        self,
        test_id: str,
        value: Any,
        *,
        sex: str | None = None,
        component: str | None = None,
    ) -> str:
        """Return the flag for ``value`` against ``test_id``'s reference range.

        Args:
            test_id: Catalog test id (e.g. ``"creatinine"``).
            value: The measured result. Numbers and numeric strings are
                evaluated; anything non-numeric yields :data:`FLAG_NONE`.
            sex: ``"M"``/``"F"`` (or ``"male"``/``"female"``) used to pick the
                correct half of a sex-split range. Ignored when not applicable.
            component: For tests whose range is a ``{component: [...]}`` mapping
                (e.g. SBR), the component to evaluate, such as ``"SBR(TOTAL)"``.

        Returns:
            :data:`FLAG_HIGH`, :data:`FLAG_LOW`, :data:`FLAG_NORMAL`, or
            :data:`FLAG_NONE` when no judgement is possible. Never raises.
        """
        try:
            number = self._to_number(value)
            if number is None:
                return FLAG_NONE

            raw = self._knowledge.get_reference_range(test_id)
            bounds = self._bounds_from_raw(raw, sex=sex, component=component)
            if bounds is None:
                return FLAG_NONE

            low, high = bounds
            return self.flag_for(number, low, high)
        except Exception as exc:  # never propagate an evaluation failure
            logger.warning("Reference evaluation failed for '%s': %s", test_id, exc)
            return FLAG_NONE

    @staticmethod
    def flag_for(value: float, low: float | None, high: float | None) -> str:
        """Classify ``value`` given optional ``low``/``high`` bounds.

        Bounds are inclusive: a value equal to a bound is :data:`FLAG_NORMAL`.
        Returns :data:`FLAG_NONE` when both bounds are missing.
        """
        if low is None and high is None:
            return FLAG_NONE
        if low is not None and value < low:
            return FLAG_LOW
        if high is not None and value > high:
            return FLAG_HIGH
        return FLAG_NORMAL

    def parse_range(self, text: str) -> tuple[float | None, float | None] | None:
        """Parse one reference-range string into ``(low, high)`` bounds.

        Returns ``None`` when the string contains no usable number. ``low`` or
        ``high`` may individually be ``None`` for one-sided ranges. Numbers are
        taken verbatim from the text; none are computed or inferred.
        """
        if not isinstance(text, str):
            return None

        lowered = text.lower()
        numbers = [float(m) for m in _NUMBER.findall(text)]
        if not numbers:
            return None

        if any(kw in lowered for kw in _UPPER_ONLY):
            return (None, numbers[0])
        if any(kw in lowered for kw in _LOWER_ONLY):
            return (numbers[0], None)

        if len(numbers) >= 2:
            low, high = numbers[0], numbers[1]
            if low > high:
                low, high = high, low
            return (low, high)

        # A lone number with no qualifying phrase is ambiguous; refuse to guess.
        return None

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _to_number(value: Any) -> float | None:
        """Coerce a result value to ``float``, or ``None`` if not numeric.

        Booleans are rejected (``True`` is not a measurement). Strings are
        parsed only when they are wholly numeric, e.g. ``"1.0"`` -- a value
        like ``"Positive"`` yields ``None`` rather than a fabricated number.
        """
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None

    def _bounds_from_raw(
        self,
        raw: Any,
        *,
        sex: str | None,
        component: str | None,
    ) -> tuple[float | None, float | None] | None:
        """Reduce a stored ``reference_range`` value to ``(low, high)`` bounds.

        Handles the three shapes the catalog uses: ``None`` (no range), a list
        of variant strings, and a ``{component: [variants]}`` mapping. Returns
        ``None`` when nothing usable can be extracted.
        """
        if raw is None:
            return None

        # Per-component mapping (e.g. SBR(TOTAL)/SBR(DIRECT)).
        if isinstance(raw, dict):
            variants = self._select_component(raw, component)
            return self._bounds_from_variants(variants, sex)

        if isinstance(raw, list):
            return self._bounds_from_variants(raw, sex)

        if isinstance(raw, str):
            return self._bounds_from_variants([raw], sex)

        return None

    @staticmethod
    def _select_component(mapping: dict, component: str | None) -> list:
        """Return the variant list for ``component`` from a range mapping."""
        if component is not None and component in mapping:
            value = mapping[component]
        elif mapping:
            # No component requested: fall back to the first entry in order.
            value = next(iter(mapping.values()))
        else:
            return []
        return value if isinstance(value, list) else [value]

    def _bounds_from_variants(
        self,
        variants: list,
        sex: str | None,
    ) -> tuple[float | None, float | None] | None:
        """Parse the first usable variant string into bounds.

        Catalog entries often list several phrasings of the same range; the
        first one that parses wins. Sex-split phrasings are narrowed to the
        relevant half before parsing.
        """
        for variant in variants:
            if not isinstance(variant, str):
                continue
            text = self._slice_for_sex(variant, sex)
            bounds = self.parse_range(text)
            if bounds is not None:
                return bounds
        return None

    @staticmethod
    def _slice_for_sex(text: str, sex: str | None) -> str:
        """Narrow a sex-split range string to the half matching ``sex``.

        Many catalog strings pack both sexes into one line, e.g.
        ``"Male 3.0--6.8 mg/dl  Female 3.0--5.7 mg/dl"`` or ``"M: 3.0--7.0"``.
        When ``sex`` is given and both markers are present, the substring for
        the other sex is removed so :meth:`parse_range` sees only the relevant
        numbers. Returns ``text`` unchanged when it is not sex-split or ``sex``
        is unknown.
        """
        if not sex:
            return text

        normalized = sex.strip().lower()
        if normalized in ("m", "male"):
            want, other = "male", "female"
        elif normalized in ("f", "female"):
            want, other = "female", "male"
        else:
            return text

        lowered = text.lower()
        want_at = lowered.find(want)
        other_at = lowered.find(other)
        if want_at == -1 or other_at == -1:
            # Not a both-sexes string -- nothing to slice.
            return text

        # Keep the segment that starts at the wanted marker and stops before
        # the other sex's marker (handling either ordering in the string).
        if want_at < other_at:
            return text[want_at:other_at]
        return text[want_at:]
