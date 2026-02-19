"""
Database — JSON-based persistent local storage for CircuLink.

All data lives under ~/.circularlink/ which is created on first run.

Schema (each JSON file is a list of dicts):
  companies.json   — verified company profiles
  products.json    — product/byproduct listings (approved | blocked | pending)
  matches.json     — computed match history (top-N recommendations cached)
  llm_logs/        — JSONL files, one per day, for Gemini inference audit trail
  config.json      — singleton dict: api_key, current session company_id
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_DATA_DIR = Path.home() / ".circularlink"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dirs() -> None:
    (_DATA_DIR / "llm_logs").mkdir(parents=True, exist_ok=True)


def _load(filename: str) -> list[dict]:
    _ensure_dirs()
    path = _DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save(filename: str, data: list[dict]) -> None:
    _ensure_dirs()
    path = _DATA_DIR / filename
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, default=str)


def _load_config() -> dict:
    _ensure_dirs()
    path = _DATA_DIR / "config.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError:
            return {}


def _save_config(cfg: dict) -> None:
    _ensure_dirs()
    path = _DATA_DIR / "config.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Database façade
# ---------------------------------------------------------------------------

class Database:
    """Thread-safe-enough façade over JSON flat-files.

    All writes re-serialise the complete file (acceptable at prototype scale;
    for production swap internals for SQLite or Postgres without changing the
    public API).
    """

    # ── Config / session ────────────────────────────────────────────────────

    @staticmethod
    def get_config() -> dict:
        return _load_config()

    @staticmethod
    def save_config(cfg: dict) -> None:
        _save_config(cfg)

    @staticmethod
    def get_api_key() -> str:
        return _load_config().get("api_key", "")

    @staticmethod
    def set_api_key(api_key: str) -> None:
        cfg = _load_config()
        cfg["api_key"] = api_key
        _save_config(cfg)

    @staticmethod
    def get_current_company_id() -> str | None:
        return _load_config().get("current_company_id")

    @staticmethod
    def set_current_company_id(company_id: str | None) -> None:
        cfg = _load_config()
        cfg["current_company_id"] = company_id
        _save_config(cfg)

    # ── Companies ───────────────────────────────────────────────────────────

    @staticmethod
    def all_companies() -> list[dict]:
        return _load("companies.json")

    @staticmethod
    def get_company(company_id: str) -> dict | None:
        return next(
            (c for c in _load("companies.json") if c["company_id"] == company_id),
            None,
        )

    @staticmethod
    def get_company_by_gstin(gstin: str) -> dict | None:
        return next(
            (c for c in _load("companies.json") if c["gstin"] == gstin),
            None,
        )

    @staticmethod
    def upsert_company(company: dict) -> dict:
        """Insert or update a company record. Adds company_id + verified_at if new."""
        companies = _load("companies.json")
        existing_idx = next(
            (i for i, c in enumerate(companies) if c["company_id"] == company.get("company_id")),
            None,
        )
        if existing_idx is None:
            company.setdefault("company_id", _uid())
            company.setdefault("verified_at", _now_iso())
            companies.append(company)
        else:
            companies[existing_idx].update(company)
            company = companies[existing_idx]
        _save("companies.json", companies)
        return company

    @staticmethod
    def delete_company(company_id: str) -> bool:
        companies = _load("companies.json")
        new = [c for c in companies if c["company_id"] != company_id]
        if len(new) == len(companies):
            return False
        _save("companies.json", new)
        return True

    # ── Products ────────────────────────────────────────────────────────────

    @staticmethod
    def all_products(status_filter: str | None = None) -> list[dict]:
        products = _load("products.json")
        if status_filter:
            products = [p for p in products if p.get("status") == status_filter]
        return products

    @staticmethod
    def get_product(product_id: str) -> dict | None:
        return next(
            (p for p in _load("products.json") if p["product_id"] == product_id),
            None,
        )

    @staticmethod
    def products_by_company(company_id: str) -> list[dict]:
        return [p for p in _load("products.json") if p.get("company_id") == company_id]

    @staticmethod
    def upsert_product(product: dict) -> dict:
        products = _load("products.json")
        existing_idx = next(
            (i for i, p in enumerate(products) if p["product_id"] == product.get("product_id")),
            None,
        )
        if existing_idx is None:
            product.setdefault("product_id", _uid())
            product.setdefault("created_at", _now_iso())
            product.setdefault("status", "pending")
            products.append(product)
        else:
            products[existing_idx].update(product)
            product = products[existing_idx]
        _save("products.json", products)
        return product

    @staticmethod
    def update_product_status(product_id: str, status: str, hazard_class: str | None = None) -> bool:
        products = _load("products.json")
        for p in products:
            if p["product_id"] == product_id:
                p["status"] = status
                if hazard_class is not None:
                    p["hazard_class"] = hazard_class
                _save("products.json", products)
                return True
        return False

    @staticmethod
    def delete_product(product_id: str) -> bool:
        products = _load("products.json")
        new = [p for p in products if p["product_id"] != product_id]
        if len(new) == len(products):
            return False
        _save("products.json", new)
        return True

    # ── Matches ─────────────────────────────────────────────────────────────

    @staticmethod
    def all_matches() -> list[dict]:
        return _load("matches.json")

    @staticmethod
    def matches_for_company(company_id: str) -> list[dict]:
        return [m for m in _load("matches.json") if m.get("buyer_company_id") == company_id]

    @staticmethod
    def save_matches(buyer_company_id: str, query_material: str, results: list[dict]) -> None:
        """Persist a batch of match results, deduplicating by (buyer, product)."""
        matches = _load("matches.json")
        existing_keys = {
            (m["buyer_company_id"], m["product_id"])
            for m in matches
        }
        for r in results:
            key = (buyer_company_id, r["product_id"])
            if key not in existing_keys:
                matches.append(
                    {
                        "match_id": _uid(),
                        "buyer_company_id": buyer_company_id,
                        "query_material": query_material,
                        "product_id": r["product_id"],
                        "product_name": r.get("product_name", ""),
                        "seller_company_name": r.get("seller_company_name", ""),
                        "seller_city": r.get("seller_city", ""),
                        "fuzzy_score": r.get("fuzzy_score", 0.0),
                        "location_score": r.get("location_score", 0.0),
                        "final_score": r.get("final_score", 0.0),
                        "created_at": _now_iso(),
                    }
                )
                existing_keys.add(key)
        _save("matches.json", matches)

    # ── LLM Logs (JSONL append-only) ────────────────────────────────────────

    @staticmethod
    def log_llm_call(
        product_id: str,
        prompt: str,
        response: str,
        predicted_materials: list[str],
        confidence: float,
    ) -> None:
        _ensure_dirs()
        today = date.today().isoformat()
        log_path = _DATA_DIR / "llm_logs" / f"{today}.jsonl"
        entry: dict[str, Any] = {
            "log_id": _uid(),
            "product_id": product_id,
            "prompt": prompt,
            "response": response,
            "predicted_materials": predicted_materials,
            "confidence": confidence,
            "created_at": _now_iso(),
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def get_llm_logs(limit: int = 50) -> list[dict]:
        _ensure_dirs()
        log_dir = _DATA_DIR / "llm_logs"
        entries: list[dict] = []
        for log_file in sorted(log_dir.glob("*.jsonl"), reverse=True):
            with log_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            if len(entries) >= limit:
                break
        return entries[:limit]

    # ── Dashboard stats ─────────────────────────────────────────────────────

    @staticmethod
    def stats() -> dict:
        companies = _load("companies.json")
        products = _load("products.json")
        matches = _load("matches.json")
        return {
            "total_companies": len(companies),
            "total_products": len(products),
            "approved_products": sum(1 for p in products if p.get("status") == "approved"),
            "blocked_products": sum(1 for p in products if p.get("status") == "blocked"),
            "pending_products": sum(1 for p in products if p.get("status") == "pending"),
            "total_matches": len(matches),
        }

    @staticmethod
    def data_dir() -> Path:
        _ensure_dirs()
        return _DATA_DIR
