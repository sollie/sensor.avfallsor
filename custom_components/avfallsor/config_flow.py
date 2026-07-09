"""Config flow for the avfallsor integration."""

import logging

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import DOMAIN
from .utils import async_find_property_id, async_get_pickup_calendar

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({vol.Required("address"): str})


class AvfallSorFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for avfallsor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input["address"].strip()
            session = async_get_clientsession(self.hass)

            try:
                property_id = await async_find_property_id(session, address)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            else:
                if not property_id:
                    errors["address"] = "invalid_address"
                else:
                    await self.async_set_unique_id(property_id)
                    self._abort_if_unique_id_configured()

                    try:
                        calendar = await async_get_pickup_calendar(session, property_id)
                    except aiohttp.ClientError:
                        errors["base"] = "cannot_connect"
                    else:
                        if not calendar:
                            errors["address"] = "no_pickup_data"
                        else:
                            return self.async_create_entry(
                                title=address,
                                data={"address": address},
                            )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
