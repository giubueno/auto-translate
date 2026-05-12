from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from saddleback.config import Config, load_config
from saddleback.exit_codes import ExitCode
from saddleback.jobdir import find_run_dir, make_run_id
from saddleback.types import Manifest, StageStatus, Segment, Translation, now_iso, read_json, write_json


_CANCELLED = False


def _install_sigint_handler() -> None:
    def handler(signum, frame):
        global _CANCELLED
        _CANCELLED = True
        sys.stderr.write("\nsaddleback: SIGINT received, finishing current step then exiting\n")

    signal.signal(signal.SIGINT, handler)


def _check_cancelled() -> None:
    if _CANCELLED:
        raise KeyboardInterrupt()


def _console(opts: dict[str, Any]) -> Console:
    return Console(no_color="NO_COLOR" in os.environ, quiet=opts.get("quiet", False))


def _emit_event(opts: dict[str, Any], **fields: Any) -> None:
    if opts.get("json"):
        fields = {"ts": now_iso(), **fields}
        print(json.dumps(fields), flush=True)


def _open_manifest(run_dir: Path, source: Path, targets: list[str], cfg: Config) -> Manifest:
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        return Manifest.model_validate(read_json(manifest_path))
    return Manifest(
        run_id=run_dir.name,
        source_path=str(source.resolve()),
        targets=targets,
        config_snapshot=cfg.model_dump(mode="json"),
    )


def _save_manifest(run_dir: Path, manifest: Manifest) -> None:
    write_json(run_dir / "manifest.json", manifest)


def _record_stage(manifest: Manifest, name: str, ok: bool, detail: str = "", artifacts: list[Path] | None = None) -> None:
    manifest.stages[name] = StageStatus(
        name=name,
        started_at=manifest.stages.get(name, StageStatus(name=name)).started_at,
        finished_at=now_iso(),
        ok=ok,
        detail=detail,
        artifact_paths=[str(p) for p in (artifacts or [])],
    )


def _start_stage(manifest: Manifest, name: str) -> None:
    if name not in manifest.stages or manifest.stages[name].started_at is None:
        manifest.stages[name] = StageStatus(name=name, started_at=now_iso())


def _stage_done(manifest: Manifest, name: str) -> bool:
    s = manifest.stages.get(name)
    return bool(s and s.ok)


# ---------------------------------------------------------------------------
# dub
# ---------------------------------------------------------------------------


