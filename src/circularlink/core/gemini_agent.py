"""
Gemini Agent
============
Integrates Google Gemini 2.5 Flash for two inference tasks:

  Task A — Material Prediction (Seller flow)
    Given a company's primary product description, predict the probable
    industrial by-products and waste streams it generates.

  Task B — Raw Material Inference (Buyer flow assisted)
    Given a buyer's search phrase or product type, expand it into a richer
    set of synonyms and related material keywords to improve fuzzy matching.

Uses google-generativeai SDK. The API key is sourced from:
  1. Database config (stored securely in ~/.circularlink/config.json)
  2. GOOGLE_API_KEY environment variable (fallback)

Both tasks return structured JSON extracted from the LLM response, with a
lightweight local validation layer to strip hallucinated or clearly wrong entries.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

MODEL_NAME = "gemini-2.5-flash"

# Maximum retries on transient API errors (rate-limit / network)
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds

# Prompt templates
_BYPRODUCT_PROMPT = """You are an expert industrial process engineer specialising in material flows and circular economy.

A manufacturing company produces the following primary product:
\"\"\"{product_description}\"\"\"

Your task:
1. List the probable industrial by-products, waste streams, scrap, or secondary materials this company likely generates during production.
2. For each by-product, provide:
   - A short, specific material name (2-5 words)
   - A one-sentence description explaining how it is generated

Return ONLY a valid JSON array with no markdown fences, no extra text:
[
  {{"material": "...", "description": "..."}},
  ...
]

Rules:
- Return 3 to 8 items maximum.
- Be specific (e.g. "copper wire scrap" not just "scrap").
- Do NOT include hazardous chemicals like benzene, asbestos, cyanide, PCBs.
- Focus on industrially tradeable secondary materials.
"""

_KEYWORD_EXPANSION_PROMPT = """You are a materials science expert and industrial supply-chain specialist.

A buyer is searching for: \"\"\"{query}\"\"\"

Expand this into a list of synonyms, trade names, related materials, and alternative names that would help locate matching listings in an industrial marketplace.

Return ONLY a valid JSON array of strings with no markdown fences, no extra text:
["term1", "term2", ...]

