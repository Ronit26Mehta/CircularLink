"""
Fuzzy NLP Matcher & Weighted Scorer
=====================================
Implements the hybrid recommendation engine:

  final_score = (0.7 × fuzzy_score) + (0.3 × location_score)

Fuzzy scoring uses RapidFuzz with a combination of:
  - token_set_ratio   : handles word-order & subset variations
  - token_sort_ratio  : robust to word reordering
  - partial_ratio     : catches partial name matches

The ensemble of these three is averaged to produce a single fuzzy_score in [0, 1].

Location scoring delegates to GeoService.location_score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from rapidfuzz import fuzz

from circularlink.core.geo import GeoService


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class MatchCandidate:
    """A single candidate product from the marketplace database."""
    product_id: str
    product_name: str
    description: str
    company_id: str
    company_name: str
    city: str
    lat: float
    lon: float
    quantity: float = 0.0
    unit: str = ""
    status: str = "approved"

    @classmethod
    def from_product_dict(cls, p: dict, company_name: str = "") -> "MatchCandidate":
        return cls(
            product_id=p.get("product_id", ""),
            product_name=p.get("name", ""),
            description=p.get("description", ""),
            company_id=p.get("company_id", ""),
            company_name=company_name or p.get("company_name", ""),
            city=p.get("city", ""),
            lat=float(p.get("lat", 0.0) or 0.0),
            lon=float(p.get("lon", 0.0) or 0.0),
            quantity=float(p.get("quantity", 0.0) or 0.0),
            unit=p.get("unit", ""),
            status=p.get("status", "pending"),
        )


@dataclass
class MatchResult:
    """A scored recommendation result."""
    product_id: str
    product_name: str
    description: str
    seller_company_id: str
    seller_company_name: str
    seller_city: str
    seller_lat: float
    seller_lon: float
    quantity: float
    unit: str
    fuzzy_score: float   # 0.0 – 1.0
    location_score: float  # 0.0 – 1.0
    final_score: float     # weighted composite
    distance_km: float
    status: str = "approved"

    @property
    def fuzzy_pct(self) -> int:
        return round(self.fuzzy_score * 100)

    @property
    def location_pct(self) -> int:
        return round(self.location_score * 100)

    @property
    def final_pct(self) -> int:
        return round(self.final_score * 100)


# ---------------------------------------------------------------------------
# Core matcher
# ---------------------------------------------------------------------------

FUZZY_WEIGHT = 0.7
LOCATION_WEIGHT = 0.3
DEFAULT_MIN_SCORE = 0.30        # discard results below 30 % final score
DEFAULT_MAX_RADIUS_KM = 2000.0  # India diagonal ~ 3200 km; practical cap 2000


class FuzzyMatcher:
    """
    Stateless fuzzy matcher.  Call match() with a query string and a list of
    MatchCandidate objects to get ranked MatchResult items.
    """

    @staticmethod
    def _fuzzy_score(query: str, candidate_name: str, candidate_desc: str) -> float:
        """
        Ensemble fuzzy score in [0, 1].

        Combines token_set_ratio + token_sort_ratio on the name, and
        partial_ratio on the description, then takes the best-of strategy.
        """
        q = query.strip().lower()
        name = candidate_name.strip().lower()
        desc = (candidate_desc or "").strip().lower()[:300]  # cap description length

        if not name:
            return 0.0

        # Primary: compare against name
        tsr = fuzz.token_set_ratio(q, name) / 100.0
        tsor = fuzz.token_sort_ratio(q, name) / 100.0
        pr_name = fuzz.partial_ratio(q, name) / 100.0

        name_score = max(tsr, tsor, pr_name)

        # Secondary: compare against description (boosted if name score is low)
        desc_score = 0.0
        if desc:
            desc_score = fuzz.token_set_ratio(q, desc) / 100.0

        # Weight: name dominates (70%), description supplements (30%)
        combined = 0.7 * name_score + 0.3 * desc_score
        return round(min(1.0, combined), 4)

    @staticmethod
    def match(
        query: str,
        candidates: list[MatchCandidate],
        buyer_lat: float,
        buyer_lon: float,
        top_k: int = 20,
        min_final_score: float = DEFAULT_MIN_SCORE,
        max_radius_km: float = DEFAULT_MAX_RADIUS_KM,
        exclude_company_id: str = "",
    ) -> list[MatchResult]:
        """
        Score and rank all candidates against a query material string.

        Parameters
        ----------
        query:             The material name being searched for.
        candidates:        List of approved marketplace listings.
        buyer_lat/lon:     Buyer's coordinates for location scoring.
        top_k:             Maximum results to return.
        min_final_score:   Discard results below this threshold [0, 1].
        max_radius_km:     Distance cap for location scoring.
        exclude_company_id: Exclude own listings from results.

        Returns
        -------
        Descending-sorted list of MatchResult (best match first).
        """
        results: list[MatchResult] = []

        for c in candidates:
            # Never recommend the buyer's own products
            if exclude_company_id and c.company_id == exclude_company_id:
                continue

            fuzzy = FuzzyMatcher._fuzzy_score(query, c.product_name, c.description)

            # Resolve seller coordinates
            geo = GeoService.resolve_coordinates(c.city, c.lat, c.lon)
            if geo and buyer_lat != 0 and buyer_lon != 0:
                loc_score = GeoService.location_score(
                    buyer_lat, buyer_lon, geo.lat, geo.lon, max_radius_km
                )
                dist_km = GeoService.haversine_km(buyer_lat, buyer_lon, geo.lat, geo.lon)
            else:
                # No coordinates available → neutral location score
                loc_score = 0.5
                dist_km = -1.0

            final = round(FUZZY_WEIGHT * fuzzy + LOCATION_WEIGHT * loc_score, 4)

            if final < min_final_score:
                continue

            results.append(
                MatchResult(
                    product_id=c.product_id,
                    product_name=c.product_name,
                    description=c.description,
                    seller_company_id=c.company_id,
                    seller_company_name=c.company_name,
                    seller_city=c.city,
                    seller_lat=geo.lat if geo else 0.0,
                    seller_lon=geo.lon if geo else 0.0,
                    quantity=c.quantity,
                    unit=c.unit,
                    fuzzy_score=fuzzy,
                    location_score=loc_score,
                    final_score=final,
                    distance_km=dist_km,
                    status=c.status,
                )
            )

        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:top_k]
