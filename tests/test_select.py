"""Tests for the SRNE Inverter select platform (configurable select entity)."""

from unittest.mock import MagicMock

import pytest

from custom_components.srne_inverter.const import DOMAIN
from custom_components.srne_inverter.entities.configurable_select import (
    ConfigurableSelect,
)
from custom_components.srne_inverter.select import async_setup_entry


def _device_config():
    return {
        "device": {"features": {}, "feature_ranges": {}, "user_preferences": {}},
        "registers": {"energy_priority": {"address": 57860}},
        "_register_by_name": {
            "energy_priority": {"address": 57860, "_address_int": 57860},
        },
        "selects": [
            {
                "entity_id": "energy_priority",
                "name": "Energy Priority",
                "register": "energy_priority",
                "options": {
                    0: "Solar First",
                    1: "Utility First",
                    2: "Battery First",
                },
                "icon": "mdi:priority-high",
            }
        ],
    }


def _coordinator():
    coordinator = MagicMock()
    coordinator.data = {"energy_priority": 0, "connected": True}
    coordinator.last_update_success = True
    coordinator.is_register_failed = MagicMock(return_value=False)
    coordinator.is_entity_unavailable = MagicMock(return_value=False)
    return coordinator


@pytest.fixture
def mock_hass():
    return MagicMock()


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test SRNE Inverter"
    entry.data = {}
    entry.options = {}
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry_loads_selects(mock_hass, mock_config_entry):
    coordinator = _coordinator()
    config = _device_config()
    mock_hass.data = {
        DOMAIN: {
            mock_config_entry.entry_id: {
                "coordinator": coordinator,
                "config": config,
            },
        }
    }
    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], ConfigurableSelect)
    assert entities[0].current_option == "Solar First"


def test_priority_mapping_battery_first(mock_config_entry):
    coordinator = _coordinator()
    coordinator.data = {"energy_priority": 2, "connected": True}
    sel = ConfigurableSelect(
        coordinator,
        mock_config_entry,
        _device_config()["selects"][0],
        _device_config(),
    )
    assert sel.current_option == "Battery First"
