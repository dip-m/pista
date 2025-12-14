import time
from typing import Optional
import requests
import xml.etree.ElementTree as ET


headers = {
    "Authorization": f"Bearer f8b71467-0069-4536-a822-1f3dd0dd431c",
    "Accept": "application/json",
}

BGG_BASE_URL = "https://boardgamegeek.com/xmlapi2/thing"


class BGGError(Exception):
    pass


def fetch_thing(
    bgg_id: int,
    thing_type: str = "boardgame",
    stats: bool = True,
    max_retries: int = 5,
    retry_sleep: float = 5.0,
) -> ET.Element:
    """Fetch a single game's XML from BGG XML API2 /thing.

    - Handles HTTP 202 (queued) by waiting and retrying.
    - Raises BGGError on non-200 responses (after retries).

    Returns the <item> element for the requested game id.
    """
    params = {
        "id": str(bgg_id),
        "type": thing_type,
    }
    if stats:
        params["stats"] = "1"

    attempt = 0
    last_exc: Optional[Exception] = None

    while attempt < max_retries:
        attempt += 1
        try:
            resp = requests.get(BGG_BASE_URL, headers=headers, params=params, timeout=30)
        except Exception as exc:
            last_exc = exc
            time.sleep(retry_sleep)
            continue

        if resp.status_code == 202:
            time.sleep(retry_sleep)
            continue

        if resp.status_code != 200:
            last_exc = BGGError(f"HTTP {resp.status_code} for id={bgg_id}")
            time.sleep(retry_sleep)
            continue

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as exc:
            last_exc = exc
            time.sleep(retry_sleep)
            continue

        item = root.find("item")
        if item is None:
            raise BGGError(f"No <item> found in XML for id={bgg_id}")
        return item

    raise BGGError(f"Failed to fetch id={bgg_id} after {max_retries} attempts: {last_exc!r}")
