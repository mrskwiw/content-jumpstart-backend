"""DataForSEO API client — Google Trends fallback for keyword enrichment.

Used when pytrends is rate-limited (429). Provides the same trend_score,
trend_direction, and trend_momentum_score fields as the pytrends path.

Cost: ~$0.002 per keyword (pay-as-you-go, no subscription).
Docs: https://docs.dataforseo.com/v3/keywords_data/google_trends/explore/live/
"""

import statistics
from datetime import date, timedelta
from typing import Optional

from .logger import logger


class DataForSEOClient:
    _BASE_URL = "https://api.dataforseo.com/v3/keywords_data/google_trends/explore/live"
    _LOCATION_US = 2840  # United States
    _TIMEOUT = 30

    def __init__(self) -> None:
        # Import here so the module loads even without backend config present
        from backend.config import settings

        self._login = settings.DATAFORSEO_LOGIN
        self._password = settings.DATAFORSEO_PASSWORD

    @property
    def configured(self) -> bool:
        return bool(self._login and self._password)

    def get_trends(self, keyword: str) -> Optional[dict]:
        """Fetch Google Trends data for a single keyword.

        Returns a dict with keys:
            trend_score (float 0-100): mean interest of the last 4 weekly points
            trend_direction (str): "rising" | "stable" | "declining" | "seasonal"
            trend_momentum_score (float): same as trend_score (for API compat)

        Returns None if not configured, on HTTP error, or if data is absent.
        """
        if not self.configured:
            return None

        import requests  # lazy import — optional dependency path

        date_from = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
        payload = [
            {
                "keywords": [keyword],
                "date_from": date_from,
                "type": "web",
                "language_code": "en",
                "location_code": self._LOCATION_US,
            }
        ]

        try:
            response = requests.post(  # nosec B113 — timeout is set
                self._BASE_URL,
                json=payload,
                auth=(self._login, self._password),
                timeout=self._TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            logger.warning(f"DataForSEO request failed for '{keyword}': {exc}")
            return None

        return self._parse_response(keyword, body)

    def _parse_response(self, keyword: str, body: dict) -> Optional[dict]:
        try:
            result = body["tasks"][0]["result"][0]
            items = result.get("items") or []
            if not items:
                logger.debug(f"DataForSEO: no items for '{keyword}'")
                return None

            # items[0].data is a list of {"date": "...", "values": [{"value": N}]}
            data_points = items[0].get("data") or []
            values = [
                pt["values"][0]["value"]
                for pt in data_points
                if pt.get("values") and pt["values"][0].get("value") is not None
            ]

            if len(values) < 4:
                logger.debug(f"DataForSEO: insufficient data points for '{keyword}'")
                return None

            recent = values[-4:]
            trend_score = float(statistics.mean(recent))
            trend_momentum = trend_score

            if len(values) >= 8:
                older = values[-8:-4]
                recent_avg = statistics.mean(recent)
                older_avg = statistics.mean(older)
                variance = statistics.stdev(values) if len(values) > 1 else 0
                if variance > 25:
                    direction = "seasonal"
                elif recent_avg > older_avg * 1.2:
                    direction = "rising"
                elif recent_avg < older_avg * 0.8:
                    direction = "declining"
                else:
                    direction = "stable"
            else:
                direction = "stable"

            return {
                "trend_score": trend_score,
                "trend_direction": direction,
                "trend_momentum_score": trend_momentum,
            }

        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(f"DataForSEO: unexpected response shape for '{keyword}': {exc}")
            return None
