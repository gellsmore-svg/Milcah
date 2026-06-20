from types import SimpleNamespace

from milcah.challenge import Challenge
from milcah.ingestion import ingest_text
from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.rounds import run_rounds


def _fw_units():
    fw = ingest_text("Matter is topological.", title="t")
    units = [ReasoningUnit.make(framework_id=fw.id, unit_type=RT.CLAIM, text="Matter is topological.")]
    return fw, units


def _obj(fw_id, text):
    return ReasoningUnit.make(framework_id=fw_id, unit_type=RT.CLAIM, text=text)


def test_rounds_converge_when_nothing_new():
    fw, units = _fw_units()
    rep = run_rounds(
        fw, units,
        reason=lambda o, b: SimpleNamespace(generated=0),
        challenge=lambda f, o: Challenge(framework_id=f.id),
        max_rounds=5,
    )
    assert rep.stop_reason == "converged"
    assert len(rep.rounds) == 1


def test_rounds_stop_on_repeated_objections():
    fw, units = _fw_units()

    def challenge(f, o):
        return Challenge(framework_id=f.id, objections=[_obj(f.id, "the same objection")])

    rep = run_rounds(
        fw, units,
        reason=lambda o, b: SimpleNamespace(generated=2),
        challenge=challenge, max_rounds=5, node_budget=100,
    )
    assert rep.stop_reason == "repeated_objections"
    assert len(rep.rounds) == 2  # round 1 records it, round 2 detects the repeat


def test_rounds_stop_at_max_rounds():
    fw, units = _fw_units()
    counter = {"n": 0}

    def challenge(f, o):
        counter["n"] += 1
        return Challenge(framework_id=f.id, objections=[_obj(f.id, f"objection {counter['n']}")])

    rep = run_rounds(
        fw, units,
        reason=lambda o, b: SimpleNamespace(generated=1),
        challenge=challenge, max_rounds=3, node_budget=100,
    )
    assert rep.stop_reason == "max_rounds"
    assert len(rep.rounds) == 3


def test_rounds_stop_on_node_budget():
    fw, units = _fw_units()
    rep = run_rounds(
        fw, units,
        reason=lambda o, b: SimpleNamespace(generated=b),  # consume the whole budget
        challenge=lambda f, o: Challenge(framework_id=f.id, objections=[_obj(f.id, "x")]),
        max_rounds=10, node_budget=5, per_round_nodes=5,
    )
    assert rep.stop_reason == "node_budget"
    assert len(rep.rounds) == 1
    assert sum(r.new_nodes for r in rep.rounds) == 5
