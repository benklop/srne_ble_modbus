"""Sprint 3 structural checks against the repository (paths are repo-relative)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION = REPO_ROOT / "custom_components" / "srne_inverter"


def test_core_paths_exist():
    assert (INTEGRATION / "config_flow" / "onboarding.py").is_file()
    assert (INTEGRATION / "translations" / "en.json").is_file()
    assert (INTEGRATION / "onboarding" / "context.py").is_file()
    assert (INTEGRATION / "onboarding" / "state_machine.py").is_file()


def test_presets_exported():
    from custom_components.srne_inverter.config_flow import CONFIGURATION_PRESETS

    assert isinstance(CONFIGURATION_PRESETS, dict)
    assert len(CONFIGURATION_PRESETS) >= 1


def test_translations_json_loads():
    import json

    data = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
