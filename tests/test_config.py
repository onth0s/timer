"""Tests for the Config class and validation."""

from pathlib import Path

import pytest

from countdown.config import Config, validate_anim_mode
from countdown.pulses import VALID_ANIM_MODES


def test_config_path_default_is_project_root_yaml():
    """Config.path defaults to ./config.yaml."""
    assert Config.path == Path("config.yaml")


def test_config_default_anim_is_rich(tmp_config):
    """Default anim is 'rich' (per AGENTS.md mandate)."""
    assert Config.DEFAULT["anim"] == "rich"


def test_load_missing_file_returns_defaults(tmp_config):
    """Missing config.yaml yields defaults (no error)."""
    cfg = Config.load()
    assert cfg.get("anim") == "rich"


def test_save_then_load_roundtrip(tmp_config):
    """save() persists data; load() reads it back."""
    cfg = Config()
    cfg.set("anim", "drawille")
    cfg.save()
    assert tmp_config.exists()

    cfg2 = Config.load()
    assert cfg2.get("anim") == "drawille"


def test_set_then_save_writes_valid_yaml(tmp_config):
    """Save produces a parseable YAML file with expected key."""
    cfg = Config()
    cfg.set("anim", "smooth")
    cfg.save()

    contents = tmp_config.read_text()
    assert "anim: smooth" in contents


def test_save_creates_parent_directory(tmp_path, monkeypatch):
    """Save creates missing parent dirs."""
    from countdown import config as config_mod

    target = tmp_path / "nested" / "dir" / "config.yaml"
    monkeypatch.setattr(config_mod.Config, "path", target)

    cfg = Config()
    cfg.set("anim", "ghostprint")
    cfg.save()
    assert target.exists()


def test_set_invalid_anim_raises(tmp_config):
    """set() rejects invalid anim values."""
    cfg = Config()
    with pytest.raises(ValueError) as exc:
        cfg.set("anim", "neon-rave")
    msg = str(exc.value)
    assert "neon-rave" in msg
    for mode in VALID_ANIM_MODES:
        assert mode in msg


def test_load_rejects_invalid_anim_from_disk(tmp_config):
    """Loading an invalid anim value from disk raises ValueError."""
    tmp_config.write_text("anim: neon-rave\n")
    with pytest.raises(ValueError) as exc:
        Config.load()
    assert "neon-rave" in str(exc.value)


def test_load_rejects_empty_config_file(tmp_config):
    """An empty YAML file is valid and yields defaults."""
    tmp_config.write_text("")
    cfg = Config.load()
    assert cfg.get("anim") == "rich"


def test_load_rejects_yaml_with_unknown_keys(tmp_config):
    """Unknown keys are preserved as-is (no strict key allowlist)."""
    tmp_config.write_text("anim: rich\nfoo: bar\n")
    cfg = Config.load()
    assert cfg.get("anim") == "rich"
    assert cfg.get("foo") == "bar"


def test_load_rejects_non_mapping_yaml(tmp_config):
    """A list or scalar at the top level raises ValueError."""
    tmp_config.write_text("- 1\n- 2\n")
    with pytest.raises(ValueError):
        Config.load()


def test_validate_anim_mode_accepts_all_valid_modes():
    """All valid modes pass validation."""
    for mode in VALID_ANIM_MODES:
        validate_anim_mode(mode)  # should not raise


def test_validate_anim_mode_rejects_unknown():
    """Unknown modes raise ValueError listing valid options."""
    with pytest.raises(ValueError) as exc:
        validate_anim_mode("definitely-not-a-mode")
    msg = str(exc.value)
    assert "definitely-not-a-mode" in msg
    for mode in VALID_ANIM_MODES:
        assert mode in msg


def test_validate_anim_mode_rejects_empty_string():
    """Empty string is not a valid mode."""
    with pytest.raises(ValueError):
        validate_anim_mode("")


def test_as_dict_returns_copy(tmp_config):
    """as_dict returns a defensive copy."""
    cfg = Config()
    data = cfg.as_dict()
    data["anim"] = "mutated"
    assert cfg.get("anim") == "rich"


def test_get_returns_none_for_missing_key(tmp_config):
    """get() returns the supplied default for missing keys."""
    cfg = Config()
    assert cfg.get("nonexistent") is None
    assert cfg.get("nonexistent", "fallback") == "fallback"
