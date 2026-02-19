"""
Hazard Checker
==============
Cross-references product names against the government-sourced hazardous
substances CSV bundled with CircuLink.

Strategy (defence-in-depth):
  1. Exact case-insensitive match on common_name.
  2. Substring containment check (catches "benzene residue" → benzene).
  3. RapidFuzz token_set_ratio with a configurable threshold (default 85).
     This handles abbreviations, typos, spelling variants.
  4. CAS number match when a CAS string is detected in the product name.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path


@dataclass
class HazardResult:
    is_hazardous: bool
    matched_name: str = ""
    cas_number: str = ""
    hazard_class: str = ""
    notes: str = ""
    match_type: str = ""      # exact | substring | fuzzy | cas
    match_score: float = 0.0  # 0-100 for fuzzy, 100 for exact/substring/cas

    def __str__(self) -> str:
        if not self.is_hazardous:
            return "SAFE — No hazardous substance match found"
        return (
            f"HAZARDOUS [{self.hazard_class}] — Matched '{self.matched_name}' "
            f"via {self.match_type} (score {self.match_score:.0f}). "
            f"CAS: {self.cas_number or 'N/A'}. {self.notes}"
        )


# Pre-compiled CAS pattern: digits-digits-digit
_CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")


def _load_hazard_table() -> list[dict]:
    """Load the bundled hazardous.csv once and return as list of dicts."""
    try:
        # Try importlib.resources (preferred for installed packages)
        pkg_files = resources.files("circularlink").joinpath("data/hazardous.csv")
        text = pkg_files.read_text(encoding="utf-8")
    except Exception:
        # Fallback: traverse up from this file's location
        here = Path(__file__).parent.parent / "data" / "hazardous.csv"
        text = here.read_text(encoding="utf-8")

    reader = csv.DictReader(text.splitlines())
    rows = []
    for row in reader:
        rows.append(
            {
                "common_name": row.get("common_name", "").strip(),
                "cas_number": row.get("cas_number", "").strip(),
                "hazard_class": row.get("hazard_class", "").strip(),
                "notes": row.get("notes", "").strip(),
            }
        )
    return rows


class HazardChecker:
    """
    Checks a product name/description for hazardous substance matches.

    Instantiate once and reuse; the CSV is loaded at construction time.
    """

    def __init__(self, fuzzy_threshold: float = 85.0) -> None:
        self._threshold = fuzzy_threshold
        self._table: list[dict] = _load_hazard_table()
        # Pre-build lowered name list for fast iteration
        self._names_lower: list[str] = [
            row["common_name"].lower() for row in self._table
        ]

    def check(self, product_name: str, description: str = "") -> HazardResult:
        """
        Check product_name (and optional description) for hazardous matches.

        Returns a HazardResult with is_hazardous=False if no match is found.
        """
        from rapidfuzz import fuzz  # lazy import; rapidfuzz must be installed

        combined = f"{product_name} {description}".strip().lower()

        # ── 1. CAS number direct match ───────────────────────────────────
        cas_candidates = _CAS_RE.findall(combined)
        if cas_candidates:
            for cas in cas_candidates:
                for row in self._table:
                    if row["cas_number"] and row["cas_number"].lower() == cas.lower():
                        return HazardResult(
                            is_hazardous=True,
                            matched_name=row["common_name"],
                            cas_number=row["cas_number"],
                            hazard_class=row["hazard_class"],
                            notes=row["notes"],
                            match_type="cas",
                            match_score=100.0,
                        )

        # ── 2. Exact match on common_name ────────────────────────────────
        name_lower = product_name.strip().lower()
        for i, row_name in enumerate(self._names_lower):
            if row_name and name_lower == row_name:
                row = self._table[i]
                return HazardResult(
                    is_hazardous=True,
                    matched_name=row["common_name"],
                    cas_number=row["cas_number"],
                    hazard_class=row["hazard_class"],
                    notes=row["notes"],
                    match_type="exact",
                    match_score=100.0,
                )

        # ── 3. Substring containment ─────────────────────────────────────
        for i, row_name in enumerate(self._names_lower):
            if row_name and (row_name in combined or combined in row_name):
                row = self._table[i]
                return HazardResult(
                    is_hazardous=True,
                    matched_name=row["common_name"],
                    cas_number=row["cas_number"],
                    hazard_class=row["hazard_class"],
                    notes=row["notes"],
                    match_type="substring",
                    match_score=95.0,
                )

        # ── 4. Fuzzy match ───────────────────────────────────────────────
        best_score = 0.0
        best_idx = -1
        for i, row_name in enumerate(self._names_lower):
            if not row_name:
                continue
            score = fuzz.token_set_ratio(name_lower, row_name)
            if score > best_score:
                best_score = score
                best_idx = i

        if best_score >= self._threshold and best_idx >= 0:
            row = self._table[best_idx]
            return HazardResult(
                is_hazardous=True,
                matched_name=row["common_name"],
                cas_number=row["cas_number"],
                hazard_class=row["hazard_class"],
                notes=row["notes"],
                match_type="fuzzy",
                match_score=best_score,
            )

        return HazardResult(is_hazardous=False)

    def bulk_check(self, items: list[str]) -> list[HazardResult]:
        """Check a list of material names. Returns one result per item."""
        return [self.check(item) for item in items]
