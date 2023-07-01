"""
xxx
"""

import argparse
import functools
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from io import IOBase
from pathlib import Path

import tomli

print_err = functools.partial(print, file=sys.stderr)


if sys.version_info < (3, 9):
    print_err(f"at least Python 3.9 is required")
    exit(1)


def command(*args) -> list[str]:
    return [
        str(sub_arg)
        for arg in args
        for sub_arg in (shlex.split(arg) if isinstance(arg, str) else arg)
    ]


@dataclass
class Ctx:
    stdin: IOBase
    stdout: IOBase
    stderr: IOBase
    argv: list[str]

    @staticmethod
    def from_env() -> "Ctx":
        return Ctx(
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            argv=sys.argv,
        )

    def run(self, *args, **kwargs):
        kwargs.setdefault("check", True)
        kwargs.setdefault("text", True)
        kwargs.setdefault("stdin", self.stdin)
        kwargs.setdefault("stdout", self.stdout)
        kwargs.setdefault("stderr", self.stderr)
        return subprocess.run(command(*args), **kwargs)


@dataclass
class BackupSource:
    source: Path
    archive_name: str


valid_archive_name_re = re.compile(r"^[\w\d_-]{1,100}$")


@dataclass
class Borg:
    ctx: Ctx
    env: dict[str, str]
    backup_sources: dict[str, BackupSource]

    def run_borg(self, *args, **kwargs):
        env = kwargs.get("env", self.env)
        for env_var, value in self.env.items():
            env.setdefault(env_var, value)

        print(repr(self))
        self.ctx.run("borg", *args, env={**os.environ, **self.env}, **kwargs)

    @staticmethod
    def from_config_file(ctx: Ctx, config_file: Path) -> "Borg":
        with config_file.open("rb") as fp:
            raw_config = tomli.load(fp)

        backup_sources = []
        for raw_src_name, raw_src_config in raw_config.get("backup", {}).items():
            assert (
                "source_dir" in raw_src_config
            ), f"backup.{raw_src_name} must contain 'source_dir', but got {raw_src_config.keys()}"
            raw_config.setdefault("archive_name", raw_src_name)
            archive_name = raw_config["archive_name"]
            assert valid_archive_name_re.match(
                archive_name
            ), f"archive name must be alphanumeric and 1-100 chars, but got: {archive_name!r}"
            backup_sources.append(
                BackupSource(
                    Path(raw_src_config["source_dir"]).expanduser(), archive_name
                )
            )

        return Borg(ctx, raw_config.get("env", {}), backup_sources)


def action_help(borg: Borg, parser: argparse.ArgumentParser):
    parser.print_help(borg.ctx.stderr)


def action_borg(borg: Borg, command: list[str]):
    borg.run_borg(*command)


def main(ctx: Ctx):
    parser = argparse.ArgumentParser(prog=Path(ctx.argv[0]).name, description=__doc__)
    parser.set_defaults(action=functools.partial(action_help, parser=parser))

    parser.add_argument(
        "--config", "-c", default="backup-config.toml", help="Backup config file"
    )

    subparsers = parser.add_subparsers(title="Command")

    _subparser_help = subparsers.add_parser(
        "help", help="Show this help message and exit"
    )

    subparser_borg = subparsers.add_parser("borg", help="Run a command with `borg`")
    subparser_borg.set_defaults(action=action_borg)
    subparser_borg.add_argument("command", nargs="*", help="Borg command to execute")

    parsed_args = vars(parser.parse_args(ctx.argv[1:]))
    config_file = Path(parsed_args.pop("config")).expanduser()
    borg = Borg.from_config_file(ctx, config_file)
    action = parsed_args.pop("action")
    action(borg, **parsed_args)


if __name__ == "__main__":
    main(Ctx.from_env())
