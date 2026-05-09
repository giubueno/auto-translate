from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from saddleback import __version__
from saddleback.exit_codes import ExitCode

app = typer.Typer(
    name="saddleback",
    help="Local-first CLI to dub English meeting MP4s into German and Spanish audio.",
    no_args_is_help=True,
    add_completion=False,
)


def _console() -> Console:
    no_color = "NO_COLOR" in os.environ
    return Console(no_color=no_color, stderr=False)


def _enforce_python_version() -> None:
    if sys.version_info[:2] != (3, 14):
        sys.stderr.write(
            f"saddleback requires Python 3.14.x; running on {sys.version.split()[0]}.\n"
        )
        raise typer.Exit(code=ExitCode.PREFLIGHT_FAILED)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"saddleback {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        exists=True,
        readable=True,
        help="Explicit config file path.",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-error stdout."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging to stderr."),
    json_out: bool = typer.Option(False, "--json", help="Emit NDJSON status events to stdout."),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable rich progress bars."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print plan, perform no work."),
    test_mode: bool = typer.Option(
        False,
        "--test-mode",
        help="Deterministic test mode: mocked translator + cached/stub TTS. (FR43)",
    ),
    ctx: typer.Context = typer.Option(None, hidden=True),
) -> None:
    """Saddleback — entry point."""
    _enforce_python_version()
    if ctx is not None:
        ctx.ensure_object(dict)
        ctx.obj.update(
            {
                "config_path": config,
                "quiet": quiet,
                "verbose": verbose,
                "json": json_out,
                "no_progress": no_progress or "NO_COLOR" in os.environ,
                "dry_run": dry_run,
                "test_mode": test_mode,
            }
        )


@app.command()
def dub(
    ctx: typer.Context,
    source: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        dir_okay=False,
        help="Source MP4 to dub.",
    ),
    lang: str = typer.Option(
        "both",
        "--lang",
        help="Target language(s): 'de', 'es', or 'both'.",
        case_sensitive=False,
    ),
) -> None:
    """Run the full dub pipeline end-to-end."""
    from saddleback.orchestrator import run_dub

    targets = _resolve_targets(lang)
    code = run_dub(source=source, targets=targets, opts=ctx.obj or {})
    raise typer.Exit(code=int(code))


@app.command()
def regen(
    ctx: typer.Context,
    segment_id: int = typer.Argument(..., help="Segment id to regenerate."),
    lang: str = typer.Option(
        "both",
        "--lang",
        help="Target language(s) to regenerate: 'de', 'es', or 'both'.",
    ),
    shorter: bool = typer.Option(
        False,
        "--shorter",
        help="Re-prompt translator with a 'shorter' instruction.",
    ),
    run_id: str | None = typer.Option(
        None,
        "--run-id",
        help="Run id to operate on. Defaults to most recent run.",
    ),
) -> None:
    """Regenerate a single segment in an existing run."""
    from saddleback.orchestrator import run_regen

    targets = _resolve_targets(lang)
    code = run_regen(
        segment_id=segment_id,
        targets=targets,
        shorter=shorter,
        run_id=run_id,
        opts=ctx.obj or {},
    )
    raise typer.Exit(code=int(code))


@app.command()
def play(
    ctx: typer.Context,
    segment_id: int = typer.Argument(..., help="Segment id to play."),
    lang: str = typer.Option("de", "--lang", help="Language to audition: 'de' or 'es'."),
    run_id: str | None = typer.Option(None, "--run-id"),
) -> None:
    """Play a single synthesized segment via afplay (macOS) for spot-check."""
    from saddleback.orchestrator import play_segment

    code = play_segment(segment_id=segment_id, lang=lang.lower(), run_id=run_id, opts=ctx.obj or {})
    raise typer.Exit(code=int(code))


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Run preflight checks. Reports each dependency with actionable remediation."""
    from saddleback.doctor import run_doctor

    code = run_doctor(opts=ctx.obj or {})
    raise typer.Exit(code=int(code))


@app.command()
def status(
    ctx: typer.Context,
    run_id: str | None = typer.Argument(None, help="Run id; defaults to most recent."),
) -> None:
    """Report stage-completion status of a job."""
    from saddleback.orchestrator import run_status

    code = run_status(run_id=run_id, opts=ctx.obj or {})
    raise typer.Exit(code=int(code))


@app.command()
def clean(
    ctx: typer.Context,
    run_id: str | None = typer.Argument(None, help="Run id; defaults to most recent."),
    keep_outputs: bool = typer.Option(
        True,
        "--keep-outputs/--remove-outputs",
        help="Whether to keep final dubbed MP4s.",
    ),
) -> None:
    """Remove intermediate artifacts; optionally keep final outputs."""
    from saddleback.orchestrator import run_clean

    code = run_clean(run_id=run_id, keep_outputs=keep_outputs, opts=ctx.obj or {})
    raise typer.Exit(code=int(code))


def _resolve_targets(lang: str) -> list[str]:
    raw = lang.strip().lower()
    if raw in {"both", "de,es", "es,de"}:
        return ["de", "es"]
    if raw in {"de", "es"}:
        return [raw]
    if "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if all(p in {"de", "es"} for p in parts):
            return parts
    sys.stderr.write(f"unknown --lang value: {lang!r}; expected de, es, both, or de,es\n")
    raise typer.Exit(code=ExitCode.BAD_USAGE)


if __name__ == "__main__":
    app()
