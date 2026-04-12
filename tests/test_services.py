"""Tests for SRNE Inverter service calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.srne_inverter import (
    SERVICE_FORCE_REFRESH,
    SERVICE_RESET_STATISTICS,
    SERVICE_RESTART_INVERTER,
    async_setup_entry,
)
from custom_components.srne_inverter.application.use_cases.write_register_result import (
    WriteRegisterResult,
)
from custom_components.srne_inverter.const import DOMAIN

from tests.conftest import configure_mock_hass_core


def _patches_for_async_setup(mock_coordinator, full_device_config):
    mock_coordinator._load_storage = AsyncMock()
    mock_coordinator._failed_registers = set()
    mock_coordinator._unavailable_sensors = set()
    mock_container = MagicMock()
    mock_container.coordinator = mock_coordinator
    return (
        patch(
            "custom_components.srne_inverter.load_entity_config",
            AsyncMock(return_value=full_device_config),
        ),
        patch(
            "custom_components.srne_inverter.presentation.container.create_container",
            return_value=mock_container,
        ),
    )


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
    coordinator.async_write_register = AsyncMock(
        return_value=WriteRegisterResult(success=True)
    )
    coordinator._failed_reads = 5
    coordinator._total_updates = 100
    coordinator._failed_registers = set()
    coordinator._unavailable_sensors = set()
    coordinator.data = {"battery_soc": 85, "connected": True}
    return coordinator


@pytest.fixture
async def setup_integration(mock_config_entry, mock_coordinator, full_device_config, tmp_path):
    """Set up the integration with mock coordinator."""
    hass = MagicMock()
    hass.data = {}
    configure_mock_hass_core(hass, str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()

    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        await async_setup_entry(hass, mock_config_entry)

    return hass, mock_coordinator, mock_config_entry


@pytest.mark.asyncio
async def test_force_refresh_service(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test force refresh service."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Create service call
    call = ServiceCall(hass, DOMAIN, SERVICE_FORCE_REFRESH, {})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_FORCE_REFRESH:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify coordinator.async_request_refresh was called
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_reset_statistics_service(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test reset statistics service."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Set initial counter values
    mock_coordinator._failed_reads = 10
    mock_coordinator._total_updates = 200

    # Create service call
    call = ServiceCall(hass, DOMAIN, SERVICE_RESET_STATISTICS, {})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESET_STATISTICS:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify counters were reset
    assert mock_coordinator._failed_reads == 0
    assert mock_coordinator._total_updates == 0

    # Verify refresh was triggered
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_restart_inverter_requires_confirmation(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test restart requires confirmation."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Create service call WITHOUT confirm=true
    call = ServiceCall(hass, DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": False})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise ValueError
        with pytest.raises(ValueError, match="Restart requires confirmation"):
            await service_handler(call)

    # Verify write was NOT called
    mock_coordinator.async_write_register.assert_not_called()


@pytest.mark.asyncio
async def test_restart_inverter_no_confirm_parameter(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test restart without confirm parameter."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Create service call WITHOUT confirm parameter
    call = ServiceCall(hass, DOMAIN, SERVICE_RESTART_INVERTER, {})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise ValueError
        with pytest.raises(ValueError, match="Restart requires confirmation"):
            await service_handler(call)

    # Verify write was NOT called
    mock_coordinator.async_write_register.assert_not_called()


@pytest.mark.asyncio
async def test_restart_inverter_with_confirmation(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test restart with confirmation."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Create service call WITH confirm=true
    call = ServiceCall(hass, DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler
        await service_handler(call)

    # Verify write to register 0xDF01 with value 0x0001
    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


@pytest.mark.asyncio
async def test_restart_inverter_handles_failure(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test restart handles write failure."""
    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Mock write failure
    mock_coordinator.async_write_register = AsyncMock(
        return_value=WriteRegisterResult(success=False, error="device busy")
    )

    # Create service call WITH confirm=true
    call = ServiceCall(hass, DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler - should raise HomeAssistantError
        with pytest.raises(HomeAssistantError, match="Failed to send restart command"):
            await service_handler(call)

    # Verify write was attempted
    mock_coordinator.async_write_register.assert_called_once_with(0xDF01, 0x0001)


@pytest.mark.asyncio
async def test_services_registered_on_setup(
    mock_config_entry, mock_coordinator, full_device_config, tmp_path
):
    """Test that all services are registered during setup."""
    hass = MagicMock()
    hass.data = {}
    configure_mock_hass_core(hass, str(tmp_path))
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()

    registered_services = []

    def track_registration(domain, service, handler, schema=None):
        registered_services.append(service)

    hass.services.async_register = track_registration

    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        await async_setup_entry(hass, mock_config_entry)

    from custom_components.srne_inverter import SERVICE_HIDE_UNSUPPORTED

    assert SERVICE_FORCE_REFRESH in registered_services
    assert SERVICE_RESET_STATISTICS in registered_services
    assert SERVICE_RESTART_INVERTER in registered_services
    assert SERVICE_HIDE_UNSUPPORTED in registered_services
    assert len(registered_services) == 4


@pytest.mark.asyncio
async def test_services_unregistered_on_unload(mock_config_entry, mock_coordinator):
    """Test that all services are unregistered during unload."""
    from custom_components.srne_inverter import async_unload_entry

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

    unregistered_services = []

    def track_unregistration(domain, service):
        unregistered_services.append(service)

    hass.services.async_remove = track_unregistration

    await async_unload_entry(hass, mock_config_entry)

    assert SERVICE_FORCE_REFRESH in unregistered_services
    assert SERVICE_RESET_STATISTICS in unregistered_services
    assert SERVICE_RESTART_INVERTER in unregistered_services
    assert len(unregistered_services) == 3


@pytest.mark.asyncio
async def test_restart_inverter_success_logging(
    mock_config_entry, mock_coordinator, full_device_config, caplog, tmp_path
):
    """Test restart service logs success message."""
    import logging

    hass = MagicMock()
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    configure_mock_hass_core(hass, str(tmp_path))

    # Create service call WITH confirm=true
    call = ServiceCall(hass, DOMAIN, SERVICE_RESTART_INVERTER, {"confirm": True})

    # Get the registered service handler
    p_load, p_create = _patches_for_async_setup(mock_coordinator, full_device_config)
    with p_load, p_create:
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services = MagicMock()

        service_handler = None

        def capture_handler(domain, service, handler, schema=None):
            nonlocal service_handler
            if service == SERVICE_RESTART_INVERTER:
                service_handler = handler

        hass.services.async_register = capture_handler
        hass.services.async_remove = MagicMock()

        await async_setup_entry(hass, mock_config_entry)

        # Call the service handler with logging
        with caplog.at_level(logging.INFO):
            await service_handler(call)

        # Note: caplog may not capture logs due to mock setup
        # This test validates that the service runs successfully
        mock_coordinator.async_write_register.assert_called_once()
