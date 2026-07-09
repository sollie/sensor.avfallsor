"""The avfallsor integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import AvfallSorCoordinator
from .utils import async_find_property_id, is_valid_property_id

DOMAIN = "avfallsor"
NAME = DOMAIN
VERSION = "1.0.0"
ISSUEURL = "https://github.com/sollie/sensor.avfallsor/issues"

STARTUP = """
-------------------------------------------------------------------
{name}
Version: {version}
This is a custom component
If you have any issues with this you need to open an issue here:
{issueurl}
-------------------------------------------------------------------
""".format(name=NAME, version=VERSION, issueurl=ISSUEURL)

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type AvfallSorConfigEntry = ConfigEntry[AvfallSorCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration (nothing to do for YAML)."""
    _LOGGER.info(STARTUP)
    return True


async def _resolve_property_id(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Resolve the property UUID for a config entry.

    New entries store an ``address``. Legacy entries created before the
    address search worked may only carry a ``street_id`` (which already is the
    property UUID); honour those so existing installs keep working.
    """
    street_id = entry.data.get("street_id")
    if street_id and is_valid_property_id(street_id):
        return street_id

    address = entry.data.get("address")
    if address:
        session = async_get_clientsession(hass)
        return await async_find_property_id(session, address)

    return None


async def async_setup_entry(hass: HomeAssistant, entry: AvfallSorConfigEntry) -> bool:
    """Set up avfallsor from a config entry."""
    try:
        property_id = await _resolve_property_id(hass, entry)
    except Exception as err:  # noqa: BLE001 - surface as retryable setup error
        raise ConfigEntryNotReady(
            f"Could not reach avfallsor.no to resolve the address: {err}"
        ) from err

    if not property_id:
        raise ConfigEntryError(
            "Could not resolve a pickup location for the configured address. "
            "Please reconfigure the integration with a valid Avfall Sør address."
        )

    coordinator = AvfallSorCoordinator(hass, entry, property_id)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AvfallSorConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
