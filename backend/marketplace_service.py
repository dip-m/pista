# backend/marketplace_service.py
import os
import requests
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.logger_config import logger

# Environment variable to toggle mock mode
USE_MOCK_MARKETPLACE = os.getenv("USE_MOCK_MARKETPLACE", "true").lower() == "true"


def search_amazon(game_name: str) -> List[Dict[str, Any]]:
    """Search Amazon Product Advertising API for game listings."""
    # TODO: Implement Amazon Product Advertising API integration
    # Requires: AWS credentials, Product Advertising API access
    # API: https://webservices.amazon.com/paapi5/documentation/
    listings = []
    try:
        # Placeholder for real API call
        # response = requests.get(...)
        pass
    except Exception as e:
        logger.warning(f"Amazon search error: {e}")
    return listings


def search_ebay(game_name: str) -> List[Dict[str, Any]]:
    """Search eBay Finding API for game listings."""
    # TODO: Implement eBay Finding API integration
    # Requires: eBay API credentials
    # API: https://developer.ebay.com/DevZone/finding/Concepts/FindingAPIGuide.html
    listings = []
    try:
        # Placeholder for real API call
        # response = requests.get(...)
        pass
    except Exception as e:
        logger.warning(f"eBay search error: {e}")
    return listings


def search_geekmarket(game_name: str) -> List[Dict[str, Any]]:
    """Search BoardGameGeek GeekMarket for game listings."""
    # TODO: Implement BGG GeekMarket scraping/API
    # Note: BGG doesn't have a public API for GeekMarket
    # May need to scrape or use unofficial API
    listings = []
    try:
        # Placeholder for real implementation
        # response = requests.get(...)
        pass
    except Exception as e:
        logger.warning(f"GeekMarket search error: {e}")
    return listings


def search_wallapop(game_name: str) -> List[Dict[str, Any]]:
    """Search Wallapop API for game listings."""
    # TODO: Implement Wallapop API integration
    # Requires: Wallapop API credentials
    listings = []
    try:
        # Placeholder for real API call
        # response = requests.get(...)
        pass
    except Exception as e:
        logger.warning(f"Wallapop search error: {e}")
    return listings


