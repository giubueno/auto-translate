from __future__ import annotations

from pathlib import Path

from saddleback.config import Config
from saddleback.stages import translate
from saddleback.types import Segment


def test_test_mode_produces_deterministic_output(tmp_path: Path):
    cfg = Config()
    cfg = cfg.model_copy(update={"runtime": cfg.runtime.model_copy(update={"test_mode": True})})

    segments = [
        Segment(id=0, start=0.0, end=2.0, text="Hello there."),
        Segment(id=1, start=2.0, end=4.0, text="This is a test."),
    ]
    targets = ["de", "es"]
    out = translate.run(segments, targets, tmp_path, cfg)

    assert set(out) == {"de", "es"}
    de = out["de"]
    assert len(de) == 2
    assert de[0].text == "[de] Hello there."
    assert de[0].overflow is False
    assert (tmp_path / "translations" / "de.json").exists()
    assert (tmp_path / "translations" / "es.json").exists()


def test_word_budget_proportional_to_source():
    seg = Segment(id=0, start=0.0, end=2.0, text="five word source segment here please")
    budget_low = translate._word_budget(seg, ratio=1.0)
    budget_high = translate._word_budget(seg, ratio=1.5)
    assert budget_low == 6
    assert budget_high == 9
