"""Tests for the SRNE Inverter sensor platform (YAML-driven entities)."""

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.srne_inverter.const import DOMAIN
from custom_components.srne_inverter.entities.configurable_sensor import (
    ConfigurableSensor,
)
from custom_components.srne_inverter.sensor import async_setup_entry


def _make_coordinator():
    coordinator = MagicMock(
        spec=[
            "data",
            "last_update_success",
            "is_register_failed",
            "is_entity_unavailable",
        ]
    )
    coordinator.data = {"connected": True, "battery_soc": 85}
    coordinator.last_update_success = True
    coordinator.is_register_failed = MagicMock(return_value=False)
    coordinator.is_entity_unavailable = MagicMock(return_value=False)
    return coordinator


def _minimal_device_config():
    return {
        "version": "2.0",
        "device": {"features": {}, "feature_ranges": {}, "user_preferences": {}},
        "registers": {
            "battery_soc": {"address": 0x100},
        },
        "sensors": [
            {
                "entity_id": "battery_soc",
                "name": "Battery SOC",
                "source_type": "coordinator_data",
                "data_key": "battery_soc",
                "device_class": "battery",
                "unit_of_measurement": "%",
            }
        ],
    }


@pytest.fixture
def mock_hass():
    return MagicMock(spec=HomeAssistant)


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test SRNE Inverter"
    entry.data = {}
    entry.options = {
        "enable_diagnostic_sensors": False,
        "enable_calculated_sensors": True,
        "enable_energy_dashboard": True,
    }
    return entry


@pytest.mark.asyncio
async def test_async_setup_entry_creates_configurable_sensors(
    mock_hass, mock_config_entry
):
    coordinator = _make_coordinator()
    config = _minimal_device_config()
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
    assert isinstance(entities[0], ConfigurableSensor)
    assert entities[0].unique_id == "test_entry_battery_soc"


def test_configurable_battery_soc_sensor(mock_config_entry):
    coordinator = _make_coordinator()
    cfg = _minimal_device_config()["sensors"][0]
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    assert sensor.native_value == 85