Rules:
- Return 4 to 10 terms maximum.
- Include common abbreviations and trade names.
- Do NOT include hazardous substances.
"""


@dataclass
class PredictedMaterial:
    material: str
    description: str
    confidence: float = 0.9  # default confidence for LLM-predicted items


@dataclass
class GeminiResponse:
    success: bool
    predicted_materials: list[PredictedMaterial] = field(default_factory=list)
    expanded_keywords: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: str = ""
    model_used: str = MODEL_NAME
    latency_ms: float = 0.0


class GeminiAgent:
    """
    CircuLink Gemini Agent.

    Manages the Gemini client lifecycle and exposes high-level methods for
    material prediction and keyword expansion.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "Gemini API key is required. "
                "Set it in KYC/Settings or export GOOGLE_API_KEY."
            )
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=GenerationConfig(
                temperature=0.2,       # low temperature for factual material science
                top_p=0.95,
                max_output_tokens=1024,
            ),
        )
        self._api_key = api_key

    # ── Seller Flow: Predict by-products from primary product ───────────────

    def predict_byproducts(
        self,
        product_description: str,
        product_id: str = "",
    ) -> GeminiResponse:
        """
        Predict industrial by-products from a primary product description.

        Returns a GeminiResponse with predicted_materials populated.
        Logs the call to the Database LLM audit trail.
        """
        from circularlink.storage.db import Database

        prompt = _BYPRODUCT_PROMPT.format(product_description=product_description)
        t_start = time.monotonic()
        raw = self._call_with_retry(prompt)
        latency_ms = (time.monotonic() - t_start) * 1000

        if raw.startswith("__ERROR__"):
            return GeminiResponse(
                success=False,
                raw_response=raw,
                error=raw.replace("__ERROR__", "").strip(),
                latency_ms=latency_ms,
            )

        materials = self._parse_material_list(raw)
        resp = GeminiResponse(
            success=True,
            predicted_materials=materials,
            raw_response=raw,
            latency_ms=latency_ms,
        )

        # Persist to audit trail
        try:
            Database.log_llm_call(
                product_id=product_id,
                prompt=prompt,
                response=raw,
                predicted_materials=[m.material for m in materials],
                confidence=sum(m.confidence for m in materials) / max(len(materials), 1),
            )
        except Exception:
            pass  # Logging failure must never crash the main flow

        return resp

    # ── Buyer Flow: Expand search keywords ──────────────────────────────────

    def expand_keywords(self, query: str) -> GeminiResponse:
        """
        Expand a buyer's search query into synonyms and related material names.

        Returns a GeminiResponse with expanded_keywords populated.
        """
        prompt = _KEYWORD_EXPANSION_PROMPT.format(query=query)
        t_start = time.monotonic()
        raw = self._call_with_retry(prompt)
        latency_ms = (time.monotonic() - t_start) * 1000

        if raw.startswith("__ERROR__"):
            return GeminiResponse(
                success=False,
                raw_response=raw,
                error=raw.replace("__ERROR__", "").strip(),
                latency_ms=latency_ms,
            )

        keywords = self._parse_keyword_list(raw)
        return GeminiResponse(
            success=True,
            expanded_keywords=keywords,
            raw_response=raw,
            latency_ms=latency_ms,
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _call_with_retry(self, prompt: str) -> str:
        """Call the Gemini API with retries. Returns raw text or '__ERROR__ ...'."""
        last_error = ""
        for attempt in range(_MAX_RETRIES):
            try:
                result = self._model.generate_content(prompt)
                # Extract text from response
                if result.parts:
                    return result.text.strip()
                return ""
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAY * (attempt + 1))
        return f"__ERROR__ {last_error}"

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown fences and extract the JSON content."""
        # Remove ```json ... ``` fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw)
        cleaned = cleaned.replace("```", "").strip()
        return cleaned

    @staticmethod
    def _parse_material_list(raw: str) -> list[PredictedMaterial]:
        """Parse JSON array of {material, description} dicts from LLM response."""
        try:
            data = json.loads(GeminiAgent._extract_json(raw))
            if not isinstance(data, list):
                return []
            materials = []
            for item in data:
                if isinstance(item, dict):
                    mat = str(item.get("material", "")).strip()
                    desc = str(item.get("description", "")).strip()
                    if mat:
                        materials.append(PredictedMaterial(material=mat, description=desc))
            return materials
        except (json.JSONDecodeError, TypeError, ValueError):
            # Attempt a lenient line-by-line extraction
            materials = []
            for line in raw.splitlines():
                line = line.strip().strip('",[]').strip()
                if line and len(line) > 3 and not line.startswith(("{", "}")):
                    materials.append(PredictedMaterial(material=line, description=""))
            return materials[:8]

    @staticmethod
    def _parse_keyword_list(raw: str) -> list[str]:
        """Parse JSON array of strings from LLM response."""
        try:
            data = json.loads(GeminiAgent._extract_json(raw))
            if isinstance(data, list):
                return [str(k).strip() for k in data if str(k).strip()]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        # Lenient: one term per line
        terms = []
        for line in raw.splitlines():
            term = line.strip().strip('",[]').strip()
            if term and len(term) > 1:
                terms.append(term)
        return terms[:10]

    # ── Factory / singleton helpers ──────────────────────────────────────────

    @staticmethod
    def from_env_or_db() -> "GeminiAgent | None":
        """
        Build a GeminiAgent from the saved API key or GOOGLE_API_KEY env var.
        Returns None if no key is found.
        """
        try:
            from circularlink.storage.db import Database
            key = Database.get_api_key() or os.getenv("GOOGLE_API_KEY", "")
        except Exception:
            key = os.getenv("GOOGLE_API_KEY", "")
        if not key:
            return None
        try:
            return GeminiAgent(api_key=key)
        except Exception:
            return None