def search_bga(game_id: Optional[int] = None, game_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search Board Game Arena (BGA) for game availability.
    Checks if game is available on BGA and whether it requires premium.

    Args:
        game_id: BGG game ID to match
        game_name: Game name to search for (fallback)

    Returns:
        List of BGA listings (typically 0 or 1 entry)
    """
    listings = []
    try:
        # BGA game list URL
        bga_gamelist_url = "https://en.boardgamearena.com/gamelist"

        # Fetch BGA game list
        response = requests.get(bga_gamelist_url, timeout=10)
        if response.status_code != 200:
            logger.warning(f"BGA gamelist fetch failed: {response.status_code}")
            return listings

        # Parse HTML to find game names and IDs
        html = response.text

        # Try to match game by name (case-insensitive)
        if game_name:
            # Look for game name in BGA game list
            # BGA uses data-gamename attribute or similar
            pattern = rf'data-gamename=["\']([^"\']*{re.escape(game_name.lower())}[^"\']*)["\']'
            matches = re.findall(pattern, html, re.IGNORECASE)

            if not matches:
                # Try alternative pattern - look for game links
                pattern = rf'<a[^>]*href=["\']/gamepanel[^"\']*["\'][^>]*>([^<]*{re.escape(game_name)}[^<]*)</a>'
                matches = re.findall(pattern, html, re.IGNORECASE)

        # Check if game requires premium
        # BGA premium info is typically in a separate API or page
        # For now, we'll mark as requiring premium check
        bga_access = "premium_required"  # Default assumption
        premium_price = get_bga_premium_price()

        if matches or game_name:
            listings.append(
                {
                    "platform": "BGA",
                    "marketplace_name": "bga",
                    "url": f"https://en.boardgamearena.com/gamelist",
                    "price": 0,  # Free to play (but may need premium)
                    "currency": "USD",
                    "shipping_included": True,  # Digital, no shipping
                    "condition": "Digital",
                    "bga_access": bga_access,
                    "premium_price": premium_price,
                    "premium_price_currency": "USD",
                    "premium_price_last_checked": datetime.now().isoformat(),
                    "estimated_total_cost": premium_price if bga_access == "premium_required" else 0,
                }
            )
    except Exception as e:
        logger.warning(f"BGA search error: {e}")

    return listings


def get_bga_premium_price() -> float:
    """
    Get current BGA Premium subscription price.
    Checks announcement page or API for current pricing.

    Returns:
        Premium price in USD, or 0 if unavailable
    """
    try:
        # BGA premium pricing is typically on their announcement page
        # URL: https://boardgamearena.com/premium
        premium_url = "https://boardgamearena.com/premium"
        response = requests.get(premium_url, timeout=10)

        if response.status_code == 200:
            html = response.text
            # Look for price patterns like $14.99, €12.99, etc.
            # Common patterns: $XX.XX, €XX.XX, £XX.XX
            price_patterns = [
                r"\$(\d+\.?\d*)",  # USD
                r"€(\d+\.?\d*)",  # EUR
                r"£(\d+\.?\d*)",  # GBP
            ]

            for pattern in price_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    # Convert to float and return first match
                    # For EUR/GBP, we'd need conversion, but for now return USD equivalent
                    price = float(matches[0])
                    if "€" in pattern or "£" in pattern:
                        # Rough conversion (should use actual exchange rates)
                        price = price * 1.1  # Approximate USD conversion
                    return price

        # Fallback: Default BGA premium price (typically around $14.99/month)
        return 14.99
    except Exception as e:
        logger.warning(f"Error fetching BGA premium price: {e}")
        return 14.99  # Default fallback


def get_mock_listings(game_name: str) -> List[Dict[str, Any]]:
    """Generate mock marketplace listings for testing."""
    return [
        {
            "platform": "Amazon",
            "price": 29.99,
            "currency": "$",
            "shipping_included": True,
            "condition": "New",
            "location": "USA",
            "seller_rating": 4.8,
            "seller_reviews": 1250,
            "url": f"https://www.amazon.com/s?k={game_name.replace(' ', '+')}",
        },
        {
            "platform": "eBay",
            "price": 24.99,
            "currency": "$",
            "shipping_included": False,
            "condition": "Used",
            "location": "UK",
            "seller_rating": 4.6,
            "seller_reviews": 342,
            "url": f"https://www.ebay.com/sch/i.html?_nkw={game_name.replace(' ', '+')}",
        },
        {
            "platform": "GeekMarket",
            "price": 22.50,
            "currency": "$",
            "shipping_included": False,
            "condition": "Like New",
            "location": "USA",
            "seller_rating": 4.9,
            "seller_reviews": 89,
            "url": f"https://boardgamegeek.com/geekmarket/browse?query={game_name.replace(' ', '+')}",
        },
        {
            "platform": "Wallapop",
            "price": 18.00,
            "currency": "€",
            "shipping_included": True,
            "condition": "Used",
            "location": "Spain",
            "seller_rating": 4.7,
            "seller_reviews": 156,
            "url": f"https://es.wallapop.com/search?keywords={game_name.replace(' ', '+')}",
        },
    ]


def search_marketplace(game_name: str, game_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Search all marketplace sources and aggregate results.
    Returns unified list of listings from all platforms.

    Args:
        game_name: Name of the game to search for
        game_id: Optional game ID (useful for BGA matching)
    """
    if USE_MOCK_MARKETPLACE:
        logger.debug("Using mock marketplace data")
        return get_mock_listings(game_name)

    all_listings = []

    # Search all platforms in parallel (could use asyncio for better performance)
    try:
        amazon_listings = search_amazon(game_name)
        all_listings.extend(amazon_listings)
    except Exception as e:
        logger.error(f"Amazon search failed: {e}")

    try:
        ebay_listings = search_ebay(game_name)
        all_listings.extend(ebay_listings)
    except Exception as e:
        logger.error(f"eBay search failed: {e}")

    try:
        geekmarket_listings = search_geekmarket(game_name)
        all_listings.extend(geekmarket_listings)
    except Exception as e:
        logger.error(f"GeekMarket search failed: {e}")

    try:
        wallapop_listings = search_wallapop(game_name)
        all_listings.extend(wallapop_listings)
    except Exception as e:
        logger.error(f"Wallapop search failed: {e}")

    # Search BGA (Board Game Arena) - requires game_id or game_name
    try:
        bga_listings = search_bga(game_id=game_id, game_name=game_name)
        all_listings.extend(bga_listings)
    except Exception as e:
        logger.error(f"BGA search failed: {e}")

    # Sort by price (lowest first)
    all_listings.sort(key=lambda x: x.get("price", float("inf")))

    return all_listings
