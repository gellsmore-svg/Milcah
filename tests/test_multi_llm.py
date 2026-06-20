from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.multi_llm import MultiLLMExtractor, reconcile_extractions, reconcile_semantic


def _u(fid, t, text):
    return ReasoningUnit.make(framework_id=fid, unit_type=t, text=text)


def test_reconcile_agreement_consensus_and_majority_type():
    fid = "f1"
    m1 = [_u(fid, RT.OBSERVATION, "Particles persist."), _u(fid, RT.ASSUMPTION, "Identity is topological.")]
    m2 = [_u(fid, RT.OBSERVATION, "particles persist"), _u(fid, RT.CLAIM, "Identity is topological.")]
    m3 = [_u(fid, RT.OBSERVATION, "Particles persist.")]

    out = reconcile_extractions({"a": m1, "b": m2, "c": m3}, total_models=3)

    # "Particles persist." extracted by all three (normalised match) -> full agreement
    persist = next(u for u in out if "persist" in u.text.lower())
    assert persist.metadata["agreement"] == 3
    assert persist.metadata["consensus"] == 1.0
    assert persist.metadata["models"] == ["a", "b", "c"]
    assert persist.type == RT.OBSERVATION  # unanimous type

    # "Identity is topological." by a (assumption) + b (claim): agreement 2, type disagreement surfaced
    ident = next(u for u in out if "identity" in u.text.lower())
    assert ident.metadata["agreement"] == 2
    assert ident.metadata["type_votes"] == {"assumption": 1, "claim": 1}
    assert ident.type == RT.ASSUMPTION  # majority/first-seen tie-break, deterministic
    assert ident.markers == ["multi-llm"]

    # sorted by agreement, descending
    assert [u.metadata["agreement"] for u in out] == sorted(
        (u.metadata["agreement"] for u in out), reverse=True
    )


def test_reconcile_within_model_dedup():
    fid = "f2"
    # a model repeating the same text must not inflate agreement to 2
    m1 = [_u(fid, RT.CLAIM, "X holds."), _u(fid, RT.CLAIM, "x holds")]
    out = reconcile_extractions({"only": m1})
    assert len(out) == 1
    assert out[0].metadata["agreement"] == 1


def test_multi_llm_extractor_runs_each_model_then_reconciles():
    fw = ingest_text("body text", title="t")
    seen: list[str] = []

    def fake(framework, model):
        seen.append(model)
        units = [ReasoningUnit.make(framework_id=framework.id, unit_type=RT.CLAIM, text="shared claim")]
        if model == "m2":
            units.append(ReasoningUnit.make(framework_id=framework.id, unit_type=RT.OBSERVATION, text="only m2"))
        return units

    out = MultiLLMExtractor(["m1", "m2"], extract_with=fake).extract(fw)
    assert seen == ["m1", "m2"]
    shared = next(u for u in out if u.text == "shared claim")
    assert shared.metadata["agreement"] == 2 and shared.metadata["models"] == ["m1", "m2"]
    only = next(u for u in out if u.text == "only m2")
    assert only.metadata["agreement"] == 1
    assert out[0].text == "shared claim"  # highest agreement first


def test_multi_llm_dedups_model_list_and_requires_one():
    import pytest

    ext = MultiLLMExtractor(["m1", "m1", "m2"], extract_with=lambda f, m: [])
    assert ext.models == ["m1", "m2"]
    with pytest.raises(ValueError):
        MultiLLMExtractor([], extract_with=lambda f, m: [])


def test_multi_llm_tolerates_a_failing_model():
    fw = ingest_text("body", title="t")

    def flaky(framework, model):
        if model == "slow":
            raise TimeoutError("model too slow on this hardware")
        return [ReasoningUnit.make(framework_id=framework.id, unit_type=RT.CLAIM, text="kept")]

    # one model fails -> skipped, the rest still reconcile; consensus over survivors
    out = MultiLLMExtractor(["ok", "slow"], extract_with=flaky).extract(fw)
    assert [u.text for u in out] == ["kept"]
    assert out[0].metadata["agreement"] == 1 and out[0].metadata["consensus"] == 1.0
    assert out[0].metadata["models"] == ["ok"]


def test_multi_llm_raises_only_if_all_models_fail():
    import pytest

    fw = ingest_text("body", title="t")

    def boom(framework, model):
        raise RuntimeError("down")

    with pytest.raises(RuntimeError, match="all 2 model"):
        MultiLLMExtractor(["a", "b"], extract_with=boom).extract(fw)


def test_reconcile_semantic_merges_phrasing_variants():
    fid = "f"
    m1 = [_u(fid, RT.PRIMITIVE, "a vorton is a knotted configuration")]
    m2 = [_u(fid, RT.PRIMITIVE, "vorton is a knotted configuration")]  # phrasing variant
    m3 = [_u(fid, RT.OBSERVATION, "particles persist over time")]

    def embed(text):  # vorton texts cluster together; particles is orthogonal
        return [1.0, 0.0] if "vorton" in text else [0.0, 1.0]

    out = reconcile_semantic({"a": m1, "b": m2, "c": m3}, embed=embed, threshold=0.9, total_models=3)

    vorton = next(u for u in out if "vorton" in u.text.lower())
    assert vorton.metadata["agreement"] == 2  # merged despite different wording
    assert vorton.metadata["models"] == ["a", "b"]
    assert "semantic" in vorton.markers
    assert vorton.text == "a vorton is a knotted configuration"  # most frequent / longest rep
    # the same input under exact-text reconciliation would NOT merge them:
    assert max(u.metadata["agreement"] for u in reconcile_extractions({"a": m1, "b": m2, "c": m3})) == 1


def test_reconcile_semantic_embed_failure_is_singleton():
    fid = "f"
    units = [_u(fid, RT.CLAIM, "x"), _u(fid, RT.CLAIM, "y")]
    out = reconcile_semantic({"a": units}, embed=lambda t: [], threshold=0.5)
    assert len(out) == 2  # no embeddings -> nothing merges


def test_multi_llm_semantic_mode_uses_injected_embed():
    fw = ingest_text("body", title="t")

    def fake(framework, model):
        text = "a claim" if model == "m1" else "claim"
        return [ReasoningUnit.make(framework_id=framework.id, unit_type=RT.CLAIM, text=text)]

    out = MultiLLMExtractor(
        ["m1", "m2"], reconcile="semantic", embed=lambda t: [1.0, 0.0], extract_with=fake
    ).extract(fw)
    assert len(out) == 1 and out[0].metadata["agreement"] == 2


def test_multi_llm_rejects_bad_reconcile_mode():
    import pytest

    with pytest.raises(ValueError, match="reconcile"):
        MultiLLMExtractor(["m"], reconcile="telepathy", extract_with=lambda f, m: [])
