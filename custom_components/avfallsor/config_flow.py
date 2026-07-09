"""Config flow for the avfallsor integration."""

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN
from .utils import async_find_property_id, async_get_pickup_calendar

_LOGGER = logging.getLogger(__name__)


def _schema(default_address: str = "") -> vol.Schema:
    return vol.Schema({vol.Required("address", default=default_address): str})


class AvfallSorFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for avfallsor."""

    VERSION = 1

    async def _resolve(self, address: str, errors: dict[str, str]) -> str | None:
        """Resolve an address to a property id, populating errors on failure."""
        session = async_get_clientsession(self.hass)

        try:
            property_id = await async_find_property_id(session, address)
        except (aiohttp.ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
            return None

        if not property_id:
            errors["address"] = "invalid_address"
            return None

        try:
            calendar = await async_get_pickup_calendar(session, property_id)
        except (aiohttp.ClientError, TimeoutError):
            errors["base"] = "cannot_connect"
            return None

        if not calendar:
            errors["address"] = "no_pickup_data"
            return None

        return property_id

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input["address"].strip()
            property_id = await self._resolve(address, errors)
            if property_id is not None:
                await self.async_set_unique_id(property_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=address, data={"address": address})

        return self.async_show_form(
            step_id="user", data_schema=_schema(), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input["address"].strip()
            property_id = await self._resolve(address, errors)
            if property_id is not None:
                for other in self._async_current_entries():
                    if (
                        other.entry_id != entry.entry_id
                        and other.unique_id == property_id
                    ):
                        return self.async_abort(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry,
                    data={"address": address},
                    unique_id=property_id,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(entry.data.get("address", "")),
            errors=errors,
        )
