"""
GSTIN Validator
===============
Validates Indian Goods and Services Tax Identification Numbers using the
official 15-character format mandated by the GST Council:

  Positions  1-2  : State code  (01–37)
  Positions  3-7  : PAN alpha   (5 uppercase letters)
  Positions  8-11 : PAN numeric (4 digits)
  Position   12   : PAN check   (1 uppercase letter)
  Position   13   : Entity type (1–9 or A-Z, not 0)
  Position   14   : Z           (always literal 'Z')
  Position   15   : Check digit (0–9 or A-Z)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# Official regex per GST Council specification
_GSTIN_REGEX = re.compile(
    r"^([0-3][0-9])"            # state code 01-39
    r"([A-Z]{5})"               # PAN: 5 alpha
    r"([0-9]{4})"               # PAN: 4 numeric
    r"([A-Z])"                  # PAN: 1 alpha check
    r"([1-9A-Z])"               # entity type (not 0)
    r"(Z)"                      # literal Z
    r"([0-9A-Z])$"              # check digit
)

# Mapping of state codes to state names
_STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman & Diu",
    "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}


@dataclass
class GSTINResult:
    valid: bool
    gstin: str
    state_code: str = ""
    state_name: str = ""
    pan: str = ""
    entity_type: str = ""
    error: str = ""

    def __str__(self) -> str:
        if self.valid:
            return (
                f"Valid GSTIN | State: {self.state_name} ({self.state_code}) "
                f"| PAN: {self.pan} | Entity: {self.entity_type}"
            )
        return f"Invalid GSTIN: {self.error}"


class GSTINValidator:
    """Stateless GSTIN validator."""

    @staticmethod
    def validate(gstin: str) -> GSTINResult:
        """Validate a GSTIN string and return a rich result object."""
        if not gstin:
            return GSTINResult(valid=False, gstin=gstin, error="GSTIN cannot be empty")

        gstin = gstin.strip().upper()

        if len(gstin) != 15:
            return GSTINResult(
                valid=False,
                gstin=gstin,
                error=f"GSTIN must be exactly 15 characters (got {len(gstin)})",
            )

        match = _GSTIN_REGEX.fullmatch(gstin)
        if not match:
            return GSTINResult(
                valid=False,
                gstin=gstin,
                error="GSTIN format invalid — does not match pattern "
                      "[StateCode][PAN][EntityType][Z][CheckDigit]",
            )

        state_code = match.group(1)
        pan = match.group(2) + match.group(3) + match.group(4)
        entity_type = match.group(5)
        state_name = _STATE_CODES.get(state_code, f"Unknown state ({state_code})")

        # Validate state code is within known range (01-38 + special)
        state_int = int(state_code)
        if not (1 <= state_int <= 38 or state_code in ("97", "99")):
            return GSTINResult(
                valid=False,
                gstin=gstin,
                state_code=state_code,
                error=f"State code {state_code!r} is not a recognised Indian state/UT",
            )

        return GSTINResult(
            valid=True,
            gstin=gstin,
            state_code=state_code,
            state_name=state_name,
            pan=pan,
            entity_type=entity_type,
        )

    @staticmethod
    def is_valid(gstin: str) -> bool:
        return GSTINValidator.validate(gstin).valid
