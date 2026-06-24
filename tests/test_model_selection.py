"""Tests for diverse per-role model selection (ADR-001). All offline (pure)."""

from milcah.model_selection import (
    ROLE_ORDER,
    assign_diverse_models,
    filter_reasoning_models,
    make_hoglah_model_lister,
)


def test_filter_reasoning_models_drops_embedders():
    avail = ["gemma4:latest", "bge-m3:latest", "nomic-embed-text:latest", "qwen3.6:latest"]
    assert filter_reasoning_models(avail) == ["gemma4:latest", "qwen3.6:latest"]


def test_model_lister_is_submitter_only(monkeypatch):
    created = []

    class FakeHoglah:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def available_models(self):
            return ["m1"]

        def close(self):
            pass

    import types, sys
    monkeypatch.setitem(sys.modules, "hoglah", types.SimpleNamespace(Hoglah=FakeHoglah))
    assert make_hoglah_model_lister()() == ["m1"]
    assert created == [{"use_real": True, "config": None, "start_worker": False}]


def test_assigns_distinct_models_to_every_role_when_enough_available():
    out = assign_diverse_models(
        ROLE_ORDER, ["m1", "m2", "m3", "m4", "m5"], pinned={}, default="d"
    )
    assert set(out) == set(ROLE_ORDER)
    assert len(set(out.values())) == 4  # all distinct
    assert "d" not in out.values()      # default not needed


def test_honours_pinned_and_auto_picks_never_collide_with_them():
    out = assign_diverse_models(
        ROLE_ORDER, ["m1", "m2", "m3"], pinned={"proposer": "m2"}, default="d"
    )
    assert out["proposer"] == "m2"                 # pinned kept verbatim
    assert "m2" not in [out["challenger"], out["fallacy"], out["synthesis"]]
    assert len(set(out.values())) == 4             # still all distinct


def test_falls_back_to_default_when_too_few_models():
    out = assign_diverse_models(ROLE_ORDER, ["m1"], pinned={}, default="d")
    assert out["proposer"] == "m1"                 # the one real model, in order
    assert out["challenger"] == "d"                # pool exhausted -> default
    assert out["fallacy"] == "d"
    assert out["synthesis"] == "d"


def test_empty_available_degrades_to_all_default():
    out = assign_diverse_models(ROLE_ORDER, [], pinned={}, default="d")
    assert out == {r: "d" for r in ROLE_ORDER}


def test_all_pinned_ignores_available():
    pinned = {r: f"p-{r}" for r in ROLE_ORDER}
    out = assign_diverse_models(ROLE_ORDER, ["m1", "m2"], pinned=pinned, default="d")
    assert out == pinned


def test_dedupes_and_skips_pinned_values_in_available_pool():
    # available has dups and includes the pinned model; auto picks must be clean.
    out = assign_diverse_models(
        ROLE_ORDER, ["m1", "m1", "m2", "m3"], pinned={"synthesis": "m1"}, default="d"
    )
    autos = [out["proposer"], out["challenger"], out["fallacy"]]
    assert out["synthesis"] == "m1"
    assert "m1" not in autos                        # pinned value excluded from pool
    assert autos == ["m2", "m3", "d"]               # m1 deduped+excluded, then exhausted
