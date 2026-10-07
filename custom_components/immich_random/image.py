"""Image platform for the Immich Random Image integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ImmichCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Immich Random image platform."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator: ImmichCoordinator = entry_data["coordinator"]

    _LOGGER.info(
        "Setting up Immich Random Image entity (host=%s, albums=%d, verify_ssl=%s)",
        coordinator.hub.host,
        len(coordinator.hub.album_ids),
        coordinator.hub.verify_ssl,
    )

    # Fetch the first image now; afterwards the coordinator refreshes on the
    # configured scan interval (the entity itself does not poll).
    await coordinator.async_refresh()

    async_add_entities([ImmichRandomImageEntity(hass, coordinator, config_entry)])


class ImmichRandomImageEntity(CoordinatorEntity[ImmichCoordinator], ImageEntity):
    """Image entity that displays a random image from Immich."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: ImmichCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass=hass, verify_ssl=coordinator.hub.verify_ssl)
        self._coordinator = coordinator
        self._config_entry = config_entry
        album_ids = coordinator.hub.album_ids
        if album_ids:
            if len(album_ids) == 1:
                self._attr_unique_id = f"immich_random_album_{album_ids[0]}"
                self._attr_name = "Immich Random Album Image"
            else:
                self._attr_unique_id = (
                    f"immich_random_albums_{'_'.join(album_ids[:3])}"
                )
                self._attr_name = "Immich Random Multi-Album Image"
        else:
            self._attr_unique_id = "immich_random"
            self._attr_name = "Immich Random Image"

    async def async_image(self) -> bytes | None:
        """Return the current image bytes."""
        if not self._coordinator.image_bytes:
            await self._coordinator.async_request_refresh()
        return self._coordinator.image_bytes

    @property
    def content_type(self) -> str:
        """Return the MIME type reported by Immich for the current image."""
        return self._coordinator.content_type

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity state attributes from coordinator data."""
        data = self._coordinator.data or {}
        return {
            "media_filename": data.get("media_filename", ""),
            "media_localdatetime": data.get("media_localdatetime", ""),
            "media_width": data.get("media_width", ""),
            "media_height": data.get("media_height", ""),
        }

    @property
    def image_last_updated(self) -> datetime | None:
        """Return the last time the image was updated."""
        data = self._coordinator.data or {}
        last_pulled = data.get("last_pulled")
        if last_pulled:
            try:
                return datetime.fromisoformat(last_pulled)
            except (ValueError, TypeError):
                pass
        return self._coordinator.last_update_success_time
