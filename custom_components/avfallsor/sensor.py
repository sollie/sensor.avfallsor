"""Sensor platform for the avfallsor integration."""

import logging
from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, AvfallSorConfigEntry
from .coordinator import AvfallSorCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by Avfall Sør"

ICONS = {
    "paper": "mdi:newspaper-variant-multiple",
    "bio": "mdi:leaf",
    "residual": "mdi:trash-can",
    "metal": "mdi:bottle-wine",
    "plastic": "mdi:recycle",
    "glass": "mdi:bottle-wine",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AvfallSorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up avfallsor sensors from a config entry."""
    coordinator = entry.runtime_data

    address = entry.data.get("address") or "Avfall Sør"
    device_info = DeviceInfo(
        identifiers={(DOMAIN, coordinator.property_id)},
        name=f"Avfall Sør {address}",
        manufacturer="Avfall Sør",
        model="Tømmekalender",
        configuration_url="https://avfallsor.no/hjemme-hos-deg/finn-hentedag/",
    )

    entities = [
        AvfallSorSensor(coordinator, device_info, garbage_type)
        for garbage_type in sorted(coordinator.data)
    ]
    async_add_entities(entities)


class AvfallSorSensor(CoordinatorEntity[AvfallSorCoordinator], SensorEntity):
    """Next pickup date for a single garbage type."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: AvfallSorCoordinator,
        device_info: DeviceInfo,
        garbage_type: str,
    ) -> None:
        super().__init__(coordinator)
        self._garbage_type = garbage_type
        self._attr_translation_key = garbage_type
        self._attr_unique_id = f"{coordinator.property_id}_{garbage_type}"
        self._attr_device_info = device_info
        self._attr_icon = ICONS.get(garbage_type, "mdi:trash-can")

    @property
    def _dates(self) -> list[date]:
        """Upcoming pickup dates for this garbage type, today or later."""
        today = datetime.now().date()
        return [
            d for d in self.coordinator.data.get(self._garbage_type, []) if d >= today
        ]

    @property
    def native_value(self) -> date | None:
        """Return the next pickup date."""
        upcoming = self._dates
        return upcoming[0] if upcoming else None

    @property
    def available(self) -> bool:
        return super().available and self._garbage_type in self.coordinator.data

    @property
    def extra_state_attributes(self) -> dict:
        upcoming = self._dates
        days_until = (upcoming[0] - datetime.now().date()).days if upcoming else None
        return {
            "garbage_type": self._garbage_type,
            "days_until": days_until,
            "upcoming": [d.isoformat() for d in upcoming],
        }
