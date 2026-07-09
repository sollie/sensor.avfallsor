"""Helpers for talking to the avfallsor.no JSON API.

The avfallsor.no "Finn hentedag" page is backed by two public WordPress REST
endpoints. We use them directly instead of scraping HTML:

1. Address search resolves free text to a property UUID:
   /wp-json/addresses/v1/address?lookup_term=<address>
   Returns a JSON array of candidates; the property UUID is the last path
   segment of each candidate's ``href``.

2. Pickup calendar returns the schedule for a property UUID:
   /wp-json/pickup-calendar/v1/collections/property-id/<uuid>
"""

import logging
import re
from collections import defaultdict
from datetime import date, datetime

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://avfallsor.no"
ADDRESS_SEARCH_URL = f"{BASE_URL}/wp-json/addresses/v1/address"
PICKUP_CALENDAR_URL = f"{BASE_URL}/wp-json/pickup-calendar/v1/collections/property-id"

# The avfallsor.no property id is a plain UUID; the pickup-calendar route
# rejects anything that is not shaped like one with a 404.
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

# The garbage types the integration exposes. Keys match the ``wasteIcons``
# values returned by the pickup-calendar endpoint.
GARBAGE_TYPES = ["paper", "bio", "residual", "metal", "plastic", "glass"]


def normalize_query(value: str) -> str:
    """Trim and collapse internal whitespace, preserving case.

    The upstream search matches the raw ``lookup_term`` with no normalization
    of its own; a double space breaks matching entirely.
    """
    return " ".join(value.split())


def is_valid_property_id(value: str) -> bool:
    """Return True if value has the UUID shape the calendar endpoint expects."""
    return bool(value) and bool(UUID_RE.match(value))


def extract_property_id(href: str) -> str | None:
    """Pull the property UUID out of a finn-hentedag href."""
    if not href:
        return None
    candidate = href.rstrip("/").rsplit("/", 1)[-1]
    return candidate if is_valid_property_id(candidate) else None


def best_match(query: str, candidates: list[dict]) -> str | None:
    """Auto-pick the property UUID for query from the search candidates.

    Candidates with no resolvable href (street-only entries) are dropped.
    Then:
      1. An exact case/whitespace-insensitive match on ``value`` wins.
      2. Otherwise, the shortest ``value`` that has the query as a prefix
         wins (prefers "Dronningens Gate 24" over "24 A"/"24 B"/...).
      3. Otherwise, the first resolvable candidate is used.
    """
    resolvable: list[tuple[dict, str]] = []
    for candidate in candidates:
        property_id = extract_property_id(candidate.get("href", ""))
        if property_id:
            resolvable.append((candidate, property_id))

    if not resolvable:
        return None

    norm_query = normalize_query(query).lower()

    for candidate, property_id in resolvable:
        if normalize_query(candidate.get("value", "")).lower() == norm_query:
            return property_id

    best_id: str | None = None
    best_len = -1
    for candidate, property_id in resolvable:
        norm_value = normalize_query(candidate.get("value", "")).lower()
        if not norm_value.startswith(norm_query):
            continue
        if best_len == -1 or len(norm_value) < best_len:
            best_id = property_id
            best_len = len(norm_value)

    if best_id is not None:
        return best_id

    return resolvable[0][1]


async def async_search_address(session: aiohttp.ClientSession, term: str) -> list[dict]:
    """Query the address autocomplete endpoint. Returns the raw candidate list."""
    term = normalize_query(term)
    if not term:
        return []

    _LOGGER.debug("Searching avfallsor address for %r", term)
    async with session.get(ADDRESS_SEARCH_URL, params={"lookup_term": term}) as resp:
        resp.raise_for_status()
        data = await resp.json()

    if not isinstance(data, list):
        _LOGGER.warning("Unexpected address search response: %r", data)
        return []
    return data


async def async_find_property_id(
    session: aiohttp.ClientSession, address: str
) -> str | None:
    """Resolve a free-text address to a property UUID.

    Retries once without the trailing municipality (", Kristiansand"), since
    appending the city breaks the upstream match.
    """
    if not address:
        return None

    candidates = await async_search_address(session, address)
    property_id = best_match(address, candidates)
    if property_id:
        return property_id

    if "," in address:
        head = address.rsplit(",", 1)[0].strip()
        if head and head != address:
            candidates = await async_search_address(session, head)
            return best_match(head, candidates)

    return None


async def async_get_pickup_calendar(
    session: aiohttp.ClientSession, property_id: str
) -> dict[str, list[date]]:
    """Fetch the pickup calendar for a property UUID.

    Returns a mapping of garbage type -> sorted list of upcoming pickup dates.
    """
    if not is_valid_property_id(property_id):
        raise ValueError(f"Invalid property id: {property_id!r}")

    url = f"{PICKUP_CALENDAR_URL}/{property_id}"
    _LOGGER.debug("Fetching pickup calendar %s", url)
    async with session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()

    result: dict[str, set[date]] = defaultdict(set)
    for collection in data.get("collections") or []:
        for item in collection.get("items") or []:
            pickup = _parse_item_date(item, collection)
            if pickup is None:
                continue
            for icon in item.get("wasteIcons") or []:
                if icon in GARBAGE_TYPES:
                    result[icon].add(pickup)

    return {gtype: sorted(dates) for gtype, dates in result.items()}


def _parse_item_date(item: dict, collection: dict) -> date | None:
    """Extract the pickup date from a calendar item.

    Prefers the ISO ``dato`` field, falling back to the collection's
    ``dateIndex`` (both seen as e.g. "2026-07-15T00:00:00" / "2026-07-15").
    """
    for raw in (item.get("dato"), collection.get("dateIndex")):
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            _LOGGER.debug("Could not parse date %r", raw)
    return None
