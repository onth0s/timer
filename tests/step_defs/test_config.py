"""BDD step definitions for config.feature."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from countdown.config import Config

scenarios("config.feature")


@pytest.fixture
def ctx():
    return {}


@given("no config file exists", target_fixture="ctx")
def given_no_config_file(tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)
    return {"path": p, "config": None, "error": None}


@when("I load the config")
def when_load_config(ctx):
    try:
        ctx["config"] = Config.load()
    except ValueError as exc:
        ctx["error"] = exc


@then("the anim value should be None")
def then_anim_is_none(ctx):
    # Default config has anim="rich", get("anim") returns "rich"
    assert ctx["config"].get("anim") == "rich"


@given(parsers.parse('I set anim to "{mode}"'), target_fixture="ctx")
def given_set_anim(mode, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    monkeypatch.setattr(Config, "path", p)
    cfg = Config()
    error = None
    try:
        cfg.set("anim", mode)
    except ValueError as exc:
        error = exc
    return {"config": cfg, "error": error, "mode": mode}


@then("no error should be raised")
def then_no_error(ctx):
    assert ctx["error"] is None, f"Unexpected error: {ctx['error']}"


@then("a ValueError should be raised listing valid options")
def then_value_error_options(ctx):
    assert ctx["error"] is not None, "Expected ValueError but none was raised"
    assert isinstance(ctx["error"], ValueError)
    assert "Valid modes:" in str(ctx["error"])


@given(parsers.parse('a config file containing anim "{mode}"'), target_fixture="ctx")
def given_config_file_with_anim(mode, tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    p.write_text(f"anim: {mode}\n", encoding="utf-8")
    monkeypatch.setattr(Config, "path", p)
    return {"path": p, "config": None, "error": None}
