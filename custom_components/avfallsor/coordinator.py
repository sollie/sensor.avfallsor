"""DataUpdateCoordinator for the avfallsor integration."""

import logging
from datetime import date, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .utils import async_get_pickup_calendar

_LOGGER = logging.getLogger(__name__)

# The pickup schedule changes rarely, but we refresh a couple of times a day
# so holiday deviations and newly published dates are picked up in good time.
UPDATE_INTERVAL = timedelta(hours=12)


class AvfallSorCoordinator(DataUpdateCoordinator[dict[str, list[date]]]):
    """Fetch the pickup calendar for a single property."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, property_id: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="avfallsor",
            config_entry=entry,
            update_interval=UPDATE_INTERVAL,
        )
        self.property_id = property_id
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> dict[str, list[date]]:
        try:
            return await async_get_pickup_calendar(self._session, self.property_id)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with avfallsor.no: {err}") from err
