"""
U.S. Census Bureau ACS5 API client for Audience Research demographic enrichment.

Fetches real demographic data (population, income, education, age) by zip code
when CENSUS_API_KEY is configured.  Returns None gracefully when:
  - No API key is configured
  - No 5-digit zip code can be extracted from the location string
  - The Census API request fails for any reason

Free API key: https://api.census.gov/data/key_signup.html
"""

from __future__ import annotations

import re
from typing import Optional

from .logger import logger

# ACS5 2022 vintage — most recent 5-year estimate (broadly available)
_CENSUS_API_BASE = "https://api.census.gov/data/2022/acs/acs5"

# Variables to fetch per zip code
# Labels kept in sync with _VARIABLE_LABELS below.
_VARIABLES = [
    "NAME",  # Geographic name (e.g. "ZCTA5 63376")
    "B01003_001E",  # Total population
    "B19013_001E",  # Median household income (past 12 months)
    "B01002_001E",  # Median age
    "B15003_022E",  # Population 25+ with Bachelor's degree
    "B15003_023E",  # Population 25+ with Master's degree
    "B15003_025E",  # Population 25+ with Professional degree
    "B11001_001E",  # Total households
]

_VARIABLE_LABELS = {
    "B01003_001E": "Total population",
    "B19013_001E": "Median household income",
    "B01002_001E": "Median age",
    "B15003_022E": "Bachelor's degree holders (25+)",
    "B15003_023E": "Master's degree holders (25+)",
    "B15003_025E": "Professional/doctoral degree holders (25+)",
    "B11001_001E": "Total households",
}

_ZIP_RE = re.compile(r"\b(\d{5})\b")


def fetch_zip_demographics(location: str, api_key: str) -> Optional[str]:
    """
    Fetch US Census ACS5 demographic data for a zip code found in *location*.

    Args:
        location: Free-form location string (e.g. "Wentzville, MO 63376").
        api_key: Census Bureau API key.

    Returns:
        Formatted demographic summary string ready for prompt injection, or None
        when no zip code is found, the API key is missing/invalid, or any network
        error occurs.
    """
    if not api_key:
        return None

    zip_code = _extract_zip(location)
    if not zip_code:
        logger.debug(f"No 5-digit zip code found in location: {location!r}")
        return None

    try:
        import urllib.request  # stdlib — no extra dependency
        import json as _json

        variables = ",".join(_VARIABLES)
        url = (
            f"{_CENSUS_API_BASE}"
            f"?get={variables}"
            f"&for=zip+code+tabulation+area:{zip_code}"
            f"&key={api_key}"
        )

        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(
            req, timeout=10
        ) as resp:  # nosec B310 — fixed HTTPS gov endpoint
            raw = _json.loads(resp.read().decode())

        return _format_response(raw, zip_code)

    except Exception as exc:
        logger.warning(f"Census API request failed for zip {zip_code}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_zip(location: str) -> Optional[str]:
    """Return the first 5-digit number found in location, or None."""
    match = _ZIP_RE.search(location)
    return match.group(1) if match else None


def _format_response(raw: list, zip_code: str) -> Optional[str]:
    """
    Parse the Census nested-array response and return a human-readable summary.

    Census returns:
        [ [header_col1, header_col2, ...], [value1, value2, ...] ]
    """
    if not raw or len(raw) < 2:
        return None

    headers, values = raw[0], raw[1]
    data = dict(zip(headers, values))

    lines = [f"U.S. CENSUS DATA — ZIP {zip_code} (ACS5 2022):"]

    def _fmt_int(val: Optional[str]) -> str:
        try:
            n = int(val)  # type: ignore[arg-type]
            return f"{n:,}" if n >= 0 else "N/A"
        except (TypeError, ValueError):
            return "N/A"

    def _fmt_currency(val: Optional[str]) -> str:
        try:
            n = int(val)  # type: ignore[arg-type]
            return f"${n:,}" if n >= 0 else "N/A"
        except (TypeError, ValueError):
            return "N/A"

    pop = _fmt_int(data.get("B01003_001E"))
    income = _fmt_currency(data.get("B19013_001E"))
    age = data.get("B01002_001E", "N/A")
    households = _fmt_int(data.get("B11001_001E"))

    lines.append(f"  Population: {pop}  |  Households: {households}")
    lines.append(f"  Median household income: {income}  |  Median age: {age}")

    # Education breakdown
    try:
        pop_int = int(data.get("B01003_001E") or 0)
        bachelors = int(data.get("B15003_022E") or 0)
        masters = int(data.get("B15003_023E") or 0)
        professional = int(data.get("B15003_025E") or 0)
        college_plus = bachelors + masters + professional
        if pop_int > 0 and college_plus > 0:
            pct = round(college_plus / pop_int * 100, 1)
            lines.append(f"  College-educated (bachelor's+): ~{pct}% of population")
    except (TypeError, ValueError):
        pass

    return "\n".join(lines)
