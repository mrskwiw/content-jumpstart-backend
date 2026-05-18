"""
Google Maps Search via SerpAPI

Provides local business discovery and review analysis using SerpAPI's Google Maps API.
Used by Competitor Identifier and Competitive Analysis research tools.
"""

import os
from typing import List, Optional
from dataclasses import dataclass

from .logger import logger


@dataclass
class GoogleMapsPlace:
    """Google Maps place/business result"""

    place_id: str
    name: str
    address: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    hours: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class GoogleMapsReview:
    """Individual Google Maps review"""

    author: str
    rating: int  # 1-5
    text: str
    date: Optional[str] = None
    likes: Optional[int] = None


@dataclass
class PlaceWithReviews:
    """Place with its reviews"""

    place: GoogleMapsPlace
    reviews: List[GoogleMapsReview]
    total_reviews: int


class GoogleMapsClient:
    """Google Maps search client using SerpAPI"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google Maps client

        Args:
            api_key: SerpAPI API key (or reads from SERPAPI_API_KEY env)
        """
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")

        if not self.api_key:
            logger.warning(
                "No SerpAPI key found. Set SERPAPI_API_KEY environment variable. "
                "Google Maps search will return empty results."
            )

    def search_local_businesses(
        self,
        query: str,
        location: str,
        max_results: int = 10,
    ) -> List[GoogleMapsPlace]:
        """Search for local businesses on Google Maps

        Args:
            query: Search query (e.g., "coffee shops", "marketing agencies")
            location: Location (e.g., "San Francisco, CA", "New York")
            max_results: Maximum number of results to return

        Returns:
            List of Google Maps places
        """
        if not self.api_key:
            logger.warning("No SerpAPI key configured - returning empty results")
            return []

        try:
            import requests

            url = "https://serpapi.com/search"
            # Bug #170: SerpAPI Google Maps requires ll in "@lat,lng,zoom" format.
            # Passing a plain text location string causes 400 Bad Request.
            # Embed location in the query string instead — Maps understands
            # "near <city>" phrasing without coordinates.
            location_query = f"{query} near {location}" if location else query
            params: dict[str, str | int] = {
                "engine": "google_maps",
                "q": location_query,
                "type": "search",
                "api_key": self.api_key,
                "num": max_results,
            }

            logger.info(f"Google Maps search: '{query}' near '{location}'")

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Parse local results
            places = []
            for item in data.get("local_results", [])[:max_results]:
                place = GoogleMapsPlace(
                    place_id=item.get("place_id", ""),
                    name=item.get("title", ""),
                    address=item.get("address", ""),
                    rating=item.get("rating"),
                    reviews_count=item.get("reviews"),
                    phone=item.get("phone"),
                    website=item.get("website"),
                    category=item.get("type"),
                    hours=item.get("hours"),
                    latitude=item.get("gps_coordinates", {}).get("latitude"),
                    longitude=item.get("gps_coordinates", {}).get("longitude"),
                )
                places.append(place)

            logger.info(f"Found {len(places)} local businesses")
            return places

        except Exception as e:
            logger.error(f"Google Maps search failed: {e}", exc_info=True)
            return []

    def get_place_reviews(
        self,
        place_id: str,
        max_reviews: int = 20,
    ) -> PlaceWithReviews:
        """Get reviews for a specific Google Maps place

        Args:
            place_id: Google Maps place ID
            max_reviews: Maximum number of reviews to fetch

        Returns:
            PlaceWithReviews object with place data and reviews
        """
        if not self.api_key:
            logger.warning("No SerpAPI key configured - returning empty reviews")
            return PlaceWithReviews(
                place=GoogleMapsPlace(place_id=place_id, name="Unknown", address=""),
                reviews=[],
                total_reviews=0,
            )

        try:
            import requests

            url = "https://serpapi.com/search"
            params: dict[str, str | int] = {
                "engine": "google_maps_reviews",
                "place_id": place_id,
                "api_key": self.api_key,
                "num": max_reviews,
            }

            logger.info(f"Fetching reviews for place_id: {place_id}")

            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Parse place info
            place_info = data.get("place_info", {})
            place = GoogleMapsPlace(
                place_id=place_id,
                name=place_info.get("title", "Unknown"),
                address=place_info.get("address", ""),
                rating=place_info.get("rating"),
                reviews_count=place_info.get("reviews"),
            )

            # Parse reviews
            reviews = []
            for item in data.get("reviews", [])[:max_reviews]:
                review = GoogleMapsReview(
                    author=item.get("user", {}).get("name", "Anonymous"),
                    rating=item.get("rating", 0),
                    text=item.get("snippet", ""),
                    date=item.get("date", None),
                    likes=item.get("likes"),
                )
                reviews.append(review)

            logger.info(f"Fetched {len(reviews)} reviews for {place.name}")

            return PlaceWithReviews(
                place=place,
                reviews=reviews,
                total_reviews=place_info.get("reviews", len(reviews)),
            )

        except Exception as e:
            logger.error(f"Failed to fetch reviews: {e}", exc_info=True)
            return PlaceWithReviews(
                place=GoogleMapsPlace(place_id=place_id, name="Unknown", address=""),
                reviews=[],
                total_reviews=0,
            )


# Default client instance
_default_client: Optional[GoogleMapsClient] = None


def get_google_maps_client(api_key: Optional[str] = None) -> GoogleMapsClient:
    """Get or create default Google Maps client

    Args:
        api_key: Optional SerpAPI API key

    Returns:
        GoogleMapsClient instance
    """
    global _default_client

    if _default_client is None or (api_key and api_key != _default_client.api_key):
        _default_client = GoogleMapsClient(api_key=api_key)

    return _default_client
