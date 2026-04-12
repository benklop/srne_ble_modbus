"""Smoke tests for SRNE config flow (current multi-step onboarding)."""

from unittest.mock import MagicMock

import pytest
from homeassistant.data_entry_flow import FlowResultType

from custom_components.srne_inverter.config_flow import SRNEConfigFlow
from custom_components.srne_inverter.const import CONF_CONNECTION_TYPE, CONNECTION_TYPE_BLE


@pytest.mark.asyncio
async def test_async_step_user_shows_connection_choice():
    flow = SRNEConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" not in result or result.get("errors") in (None, {})


@pytest.mark.asyncio
async def test_async_step_user_ble_selection_continues_flow():
    flow = SRNEConfigFlow()
    flow.hass = MagicMock()
    flow.context = {}

    result = await flow.async_step_user(
        user_input={CONF_CONNECTION_TYPE: CONNECTION_TYPE_BLE}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "ble_device"