def run_dub(source: Path, targets: list[str], opts: dict[str, Any]) -> ExitCode:
    cfg = load_config(explicit_path=opts.get("config_path"))
    cfg = _apply_runtime_overrides(cfg, opts)
    console = _console(opts)
    runs_root = cfg.runtime.runs_dir.resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    # Find or create a run dir for this source.
    from saddleback.jobdir import existing_run_dir_for_source

    run_dir = existing_run_dir_for_source(runs_root, source)
    if run_dir is None:
        run_dir = runs_root / make_run_id(source)
        run_dir.mkdir(parents=True)

    if opts.get("dry_run"):
        console.print(f"[cyan]dry-run[/]: would dub {source} → {targets} in {run_dir}")
        return ExitCode.OK

    _install_sigint_handler()
    manifest = _open_manifest(run_dir, source, targets, cfg)
    _emit_event(opts, event="run_start", run_id=run_dir.name, targets=targets)

    started = time.monotonic()
    try:
        # Stage 1: extract
        _start_stage(manifest, "extract")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.extract import ExtractError, run as extract_run

        try:
            audio_artifacts = extract_run(source, run_dir, cfg)
        except ExtractError as exc:
            _record_stage(manifest, "extract", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]extract failed:[/] {exc}")
            return ExitCode.SOURCE_UNUSABLE
        _record_stage(manifest, "extract", ok=True, artifacts=list(audio_artifacts.values()))
        _emit_event(opts, event="stage_done", stage="extract")
        _check_cancelled()

        audio_wav = audio_artifacts["audio"]
        ref_wav = audio_artifacts["ref"]

        # Stage 2: transcribe
        _start_stage(manifest, "transcribe")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.transcribe import TranscribeError, run as transcribe_run

        try:
            segments = transcribe_run(source, audio_wav, run_dir, cfg)
        except TranscribeError as exc:
            _record_stage(manifest, "transcribe", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]transcribe failed:[/] {exc}")
            return ExitCode.STAGE_FAILED
        _record_stage(manifest, "transcribe", ok=True, artifacts=[run_dir / "segments.json"])
        _emit_event(opts, event="stage_done", stage="transcribe", segment_count=len(segments))
        _check_cancelled()

        # Stage 3: translate
        _start_stage(manifest, "translate")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.translate import TranslateError, run as translate_run

        try:
            translations_by_lang = translate_run(segments, targets, run_dir, cfg)
        except TranslateError as exc:
            _record_stage(manifest, "translate", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]translate failed:[/] {exc}")
            return ExitCode.STAGE_FAILED
        _record_stage(
            manifest,
            "translate",
            ok=True,
            artifacts=[run_dir / "translations" / f"{lang}.json" for lang in targets],
        )
        _emit_event(opts, event="stage_done", stage="translate")
        _check_cancelled()

        # Stage 4: tts
        _start_stage(manifest, "tts")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.tts import TtsError, run as tts_run

        try:
            tts_paths_by_lang = tts_run(segments, translations_by_lang, ref_wav, run_dir, cfg)
        except TtsError as exc:
            _record_stage(manifest, "tts", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]tts failed:[/] {exc}")
            return ExitCode.STAGE_FAILED
        _record_stage(manifest, "tts", ok=True)
        _emit_event(opts, event="stage_done", stage="tts")
        _check_cancelled()

        # Stage 5: build
        _start_stage(manifest, "build")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.build import BuildError, run as build_run

        try:
            tracks_by_lang, flagged_by_lang = build_run(
                segments, tts_paths_by_lang, audio_wav, run_dir, cfg
            )
        except BuildError as exc:
            _record_stage(manifest, "build", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]build failed:[/] {exc}")
            return ExitCode.STAGE_FAILED
        for lang, ids in flagged_by_lang.items():
            if ids:
                manifest.notes.append(
                    f"build: {len(ids)} flagged segments for {lang}: {ids[:10]}{'...' if len(ids) > 10 else ''}"
                )
        _record_stage(manifest, "build", ok=True, artifacts=list(tracks_by_lang.values()))
        _emit_event(opts, event="stage_done", stage="build")
        _check_cancelled()

        # Stage 6: mux
        _start_stage(manifest, "mux")
        _save_manifest(run_dir, manifest)
        from saddleback.stages.mux import MuxError, run as mux_run

        try:
            outputs = mux_run(source, tracks_by_lang, cfg)
        except MuxError as exc:
            _record_stage(manifest, "mux", ok=False, detail=str(exc))
            _save_manifest(run_dir, manifest)
            console.print(f"[red]mux failed:[/] {exc}")
            return ExitCode.STAGE_FAILED
        _record_stage(manifest, "mux", ok=True, artifacts=list(outputs.values()))
        _emit_event(opts, event="stage_done", stage="mux")

        # Optional: audio-only export next to source.
        audio_outputs: dict[str, Path] = {}
        if cfg.output.audio_export:
            _start_stage(manifest, "audio_export")
            _save_manifest(run_dir, manifest)
            from saddleback.stages.audio_export import AudioExportError, run as audio_export_run

            try:
                audio_outputs = audio_export_run(
                    source=source,
                    synced_tracks_by_lang=tracks_by_lang,
                    fmt=cfg.output.audio_export,
                    cfg=cfg,
                )
            except AudioExportError as exc:
                _record_stage(manifest, "audio_export", ok=False, detail=str(exc))
                _save_manifest(run_dir, manifest)
                console.print(f"[red]audio_export failed:[/] {exc}")
                return ExitCode.STAGE_FAILED
            _record_stage(
                manifest,
                "audio_export",
                ok=True,
                artifacts=list(audio_outputs.values()),
            )
            _emit_event(
                opts,
                event="stage_done",
                stage="audio_export",
                format=cfg.output.audio_export,
                outputs=[str(p) for p in audio_outputs.values()],
            )

        # Quality report
        _start_stage(manifest, "report")
        from saddleback.report import build_report

        report = build_report(
            run_dir=run_dir,
            segments=segments,
            outputs=outputs,
            flagged_by_lang=flagged_by_lang,
            cfg=cfg,
        )
        write_json(run_dir / "report.json", report)
        _record_stage(manifest, "report", ok=True, artifacts=[run_dir / "report.json"])
        _emit_event(opts, event="stage_done", stage="report")

        elapsed = time.monotonic() - started
        manifest.notes.append(f"completed in {elapsed:.1f}s")
        _save_manifest(run_dir, manifest)

        _print_summary(console, run_dir, segments, outputs, audio_outputs, flagged_by_lang, elapsed)
        _emit_event(opts, event="run_done", run_id=run_dir.name, elapsed_s=round(elapsed, 2))
        return ExitCode.OK

    except KeyboardInterrupt:
        manifest.notes.append("cancelled by user (SIGINT)")
        _save_manifest(run_dir, manifest)
        _emit_event(opts, event="run_cancelled", run_id=run_dir.name)
        console.print("[yellow]cancelled[/] — partial progress preserved; rerun to resume")
        return ExitCode.SIGINT
    except Exception as exc:  # noqa: BLE001
        manifest.notes.append(f"unexpected error: {exc!r}")
        _save_manifest(run_dir, manifest)
        console.print(f"[red]unexpected error:[/] {exc}")
        return ExitCode.GENERIC_FAILURE


