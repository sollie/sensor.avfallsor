"""Shared pytest fixtures for the avfallsor tests."""

import json
import sys
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

# utils.py only depends on stdlib + aiohttp (no Home Assistant imports), so we
# add its directory to sys.path and import it directly, keeping the test
# dependencies light.
COMPONENT_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "avfallsor"
)
sys.path.insert(0, str(COMPONENT_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str):
    """Load and parse a JSON fixture by file name."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def fixture():
    """Return the load_fixture helper."""
    return load_fixture


class FakeAvfallsor:
    """Drives a local stand-in for the avfallsor.no endpoints."""

    def __init__(self) -> None:
        self._address: dict[str, object] = {}
        self._calendar: dict[str, tuple[int, object]] = {}

    def set_address(self, term: str, payload: object) -> None:
        """Set the response for a given lookup_term."""
        self._address[term] = payload

    def set_calendar(
        self, property_id: str, payload: object, status: int = 200
    ) -> None:
        """Set the response for a given property id."""
        self._calendar[property_id] = (status, payload)

    async def _handle_address(self, request: web.Request) -> web.Response:
        term = request.query.get("lookup_term", "")
        return web.json_response(self._address.get(term, []))

    async def _handle_calendar(self, request: web.Request) -> web.Response:
        pid = request.match_info["pid"]
        if pid not in self._calendar:
            return web.json_response({"collections": None})
        status, payload = self._calendar[pid]
        if status != 200:
            return web.Response(status=status)
        return web.json_response(payload)


@pytest.fixture
async def avfallsor(monkeypatch):
    """Start a local fake avfallsor server and point utils at it."""
    import utils

    fake = FakeAvfallsor()
    app = web.Application()
    app.router.add_get("/wp-json/addresses/v1/address", fake._handle_address)
    app.router.add_get(
        "/wp-json/pickup-calendar/v1/collections/property-id/{pid}",
        fake._handle_calendar,
    )

    server = TestServer(app)
    await server.start_server()
    base = str(server.make_url("")).rstrip("/")

    monkeypatch.setattr(
        utils, "ADDRESS_SEARCH_URL", f"{base}/wp-json/addresses/v1/address"
    )
    monkeypatch.setattr(
        utils,
        "PICKUP_CALENDAR_URL",
        f"{base}/wp-json/pickup-calendar/v1/collections/property-id",
    )

    yield fake

    await server.close()
