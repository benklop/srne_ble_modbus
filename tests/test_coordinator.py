"""Tests for SRNEDataUpdateCoordinator (current constructor and helpers)."""

from unittest.mock import MagicMock

import pytest

from custom_components.srne_inverter.coordinator import SRNEDataUpdateCoordinator
from custom_components.srne_inverter.domain.helpers.transformations import (
    convert_to_signed_int16,
)


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {}
    return hass


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.data = {"address": "AA:BB:CC:DD:EE:FF"}
    entry.options = {"update_interval": 60}
    return entry


def test_coordinator_requires_device_config(mock_hass, mock_config_entry):
    coord = SRNEDataUpdateCoordinator(
        mock_hass,
        mock_config_entry,
        device_config={"registers": {}, "device": {}},
    )
    assert coord._address == "AA:BB:CC:DD:EE:FF"


def test_signed_int16_matches_domain_helper():
    assert convert_to_signed_int16(0) == 0
    assert convert_to_signed_int16(32767) == 32767
    assert convert_to_signed_int16(65535) == -1