def _print_summary(
    console: Console,
    run_dir: Path,
    segments: list[Segment],
    outputs: dict[str, Path],
    audio_outputs: dict[str, Path],
    flagged_by_lang: dict[str, list[int]],
    elapsed: float,
) -> None:
    table = Table(title=f"saddleback dub — {run_dir.name}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("segments", str(len(segments)))
    table.add_row("elapsed", f"{elapsed:.1f}s")
    for lang, path in outputs.items():
        flagged_count = len(flagged_by_lang.get(lang, []))
        table.add_row(f"{lang} output", str(path))
        table.add_row(f"{lang} flagged segments", str(flagged_count))
    for lang, path in audio_outputs.items():
        table.add_row(f"{lang} audio export", str(path))
    console.print(table)


# ---------------------------------------------------------------------------
# regen
# ---------------------------------------------------------------------------


def run_regen(
    segment_id: int,
    targets: list[str],
    shorter: bool,
    run_id: str | None,
    opts: dict[str, Any],
) -> ExitCode:
    cfg = load_config(explicit_path=opts.get("config_path"))
    cfg = _apply_runtime_overrides(cfg, opts)
    console = _console(opts)
    runs_root = cfg.runtime.runs_dir.resolve()
    run_dir = find_run_dir(runs_root, run_id)
    if run_dir is None:
        console.print("[red]no run found[/] — pass --run-id or run `saddleback dub` first")
        return ExitCode.BAD_USAGE

    manifest = Manifest.model_validate(read_json(run_dir / "manifest.json"))
    source = Path(manifest.source_path)
    if not source.exists():
        console.print(f"[red]source missing[/]: {source}")
        return ExitCode.SOURCE_UNUSABLE

    segments = [Segment.model_validate(s) for s in read_json(run_dir / "segments.json")]
    seg_by_id = {s.id: s for s in segments}
    if segment_id not in seg_by_id:
        console.print(f"[red]segment {segment_id} not found[/] in {len(segments)} total")
        return ExitCode.BAD_USAGE
    segment = seg_by_id[segment_id]

    audio_wav = run_dir / "audio.wav"
    ref_wav = run_dir / "ref.wav"

    from saddleback.stages.translate import TranslateError, regen_one as translate_regen
    from saddleback.stages.tts import regen_one as tts_regen
    from saddleback.stages.build import rebuild_one
    from saddleback.stages.mux import remux_one

    final_outputs: dict[str, Path] = {}
    for lang in targets:
        try:
            new_translation = translate_regen(segment, lang, run_dir, cfg, shorter=shorter)
        except TranslateError as exc:
            console.print(f"[red]translate regen failed ({lang}):[/] {exc}")
            return ExitCode.STAGE_FAILED

        # Reload all translations to pass to TTS regen.
        translations = [
            Translation.model_validate(t)
            for t in read_json(run_dir / "translations" / f"{lang}.json")
        ]
        per_seg_paths: dict[int, Path] = {}
        for t in translations:
            per_seg_paths[t.segment_id] = run_dir / "tts" / lang / f"seg_{t.segment_id:04d}.wav"

        # Regenerate just this segment's TTS clip.
        new_clip = tts_regen(segment, new_translation, lang, ref_wav, run_dir, cfg)
        per_seg_paths[segment_id] = new_clip

        tts_paths_by_lang = {lang: per_seg_paths}
        track_path, flagged_ids = rebuild_one(
            segments=segments,
            tts_paths_by_lang=tts_paths_by_lang,
            audio_wav=audio_wav,
            run_dir=run_dir,
            cfg=cfg,
            lang=lang,
            segment_id=segment_id,
        )
        out = remux_one(source=source, synced_audio=track_path, lang=lang, cfg=cfg)
        final_outputs[lang] = out

        # Refresh audio export if enabled so the .wav/.m4a/.mp3 stays in sync.
        if cfg.output.audio_export:
            from saddleback.stages.audio_export import AudioExportError, export_one

            try:
                audio_out = export_one(
                    synced_wav=track_path,
                    source=source,
                    lang=lang,
                    fmt=cfg.output.audio_export,
                    cfg=cfg,
                )
                console.print(f"[green]{lang}[/]: audio export refreshed → {audio_out}")
            except AudioExportError as exc:
                console.print(f"[yellow]{lang} audio export skipped:[/] {exc}")

        manifest.notes.append(
            f"regen segment {segment_id} ({lang}): shorter={shorter}, "
            f"flagged={'yes' if segment_id in flagged_ids else 'no'}"
        )

    _save_manifest(run_dir, manifest)
    for lang, path in final_outputs.items():
        console.print(f"[green]{lang}[/]: regenerated → {path}")
    return ExitCode.OK


# ---------------------------------------------------------------------------
# play / status / clean
# ---------------------------------------------------------------------------


def play_segment(
    segment_id: int,
    lang: str,
    run_id: str | None,
    opts: dict[str, Any],
) -> ExitCode:
    cfg = load_config(explicit_path=opts.get("config_path"))
    cfg = _apply_runtime_overrides(cfg, opts)
    console = _console(opts)
    runs_root = cfg.runtime.runs_dir.resolve()
    run_dir = find_run_dir(runs_root, run_id)
    if run_dir is None:
        console.print("[red]no run found[/]")
        return ExitCode.BAD_USAGE

    clip = run_dir / "fitted" / lang / f"seg_{segment_id:04d}.wav"
    if not clip.exists():
        clip = run_dir / "tts" / lang / f"seg_{segment_id:04d}.wav"
    if not clip.exists():
        console.print(f"[red]clip not found[/]: segment {segment_id} ({lang})")
        return ExitCode.BAD_USAGE

    if sys.platform != "darwin":
        console.print(f"[yellow]play[/]: not on macOS; clip is at {clip}")
        return ExitCode.OK

    res = subprocess.run(["afplay", str(clip)])
    return ExitCode.OK if res.returncode == 0 else ExitCode.GENERIC_FAILURE


def run_status(run_id: str | None, opts: dict[str, Any]) -> ExitCode:
    cfg = load_config(explicit_path=opts.get("config_path"))
    console = _console(opts)
    runs_root = cfg.runtime.runs_dir.resolve()
    run_dir = find_run_dir(runs_root, run_id)
    if run_dir is None:
        console.print("[red]no run found[/]")
        return ExitCode.BAD_USAGE

    manifest = Manifest.model_validate(read_json(run_dir / "manifest.json"))
    table = Table(title=f"status — {manifest.run_id}")
    table.add_column("stage")
    table.add_column("status")
    table.add_column("started")
    table.add_column("finished")
    for name in ("extract", "transcribe", "translate", "tts", "build", "mux", "report"):
        s = manifest.stages.get(name)
        if s is None:
            table.add_row(name, "[grey]pending[/]", "", "")
        elif s.ok is None:
            table.add_row(name, "[yellow]running[/]", s.started_at or "", "")
        elif s.ok:
            table.add_row(name, "[green]ok[/]", s.started_at or "", s.finished_at or "")
        else:
            table.add_row(name, f"[red]fail[/] {s.detail}", s.started_at or "", s.finished_at or "")
    console.print(table)
    return ExitCode.OK


def run_clean(run_id: str | None, keep_outputs: bool, opts: dict[str, Any]) -> ExitCode:
    import shutil

    cfg = load_config(explicit_path=opts.get("config_path"))
    console = _console(opts)
    runs_root = cfg.runtime.runs_dir.resolve()
    run_dir = find_run_dir(runs_root, run_id)
    if run_dir is None:
        console.print("[red]no run found[/]")
        return ExitCode.BAD_USAGE

    intermediates = ["audio.wav", "ref.wav", "segments.json", "translations", "tts", "fitted", "synced"]
    removed: list[str] = []
    for name in intermediates:
        p = run_dir / name
        if p.is_file():
            p.unlink()
            removed.append(str(p))
        elif p.is_dir():
            shutil.rmtree(p)
            removed.append(str(p))
    console.print(f"[green]cleaned[/] {len(removed)} entries from {run_dir}")
    if keep_outputs:
        console.print("[dim]final dubbed MP4s left in place next to source[/]")
    return ExitCode.OK


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _apply_runtime_overrides(cfg: Config, opts: dict[str, Any]) -> Config:
    """Translate CLI flags into config overrides where applicable."""
    if opts.get("test_mode") or os.environ.get("SADDLEBACK_RUNTIME_TEST_MODE", "").lower() == "true":
        cfg = cfg.model_copy(update={"runtime": cfg.runtime.model_copy(update={"test_mode": True})})
    audio_export = opts.get("audio_export")
    if audio_export:
        cfg = cfg.model_copy(
            update={"output": cfg.output.model_copy(update={"audio_export": audio_export})}
        )
    return cfg
