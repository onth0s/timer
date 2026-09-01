"""BDD step definitions for rich_pulse.feature."""

from pytest_bdd import given, scenarios, then, when

from countdown.digits import CHARS_BY_SIZE, DIGIT_SIZES
from countdown.display import horizontal_padding, visual_width
from countdown.pulses import ansi, rich
from countdown.timer import get_number_lines

scenarios("rich_pulse.feature")

_TEST_CHARS = CHARS_BY_SIZE[min(DIGIT_SIZES)]
_PHASE = 0.5


@given("the zero timer glyph lines", target_fixture="ctx")
def given_zero_lines():
    return {"lines": get_number_lines(0, _TEST_CHARS)}


@when("I style them with the rich pulse at phase 0.5")
def when_style_rich(ctx):
    ctx["styled"] = rich.style_lines(ctx["lines"], _PHASE)


@when("I style them with the rich and ansi pulses at phase 0.5")
def when_style_rich_and_ansi(ctx):
    ctx["styled"] = rich.style_lines(ctx["lines"], _PHASE)
    ctx["ansi_styled"] = ansi.style_lines(ctx["lines"], _PHASE)


@then("every styled line has the same visible width as the raw line")
def then_visible_width_matches(ctx):
    for raw, styled in zip(ctx["lines"], ctx["styled"], strict=True):
        assert visual_width(styled) == len(raw.rstrip()), (
            f"styled width {visual_width(styled)} != raw width "
            f"{len(raw.rstrip())}"
        )


@then("the widest styled line equals the raw glyph width")
def then_widest_matches(ctx):
    styled_widest = max(visual_width(line) for line in ctx["styled"])
    raw_widest = max(len(line.rstrip()) for line in ctx["lines"])
    assert styled_widest == raw_widest


@then("both pulses need the same horizontal padding")
def then_same_padding(ctx):
    pad_rich = horizontal_padding(ctx["styled"], 120)
    pad_ansi = horizontal_padding(ctx["ansi_styled"], 120)
    assert pad_rich == pad_ansi, (
        f"rich h_pad={pad_rich} != ansi h_pad={pad_ansi} — rich is shifted"
    )
