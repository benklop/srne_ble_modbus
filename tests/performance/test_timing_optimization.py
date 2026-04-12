"""Performance-oriented checks for timing configuration and batch use case."""

import time
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.srne_inverter.application.use_cases.refresh_data_use_case import (
    RefreshDataUseCase,
)
from custom_components.srne_inverter.const import (
    MAX_CONSECUTIVE_TIMEOUTS,
    MODBUS_RESPONSE_TIMEOUT,
)


class TestTimingConfiguration:
    """Validate timing constants match the integration defaults."""

    def test_modbus_response_timeout_sane(self):
        assert 0.5 <= MODBUS_RESPONSE_TIMEOUT <= 3.0

    def test_circuit_breaker_threshold(self):
        assert MAX_CONSECUTIVE_TIMEOUTS >= 3


class TestRefreshBatchTiming:
    """Lightweight checks on batch read path (mocked transport)."""

    @pytest.mark.asyncio
    async def test_read_batch_completes_under_timeout(self):
        conn_manager = Mock()
        transport = Mock()
        transport.is_connected = True
        transport.send = AsyncMock(
            return_value=bytes(
                [
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x01,
                    0x03,
                    0x04,
                    0x01,
                    0xE6,
                    0x00,
                    0xFA,
                    0x9F,
                    0x1C,
                ]
            )
        )
        protocol = Mock()
        protocol.build_read_command = Mock(
            return_value=bytes([0x01, 0x03, 0x01, 0x00, 0x00, 0x02, 0xC4, 0x0B])
        )
        protocol.decode_response = Mock(return_value={0: 486, 1: 250})

        use_case = RefreshDataUseCase(conn_manager, transport, protocol)
        start = time.time()
        result = await use_case._read_batch(0x0100, 2, 1)
        duration = time.time() - start

        assert result is not None
        assert duration < MODBUS_RESPONSE_TIMEOUT

    def test_use_case_tracks_batch_timings(self):
        conn_manager = Mock()
        transport = Mock()
        protocol = Mock()
        use_case = RefreshDataUseCase(conn_manager, transport, protocol)
        assert hasattr(use_case, "_batch_timings")
        assert hasattr(use_case, "_total_batches_processed")
        assert use_case._total_batches_processed == 0
