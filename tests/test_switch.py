"""Tests for the SRNE Inverter switch platform (configurable switch entity)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.srne_inverter.const import DOMAIN
from custom_components.srne_inverter.entities.configurable_switch import (
    ConfigurableSwitch,
)


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.title = "Test Inverter"
    entry.data = {}
    return entry


def _device_config():
    return {
        "device": {"features": {}, "feature_ranges": {}, "user_preferences": {}},
        "registers": {"power_control": {"address": 57088}},
        "_register_by_name": {
            "power_control": {"address": 57088, "_address_int": 57088},
        },
    }


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"machine_state": 1, "connected": True}
    coordinator.last_update_success = True
    coordinator.is_register_failed = MagicMock(return_value=False)
    coordinator.is_entity_unavailable = MagicMock(return_value=False)

    ok = MagicMock()
    ok.success = True
    coordinator.async_write_register = AsyncMock(return_value=ok)
    return coordinator


def _switch_config():
    return {
        "entity_id": "ac_power",
        "name": "AC Power",
        "device_class": "outlet",
        "register": "power_control",
        "on_value": 1,
        "off_value": 0,
        "state_key": "machine_state",
        "state_mapping": {"on": [4, 5], "off": [1, 9]},
        "icon": "mdi:power-plug",
    }


def test_switch_off_for_standby(mock_coordinator, mock_config_entry):
    sw = ConfigurableSwitch(
        mock_coordinator, mock_config_entry, _switch_config(), _device_config()
    )
    mock_coordinator.data = {"machine_state": 1, "connected": True}
    assert sw.is_on is False


def test_switch_on_for_ac_operation(mock_coordinator, mock_config_entry):
    sw = ConfigurableSwitch(
        mock_coordinator, mock_config_entry, _switch_config(), _device_config()
    )
    mock_coordinator.data = {"machine_state": 4, "connected": True}
    assert sw.is_on is True


@pytest.mark.asyncio
async def test_async_turn_on_writes_register(mock_coordinator, mock_config_entry):
    sw = ConfigurableSwitch(
        mock_coordinator, mock_config_entry, _switch_config(), _device_config()
    )
    sw.hass = MagicMock()
    sw.async_write_ha_state = MagicMock()

    await sw.async_turn_on()

    mock_coordinator.async_write_register.assert_awaited()
    call_args = mock_coordinator.async_write_register.await_args[0]
    assert call_args[0] == 57088
    assert call_args[1] == 1


@pytest.mark.asyncio
async def test_async_turn_on_fails_reverts_optimistic(
    mock_coordinator, mock_config_entry
):
    sw = ConfigurableSwitch(
        mock_coordinator, mock_config_entry, _switch_config(), _device_config()
    )
    sw.hass = MagicMock()
    sw.async_write_ha_state = MagicMock()

    fail = MagicMock()
    fail.success = False
    fail.error = "timeout"
    mock_coordinator.async_write_register = AsyncMock(return_value=fail)

    with pytest.raises(HomeAssistantError):
        await sw.async_turn_on()

    assert sw._optimistic_state is None
