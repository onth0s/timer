"""BDD step definitions for format_duration.feature."""

from pytest_bdd import given, parsers, scenarios, then, when

from countdown import timer

scenarios("format_duration.feature")


@given(
    parsers.parse("a duration of {seconds:d} total seconds"),
    target_fixture="ctx",
)
def given_duration_seconds(seconds):
    return {"seconds": seconds, "formatted": None}


@when("I format it")
def when_format_it(ctx):
    dur = timer.Duration(
        total_seconds=ctx["seconds"], components={"s": ctx["seconds"]}
    )
    compact = timer.compact(dur)
    ctx["formatted"] = timer.format_duration(compact)


@then(parsers.parse('the formatted string should be "{display}"'))
def then_formatted_string(ctx, display):
    assert ctx["formatted"] == display, (
        f"Got {ctx['formatted']!r}, expected {display!r}"
    )
