"""Tests for calculated sensors defined via YAML formulas."""

from unittest.mock import MagicMock

import pytest

from custom_components.srne_inverter.entities.configurable_sensor import (
    ConfigurableSensor,
)


@pytest.fixture
def mock_config_entry():
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.title = "Test SRNE Inverter"
    entry.data = {}
    return entry


def _coordinator(data):
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.is_register_failed = MagicMock(return_value=False)
    coordinator.is_entity_unavailable = MagicMock(return_value=False)
    return coordinator


def test_self_sufficiency_formula(mock_config_entry):
    coordinator = _coordinator(
        {"pv_power": 1500, "load_power": 3000, "connected": True}
    )
    cfg = {
        "entity_id": "self_sufficiency",
        "name": "Self Sufficiency",
        "source_type": "calculated",
        "depends_on": ["pv_power", "load_power"],
        "formula": "{{ ([100, (pv_power / load_power * 100)] | min) if load_power else 100 }}",
        "unit_of_measurement": "%",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    assert sensor.native_value == 50.0


def test_self_sufficiency_clamped_to_100(mock_config_entry):
    coordinator = _coordinator(
        {"pv_power": 5000, "load_power": 3000, "connected": True}
    )
    cfg = {
        "entity_id": "self_sufficiency",
        "name": "Self Sufficiency",
        "source_type": "calculated",
        "depends_on": ["pv_power", "load_power"],
        "formula": "{{ ([100, (pv_power / load_power * 100)] | min) if load_power else 100 }}",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    assert sensor.native_value == 100.0


def test_battery_power_signed_sum(mock_config_entry):
    coordinator = _coordinator(
        {
            "pv_power": 2000,
            "load_power": 1500,
            "grid_power": -200,
            "connected": True,
        }
    )
    cfg = {
        "entity_id": "battery_power",
        "name": "Battery Power",
        "source_type": "calculated",
        "depends_on": ["pv_power", "load_power", "grid_power"],
        "formula": "{{ pv_power - load_power - grid_power }}",
        "unit_of_measurement": "W",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    assert sensor.native_value == 700.0


def test_energy_from_grid_import_only(mock_config_entry):
    """Grid import magnitude: positive grid_power counts, export yields 0."""
    for grid_w, expected in ((1500, 1500), (-800, 0), (0, 0)):
        coordinator = _coordinator({"grid_power": grid_w, "connected": True})
        cfg = {
            "entity_id": "energy_from_grid",
            "name": "Energy from grid",
            "source_type": "calculated",
            "depends_on": ["grid_power"],
            "formula": "{{ [0, grid_power] | max }}",
            "unit_of_measurement": "W",
        }
        sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
        assert sensor.native_value == float(expected)


def test_grid_input_apparent_power(mock_config_entry):
    coordinator = _coordinator(
        {"grid_voltage": 230.0, "grid_current": 5.0, "connected": True}
    )
    cfg = {
        "entity_id": "grid_input_apparent_power",
        "name": "Grid input (V×I)",
        "source_type": "calculated",
        "depends_on": ["grid_voltage", "grid_current"],
        "formula": "{{ (grid_voltage | float(0) * grid_current | float(0)) | round(1) }}",
        "unit_of_measurement": "VA",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    assert sensor.native_value == 1150.0


def test_grid_power_balance_estimate(mock_config_entry):
    """P_grid ≈ P_load_proxy - P_pv - P_batt with P_load = V_inv * I_load."""
    coordinator = _coordinator(
        {
            "inverter_voltage": 230.0,
            "load_current": 10.0,
            "pv_total_power": 1000.0,
            "battery_voltage_sensor": 52.0,
            "battery_current": -20.0,
            "connected": True,
        }
    )
    cfg = {
        "entity_id": "grid_power_balance_estimate",
        "name": "Grid power (balance estimate)",
        "source_type": "calculated",
        "depends_on": [
            "inverter_voltage",
            "load_current",
            "pv_total_power",
            "battery_voltage_sensor",
            "battery_current",
        ],
        "formula": "{{ ((inverter_voltage | float(0)) * (load_current | float(0)) - (pv_total_power | float(0)) - (battery_voltage_sensor | float(0)) * (battery_current | float(0))) | round(1) }}",
        "unit_of_measurement": "W",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    # 2300 - 1000 - (52 * -20) = 2300 - 1000 + 1040 = 2340
    assert sensor.native_value == 2340.0


def test_grid_current_balance_estimate(mock_config_entry):
    coordinator = _coordinator(
        {
            "grid_voltage": 230.0,
            "inverter_voltage": 230.0,
            "load_current": 10.0,
            "pv_total_power": 1000.0,
            "battery_voltage_sensor": 52.0,
            "battery_current": 0.0,
            "connected": True,
        }
    )
    cfg = {
        "entity_id": "grid_current_balance_estimate",
        "name": "Grid current (balance estimate)",
        "source_type": "calculated",
        "depends_on": [
            "grid_voltage",
            "inverter_voltage",
            "load_current",
            "pv_total_power",
            "battery_voltage_sensor",
            "battery_current",
        ],
        "formula": "{% set v = grid_voltage | float(0) %}{% set p = (inverter_voltage | float(0)) * (load_current | float(0)) - (pv_total_power | float(0)) - (battery_voltage_sensor | float(0)) * (battery_current | float(0)) %}{% if v > 10 %}{{ (p / v) | round(2) }}{% else %}0.0{% endif %}",
        "unit_of_measurement": "A",
    }
    sensor = ConfigurableSensor(coordinator, mock_config_entry, cfg)
    # p = 2300 - 1000 = 1300, 1300/230 ≈ 5.65
    assert sensor.native_value == pytest.approx(5.65, rel=1e-3)
