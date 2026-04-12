"""Unit tests for TimeoutLearner.

Tests the timeout calculation logic for adaptive timeout optimization (Phase 3).
"""

import pytest
from unittest.mock import Mock

from custom_components.srne_inverter.application.services.timing_collector import (
    TimingCollector,
    TimingStats,
)
from custom_components.srne_inverter.application.services.timeout_learner import (
    TimeoutLearner,
    TIMEOUT_SAFETY_MULTIPLIER,
)
from custom_components.srne_inverter.const import (
    TIMING_MIN_SAMPLES,
    TIMING_MIN_TIMEOUT,
    TIMING_MAX_TIMEOUT,
)


class TestTimeoutLearnerInitialization:
    """Test TimeoutLearner initialization."""

    def test_learner_initialization(self):
        """Test learner initializes with collector."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        assert learner._collector is collector


class TestCalculateTimeout:
    """Test timeout calculation logic."""

    def test_calculate_timeout_insufficient_data(self):
        """Test returns None with insufficient samples (<20)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Only 10 samples (less than TIMING_MIN_SAMPLES = 20)
        for i in range(10):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        assert learner.calculate_timeout("modbus_read") is None

    def test_calculate_timeout_with_sufficient_data(self):
        """Test calculates timeout with sufficient samples (>=20)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Record 20 samples with P95 around 580ms
        for i in range(20):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        # P95 ~580ms -> 0.58s * 1.5 = 0.87s
        assert 0.7 < learned.timeout < 1.0

    def test_calculate_timeout_formula(self):
        """Test timeout calculation formula: P95 * 1.5."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Create controlled dataset with known P95
        # Use 100 samples: 1-100ms, P95 should be ~95ms
        for i in range(1, 101):
            collector.record("modbus_read", float(i), success=True)

        learned = learner.calculate_timeout("modbus_read")

        # P95 ~95ms -> 0.095s * 1.5 = 0.1425s, clamped to TIMING_MIN_TIMEOUT
        assert learned is not None
        assert learned.timeout == TIMING_MIN_TIMEOUT

    def test_calculate_timeout_min_clamping(self):
        """Test clamping to TIMING_MIN_TIMEOUT (0.3s)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Very fast operations: 10-30ms
        for i in range(20):
            collector.record("modbus_read", 10.0 + i, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert learned.timeout == TIMING_MIN_TIMEOUT

    def test_calculate_timeout_max_clamping(self):
        """Test clamping to TIMING_MAX_TIMEOUT (5.0s)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Very slow operations: 4000-5000ms
        for i in range(20):
            collector.record("modbus_read", 4000.0 + i * 50, success=True)

        learned = learner.calculate_timeout("modbus_read")

        # P95 ~4950ms -> 4.95s * 1.5 = 7.425s -> clamped to max
        assert learned is not None
        assert learned.timeout == TIMING_MAX_TIMEOUT

    def test_calculate_timeout_no_clamping_needed(self):
        """Test timeout calculation without clamping."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Operations around 800ms, P95 should be ~1000ms
        for i in range(20):
            collector.record("modbus_read", 800.0 + i * 10, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert TIMING_MIN_TIMEOUT < learned.timeout < TIMING_MAX_TIMEOUT
        assert 1.3 < learned.timeout < 1.6

    def test_calculate_timeout_nonexistent_operation(self):
        """Test returns None for operation with no data."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        timeout = learner.calculate_timeout("nonexistent")

        assert timeout is None

    def test_calculate_timeout_rounding(self):
        """Test timeout is rounded to 3 decimal places."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Create dataset with P95 that will produce non-round number
        for i in range(20):
            collector.record("modbus_read", 666.0 + i * 10, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert len(str(learned.timeout).split(".")[-1]) <= 3


class TestCalculateAllTimeouts:
    """Test calculate_all_timeouts functionality."""

    def test_calculate_all_timeouts_multiple_operations(self):
        """Test calculating timeouts for multiple operations."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Record sufficient data for multiple operations
        for i in range(25):
            collector.record("modbus_read", 400.0 + i * 10, success=True)
            collector.record("ble_write", 120.0 + i * 5, success=True)
            collector.record("ble_connect", 2000.0 + i * 50, success=True)

        timeouts = learner.calculate_all_timeouts()

        assert len(timeouts) == 3
        assert "modbus_read" in timeouts
        assert "ble_write" in timeouts
        assert "ble_connect" in timeouts

        for _op, learned in timeouts.items():
            assert TIMING_MIN_TIMEOUT <= learned.timeout <= TIMING_MAX_TIMEOUT

    def test_calculate_all_timeouts_excludes_insufficient_data(self):
        """Test excludes operations with insufficient samples."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Sufficient data for modbus_read
        for i in range(25):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        # Insufficient data for ble_write (only 10 samples)
        for i in range(10):
            collector.record("ble_write", 120.0 + i * 5, success=True)

        timeouts = learner.calculate_all_timeouts()

        assert "modbus_read" in timeouts
        assert "ble_write" not in timeouts

    def test_calculate_all_timeouts_empty_collector(self):
        """Test with no measurements."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        timeouts = learner.calculate_all_timeouts()

        assert len(timeouts) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_calculate_timeout_exactly_min_samples(self):
        """Test with exactly TIMING_MIN_SAMPLES (20) samples."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Exactly 20 samples
        for i in range(TIMING_MIN_SAMPLES):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        assert learner.calculate_timeout("modbus_read") is not None

    def test_calculate_timeout_one_less_than_min(self):
        """Test with one less than required samples."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # 19 samples (one less than required)
        for i in range(TIMING_MIN_SAMPLES - 1):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        assert learner.calculate_timeout("modbus_read") is None

    def test_calculate_timeout_with_outliers(self):
        """Test timeout calculation handles outliers appropriately."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Most samples around 400ms
        for i in range(18):
            collector.record("modbus_read", 400.0, success=True)

        # Add outliers (timeouts)
        collector.record("modbus_read", 5000.0, success=False)
        collector.record("modbus_read", 5000.0, success=False)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert learned.timeout <= TIMING_MAX_TIMEOUT

    def test_calculate_timeout_all_failures(self):
        """Test timeout calculation with all failed operations."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # All failures (timeouts)
        for i in range(20):
            collector.record("modbus_read", 5000.0, success=False)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert learned.timeout == TIMING_MAX_TIMEOUT

    def test_calculate_timeout_mixed_success_failure(self):
        """Test with mixed success and failure rates."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # 80% success, 20% failure
        for i in range(16):
            collector.record("modbus_read", 400.0 + i * 10, success=True)
        for i in range(4):
            collector.record("modbus_read", 2000.0, success=False)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert learned.timeout > 0.5


class TestRealisticScenarios:
    """Test realistic hardware scenarios."""

    def test_fast_hardware_optimization(self):
        """Test timeout learning for fast hardware (0.3-0.4s responses)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Fast BLE responses: 300-400ms
        for i in range(25):
            collector.record("modbus_read", 300.0 + i * 4, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert 0.5 < learned.timeout < 0.8

    def test_slow_hardware_adaptation(self):
        """Test timeout learning for slow hardware (1.5-2.5s responses)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Slow BLE responses: 1500-2500ms
        for i in range(25):
            collector.record("modbus_read", 1500.0 + i * 40, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert 3.5 < learned.timeout < 4.0

    def test_variable_hardware_adaptation(self):
        """Test timeout learning for variable hardware (0.5-1.5s responses)."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Variable responses: 500-1500ms
        for i in range(25):
            collector.record("modbus_read", 500.0 + i * 40, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert 2.0 < learned.timeout < 2.5

    def test_raspberry_pi_scenario(self):
        """Test scenario matching Raspberry Pi 3B+ characteristics."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Raspberry Pi 3B+ typical responses: 800-1200ms with occasional 1500ms
        for i in range(22):
            collector.record("modbus_read", 800.0 + i * 15, success=True)
        # Add some slower responses
        collector.record("modbus_read", 1400.0, success=True)
        collector.record("modbus_read", 1500.0, success=True)
        collector.record("modbus_read", 1300.0, success=True)

        learned = learner.calculate_timeout("modbus_read")

        assert learned is not None
        assert 1.8 < learned.timeout < 2.8


class TestIntegrationWithTimingCollector:
    """Test integration between TimeoutLearner and TimingCollector."""

    def test_learner_uses_collector_statistics(self):
        """Test learner properly uses collector statistics."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Record measurements
        for i in range(25):
            collector.record("modbus_read", 400.0 + i * 10, success=True)

        # Get statistics directly
        stats = collector.get_statistics("modbus_read")

        learned = learner.calculate_timeout("modbus_read")

        expected_timeout = (stats.p95_ms / 1000.0) * TIMEOUT_SAFETY_MULTIPLIER
        expected_clamped = max(
            TIMING_MIN_TIMEOUT,
            min(TIMING_MAX_TIMEOUT, expected_timeout),
        )

        assert learned is not None
        assert abs(learned.timeout - expected_clamped) < 0.001

    def test_learner_updates_with_new_measurements(self):
        """Test learner reflects new measurements."""
        collector = TimingCollector(sample_size=100)
        learner = TimeoutLearner(collector)

        # Initial measurements: fast responses
        for i in range(20):
            collector.record("modbus_read", 300.0 + i * 5, success=True)

        learned1 = learner.calculate_timeout("modbus_read")

        # Add slow responses
        for i in range(10):
            collector.record("modbus_read", 1000.0, success=True)

        learned2 = learner.calculate_timeout("modbus_read")

        assert learned2.timeout > learned1.timeout
