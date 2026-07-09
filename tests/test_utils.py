"""Tests for the avfallsor data layer (utils.py)."""

from datetime import date

import aiohttp
import pytest
import utils

# --- pure helpers ---------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Dronningens   gate  24 ", "Dronningens gate 24"),
        ("Dronningens gate 24", "Dronningens gate 24"),
        ("\tDronningens\ngate\t24", "Dronningens gate 24"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalize_query(raw, expected):
    assert utils.normalize_query(raw) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("223cdde9-6a18-43ca-885f-78babd62968c", True),
        ("", False),
        ("not-a-uuid", False),
        ("223cdde9-6a18-43ca-885f", False),
        ("223cdde9_6a18_43ca_885f_78babd62968c", False),
    ],
)
def test_is_valid_property_id(value, expected):
    assert utils.is_valid_property_id(value) is expected


def test_extract_property_id():
    href = "https://avfallsor.no/hjemme-hos-deg/finn-hentedag/1332c0c6-1c40-4ce8-86d7-a62717122e65/"
    assert utils.extract_property_id(href) == "1332c0c6-1c40-4ce8-86d7-a62717122e65"
    assert utils.extract_property_id("") is None
    assert (
        utils.extract_property_id("https://avfallsor.no/hjemme-hos-deg/finn-hentedag/")
        is None
    )


# --- best_match -----------------------------------------------------------


def test_best_match_exact_wins(fixture):
    candidates = fixture("address_ambiguous.json")
    # Exact match on "Dronningens Gate 24" beats the longer 24 A / 24 B.
    assert (
        utils.best_match("Dronningens gate 24", candidates)
        == "1332c0c6-1c40-4ce8-86d7-a62717122e65"
    )


def test_best_match_shortest_prefix(fixture):
    candidates = fixture("address_ambiguous.json")
    # No exact match; "24 A" is the shortest value with the query as prefix.
    assert (
        utils.best_match("Dronningens gate 24 A", candidates)
        == "32251184-9d28-4f51-8e6f-e6640d5d6c44"
    )


def test_best_match_street_only_filtered(fixture):
    candidates = fixture("address_street_only.json")
    assert utils.best_match("Øvre", candidates) is None


def test_best_match_empty():
    assert utils.best_match("anything", []) is None


def test_best_match_fallback_first():
    candidates = [
        {
            "value": "Somewhere 1",
            "href": "https://x/finn-hentedag/1332c0c6-1c40-4ce8-86d7-a62717122e65/",
        },
        {
            "value": "Elsewhere 2",
            "href": "https://x/finn-hentedag/32251184-9d28-4f51-8e6f-e6640d5d6c44/",
        },
    ]
    assert (
        utils.best_match("no prefix match", candidates)
        == "1332c0c6-1c40-4ce8-86d7-a62717122e65"
    )


# --- async: address search ------------------------------------------------


async def test_search_address_normalizes_and_parses(avfallsor, fixture):
    avfallsor.set_address("Dronningens gate 33", fixture("address_unique.json"))
    async with aiohttp.ClientSession() as session:
        result = await utils.async_search_address(session, "  Dronningens   gate  33 ")
    assert len(result) == 1
    assert result[0]["value"] == "Dronningens Gate 33"


async def test_search_address_empty_term_no_request():
    async with aiohttp.ClientSession() as session:
        assert await utils.async_search_address(session, "   ") == []


async def test_search_address_non_list_response(avfallsor):
    avfallsor.set_address("x", {"unexpected": "shape"})
    async with aiohttp.ClientSession() as session:
        assert await utils.async_search_address(session, "x") == []


# --- async: find property id ----------------------------------------------


async def test_find_property_id_unique(avfallsor, fixture):
    avfallsor.set_address("Dronningens gate 33", fixture("address_unique.json"))
    async with aiohttp.ClientSession() as session:
        pid = await utils.async_find_property_id(session, "Dronningens gate 33")
    assert pid == "bdd61d75-e427-46b2-bdfc-1962dacaf0ba"


async def test_find_property_id_comma_fallback(avfallsor, fixture):
    # The lookup with municipality returns nothing (default []); the retry
    # without it succeeds.
    avfallsor.set_address("Dronningens gate 33", fixture("address_unique.json"))
    async with aiohttp.ClientSession() as session:
        pid = await utils.async_find_property_id(
            session, "Dronningens gate 33, Kristiansand"
        )
    assert pid == "bdd61d75-e427-46b2-bdfc-1962dacaf0ba"


async def test_find_property_id_not_found(avfallsor, fixture):
    avfallsor.set_address("Øvre", fixture("address_street_only.json"))
    async with aiohttp.ClientSession() as session:
        assert await utils.async_find_property_id(session, "Øvre") is None


# --- async: pickup calendar ----------------------------------------------


async def test_get_pickup_calendar_maps_types(avfallsor, fixture):
    pid = "223cdde9-6a18-43ca-885f-78babd62968c"
    avfallsor.set_calendar(pid, fixture("calendar_full.json"))
    async with aiohttp.ClientSession() as session:
        cal = await utils.async_get_pickup_calendar(session, pid)

    assert cal["residual"] == [date(2026, 7, 15)]
    assert cal["bio"] == [date(2026, 7, 15)]
    assert cal["paper"] == [date(2026, 8, 5)]
    # Glass and metal share one collection item.
    assert cal["glass"] == [date(2026, 8, 5)]
    assert cal["metal"] == [date(2026, 8, 5)]


async def test_get_pickup_calendar_null_collections(avfallsor, fixture):
    pid = "223cdde9-6a18-43ca-885f-78babd62968c"
    avfallsor.set_calendar(pid, fixture("calendar_null.json"))
    async with aiohttp.ClientSession() as session:
        cal = await utils.async_get_pickup_calendar(session, pid)
    assert cal == {}


async def test_get_pickup_calendar_invalid_id():
    async with aiohttp.ClientSession() as session:
        with pytest.raises(ValueError):
            await utils.async_get_pickup_calendar(session, "not-a-uuid")


async def test_get_pickup_calendar_http_error_propagates(avfallsor):
    pid = "223cdde9-6a18-43ca-885f-78babd62968c"
    avfallsor.set_calendar(pid, None, status=500)
    async with aiohttp.ClientSession() as session:
        with pytest.raises(aiohttp.ClientError):
            await utils.async_get_pickup_calendar(session, pid)
