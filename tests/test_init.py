"""Tests for the SRNE Inverter integration __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.srne_inverter import async_setup_entry, async_unload_entry
from custom_components.srne_inverter.const import DOMAIN

from tests.conftest import configure_mock_hass_core


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    entry.title = "Test SRNE Inverter"
    entry.options = {}
    entry.async_on_unload = MagicMock()
    return entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_shutdown = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator._load_storage = AsyncMock()
    coordinator._failed_registers = set()
    coordinator._unavailable_sensors = set()
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


@pytest.mark.asyncio
async def test_async_setup_entry_success(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test successful setup of a config entry."""
    hass = MagicMock()
    hass.data = {}
    configure_mock_hass_core(hass, str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()

    mock_container = MagicMock()
    mock_container.coordinator = mock_coordinator

    with patch(
        "custom_components.srne_inverter.load_entity_config",
        AsyncMock(return_value=full_device_config),
    ), patch(
        "custom_components.srne_inverter.presentation.container.create_container",
        return_value=mock_container,
    ):
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        hass.config_entries.async_forward_entry_setups.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_connection_failure(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test setup failure when connection fails."""
    hass = MagicMock()
    hass.data = {}
    configure_mock_hass_core(hass, str(tmp_path))
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()

    mock_coordinator.async_config_entry_first_refresh.side_effect = Exception(
        "Connection failed"
    )

    mock_container = MagicMock()
    mock_container.coordinator = mock_coordinator

    with patch(
        "custom_components.srne_inverter.load_entity_config",
        AsyncMock(return_value=full_device_config),
    ), patch(
        "custom_components.srne_inverter.presentation.container.create_container",
        return_value=mock_container,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry_success(mock_config_entry, mock_coordinator):
    """Test successful unload of a config entry."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator,
                "config": {},
            }
        }
    }
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.services = MagicMock()
    hass.services.async_remove = MagicMock()

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_called_once()
    hass.config_entries.async_unload_platforms.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(mock_config_entry, mock_coordinator):
    """Test unload when platform unload fails."""
    hass = MagicMock()
    hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator,
                "config": {},
            }
        }
    }
    hass.config_entries = MagicMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)
    hass.services = MagicMock()
    hass.services.async_remove = MagicMock()

    result = await async_unload_entry(hass, mock_config_entry)

    assert result is False
    assert mock_config_entry.entry_id in hass.data[DOMAIN]
    mock_coordinator.async_shutdown.assert_not_called()
