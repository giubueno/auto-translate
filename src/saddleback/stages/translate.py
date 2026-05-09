"""Stage 3: translate source segments to DE / ES via LM Studio.

FR10, FR11, FR12, FR13, FR14, FR15, FR16.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from saddleback.config import Config
from saddleback.types import Segment, Translation, write_json


class TranslateError(Exception):
    pass


_LANG_NAMES = {"de": "German", "es": "Spanish"}


def _system_prompt(target_name: str, max_words: int, shorter: bool = False) -> str:
    base = (
        f"Translate the user message into {target_name}. "
        f"Output ONLY the translation, no commentary, no quotes, no explanation. "
        f"Preserve proper nouns, product names, and technical acronyms unchanged. "
        f"Match the tone of the source (informal/professional). "
    )
    constraint = (
        f"Target length: at most {max_words} words. The {target_name} text MUST fit "
        f"within the source segment's spoken duration when read aloud at normal pace."
    )
    if shorter:
        constraint += " Be more concise than a literal translation; preserve meaning, drop filler."
    return base + constraint


def _word_budget(segment: Segment, ratio: float) -> int:
    source_words = max(1, len(segment.text.split()))
    return max(2, int(round(source_words * ratio)))


def reachability_check(cfg: Config) -> None:
    """Verify the translator endpoint is reachable. Raises TranslateError otherwise. (FR11)"""
    endpoint = cfg.translator.endpoint.rstrip("/")
    url = f"{endpoint}/models"
    try:
        req = Request(url, headers={"Authorization": f"Bearer {cfg.translator.api_key}"})
        with urlopen(req, timeout=5) as resp:
            if resp.status != 200:
                raise TranslateError(
                    f"GET {url} returned {resp.status}; LM Studio not healthy"
                )
            body = resp.read().decode("utf-8", errors="replace")
            if cfg.translator.model not in body:
                raise TranslateError(
                    f"endpoint reachable but model {cfg.translator.model!r} not loaded; "
                    f"verify in LM Studio"
                )
    except URLError as exc:
        raise TranslateError(
            f"GET {url} failed: {exc.reason}; verify LM Studio is running and reachable"
        ) from exc


async def _translate_one(
    client,
    segment: Segment,
    lang: str,
    cfg: Config,
    shorter: bool = False,
) -> Translation:
    max_words = _word_budget(segment, cfg.runtime.length_budget_ratio)
    target_name = _LANG_NAMES[lang]
    system = _system_prompt(target_name, max_words, shorter=shorter)

    attempt = 1
    while True:
        resp = await client.chat.completions.create(
            model=cfg.translator.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": segment.text},
            ],
            temperature=cfg.translator.temperature,
            timeout=cfg.translator.timeout_seconds,
        )
        text = (resp.choices[0].message.content or "").strip()
        text = text.strip("\"' \t\n")
        if not text:
            if attempt >= 2:
                raise TranslateError(
                    f"translator returned empty output for segment {segment.id} ({lang})"
                )
            attempt += 1
            continue

        words = len(text.split())
        overflow = words > max_words
        if overflow and not shorter and attempt < 2:
            attempt += 1
            shorter = True
            system = _system_prompt(target_name, max_words, shorter=True)
            continue

        return Translation(
            segment_id=segment.id,
            lang=lang,
            text=text,
            overflow=overflow,
            attempts=attempt,
        )


async def _translate_all(
    segments: list[Segment],
    lang: str,
    cfg: Config,
    existing: dict[int, Translation],
    shorter: bool = False,
) -> list[Translation]:
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise TranslateError("openai SDK not installed; pip install openai") from exc

    client = AsyncOpenAI(
        base_url=cfg.translator.endpoint,
        api_key=cfg.translator.api_key,
    )
    sem = asyncio.Semaphore(cfg.translator.max_concurrency)
    out: dict[int, Translation] = dict(existing)

    async def worker(seg: Segment) -> None:
        if seg.id in out and not shorter:
            return
        async with sem:
            t = await _translate_one(client, seg, lang, cfg, shorter=shorter)
            out[seg.id] = t

    await asyncio.gather(*(worker(s) for s in segments))
    return [out[s.id] for s in segments]


def run(
    segments: list[Segment],
    targets: list[str],
    run_dir: Path,
    cfg: Config,
) -> dict[str, list[Translation]]:
    """Run the translate stage. Returns translations per language. Resumable. (FR16)"""
    if cfg.runtime.test_mode:
        return _run_test_mode(segments, targets, run_dir)

    reachability_check(cfg)

    out_dir = run_dir / "translations"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[Translation]] = {}
    for lang in targets:
        if lang not in _LANG_NAMES:
            raise TranslateError(f"unsupported target language: {lang}")
        out_path = out_dir / f"{lang}.json"
        existing: dict[int, Translation] = {}
        if out_path.exists():
            for raw in json.loads(out_path.read_text(encoding="utf-8")):
                t = Translation.model_validate(raw)
                existing[t.segment_id] = t
        translations = asyncio.run(_translate_all(segments, lang, cfg, existing))
        write_json(out_path, [t.model_dump() for t in translations])
        result[lang] = translations
    return result


def regen_one(
    segment: Segment,
    lang: str,
    run_dir: Path,
    cfg: Config,
    shorter: bool = True,
) -> Translation:
    """Regenerate a single translation for one segment+lang. (FR14)"""
    if cfg.runtime.test_mode:
        return _fake_translation(segment, lang, prefix="[shorter]" if shorter else "[regen]")

    reachability_check(cfg)
    out_path = run_dir / "translations" / f"{lang}.json"
    existing: dict[int, Translation] = {}
    if out_path.exists():
        for raw in json.loads(out_path.read_text(encoding="utf-8")):
            t = Translation.model_validate(raw)
            existing[t.segment_id] = t

    async def _do() -> Translation:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=cfg.translator.endpoint,
            api_key=cfg.translator.api_key,
        )
        return await _translate_one(client, segment, lang, cfg, shorter=shorter)

    new_translation = asyncio.run(_do())
    existing[segment.id] = new_translation
    write_json(out_path, [existing[k].model_dump() for k in sorted(existing)])
    return new_translation


# ---- test mode helpers ----

_TEST_PREFIXES = {"de": "[de]", "es": "[es]"}


def _fake_translation(segment: Segment, lang: str, prefix: str = "") -> Translation:
    pfx = prefix or _TEST_PREFIXES.get(lang, "[??]")
    return Translation(
        segment_id=segment.id,
        lang=lang,
        text=f"{pfx} {segment.text}",
        overflow=False,
        attempts=1,
    )


def _run_test_mode(
    segments: list[Segment],
    targets: list[str],
    run_dir: Path,
) -> dict[str, list[Translation]]:
    out_dir = run_dir / "translations"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, list[Translation]] = {}
    for lang in targets:
        translations = [_fake_translation(s, lang) for s in segments]
        write_json(out_dir / f"{lang}.json", [t.model_dump() for t in translations])
        result[lang] = translations
    return result
