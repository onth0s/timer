"""Click group/command subclasses and argument-routing helpers.

These live apart from ``__main__`` so the command tree stays focused on
declaring subcommands while argument munging (dash-prefixed durations,
typo-tolerant dispatch) is reusable and independently testable.
"""

from __future__ import annotations

import difflib

import click

#: Options the top-level group recognises as its own.
_GROUP_OPTS = frozenset({"-h", "--help", "--version"})
#: Options any nested group recognises as its own.
_GROUP_OPTS_LIST = frozenset({"-h", "--help"})


def _fix_dash_args(cmd: click.Command, args: list[str]) -> list[str]:
    """Insert '--' before positional arguments starting with '-' that aren't recognized options."""
    if not args or "--" in args:
        return args

    opt_names = set()
    for param in cmd.params:
        if isinstance(param, click.Option):
            opt_names.update(param.opts)
            opt_names.update(param.secondary_opts)
    opt_names.update({"-h", "--help"})

    new_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("-") and arg not in opt_names:
            new_args.append("--")
            new_args.extend(args[i:])
            return new_args

        new_args.append(arg)
        for param in cmd.params:
            if isinstance(param, click.Option) and (
                arg in param.opts or arg in param.secondary_opts
            ):
                if not param.is_flag and i + 1 < len(args):
                    i += 1
                    new_args.append(args[i])
                break
        i += 1

    return new_args


def _is_duration_token(token: str) -> bool:
    """Return True if ``token`` parses as a timer duration."""
    from . import timer

    try:
        timer.duration(token)
    except ValueError:
        return False
    return True


def _command_suggestions(token: str, commands: dict) -> list[str]:
    """Return close command-name matches for ``token``, capped at 3."""
    return difflib.get_close_matches(token, commands, n=3, cutoff=0.5)


def _resolve_typo_command(token: str, commands: dict) -> str | None:
    """Return the command ``token`` most likely means, or None.

    Only non-duration tokens that fuzzy-match a command name are resolved, so
    `timer 5` / `timer -4:40PM` still count as durations (routed to ``run``)
    while `timer sch` -- which is *not* a duration -- dispatches to
    ``schedule``.
    """
    if _is_duration_token(token):
        return None
    suggestions = _command_suggestions(token, commands)
    if not suggestions:
        return None
    return suggestions[0]


class RunCommand(click.Command):
    """Command subclass for `run` that pre-processes dash-prefixed duration arguments."""

    def parse_args(self, ctx, args):
        """Pre-process dash-prefixed positional arguments before Click option parsing."""
        fixed_args = _fix_dash_args(self, args)
        return super().parse_args(ctx, fixed_args)


class SmartGroup(click.Group):
    """Group that forwards unmatched positional args to a matching subcommand.

    Lets ``timer 5`` / ``timer -4:40PM`` work as aliases for ``timer run ...``,
    and routes ambiguous spellings like ``timer sch`` straight to ``schedule``.
    """

    def _route(self, args):
        """Return subcommand-prefixed args for an unknown leading token, or None."""
        first = args[0]
        target = _resolve_typo_command(first, self.commands)
        if target:
            return [target] + list(args[1:])
        if "run" in self.commands:
            fixed_args = _fix_dash_args(self.commands["run"], args)
            return ["run"] + fixed_args
        return None

    def parse_args(self, ctx, args):
        """Forward non-subcommand arguments to a matching subcommand."""
        if args:
            first = args[0]
            if first not in self.commands and first not in _GROUP_OPTS:
                routed = self._route(args)
                if routed is not None:
                    return super().parse_args(ctx, routed)
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx, args):
        """Route non-subcommand positional args to a matching subcommand."""
        if args and args[0] not in self.commands:
            routed = self._route(args)
            if routed is not None:
                return routed[0], self.commands[routed[0]], routed[1:]
        return super().resolve_command(ctx, args)


class ScheduleGroup(click.Group):
    """Group that routes non-subcommand tokens to the catch-all ``at`` command.

    Protects dash-prefixed target times (e.g. ``-23:45``) from Click's option
    parser, mirroring how ``SmartGroup`` forwards to ``run``.
    """

    def parse_args(self, ctx, args):
        """Rewrite unrecognized first tokens into the catch-all command."""
        if args:
            first = args[0]
            if first not in self.commands and first not in _GROUP_OPTS_LIST:
                at_cmd = self.commands.get("at")
                if at_cmd:
                    fixed_args = _fix_dash_args(at_cmd, args)
                    return super().parse_args(ctx, ["at"] + fixed_args)
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx, args):
        """Route non-subcommand tokens to the catch-all command."""
        if args and args[0] not in self.commands:
            return "at", self.commands["at"], args
        return super().resolve_command(ctx, args)


class ScheduleAtCommand(click.Command):
    """Catch-all command whose dash-prefixed positionals survive Click."""

    def parse_args(self, ctx, args):
        """Re-protect dash-prefixed positionals (idempotent)."""
        fixed_args = _fix_dash_args(self, args)
        return super().parse_args(ctx, fixed_args)


__all__ = [
    "RunCommand",
    "ScheduleAtCommand",
    "ScheduleGroup",
    "SmartGroup",
    "_command_suggestions",
    "_fix_dash_args",
    "_is_duration_token",
    "_resolve_typo_command",
]
