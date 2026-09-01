"""BDD step definitions for countup_display.feature."""

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("countup_display.feature")


@given(
    parsers.parse("the stopwatch has been running for {elapsed:d} seconds"),
    target_fixture="ctx",
)
def given_stopwatch_elapsed(elapsed):
    return {"elapsed": elapsed, "time_str": None}


@when("the display renders")
def when_display_renders(ctx):
    from countdown.timer import _format_time_string

    ctx["time_str"] = _format_time_string(ctx["elapsed"], count_up=True)


@then(parsers.parse('the rendered time string should be "{expected}"'))
def then_rendered_time_string(ctx, expected):
    assert ctx["time_str"] == expected, (
        f"At {ctx['elapsed']}s: got {ctx['time_str']!r}, expected {expected!r}"
    )
