import json

from milcah.models import ReasoningUnit, ReasoningUnitType as RT
from milcah.ontology import PlacementState as PS
from milcah.orchestration import (
    OrchestrationConfig,
    Role,
    orchestrate,
    to_jsonable,
)
from milcah.ingestion import ingest_text


def _framework_and_units():
    fw = ingest_text("Everyone knows the substrate is discrete. Therefore reality is layered.", title="T")
    units = [
        ReasoningUnit.make(framework_id=fw.id, unit_type=RT.CLAIM, text="the substrate is discrete"),
        ReasoningUnit.make(framework_id=fw.id, unit_type=RT.CONCLUSION, text="reality is layered"),
    ]
    return fw, units


def test_config_assigns_distinct_models_per_role():
    cfg = OrchestrationConfig(default_model="base", models={"proposer": "m_a", "challenger": "m_b"})
    assert cfg.model_for(Role.PROPOSER) == "m_a"
    assert cfg.model_for(Role.CHALLENGER) == "m_b"
    assert cfg.model_for(Role.FALLACY) == "base"  # falls back to default
    assert cfg.hoglah_config(Role.PROPOSER).model == "m_a"


def test_orchestrate_runs_all_roles_with_provenance():
    fw, units = _framework_and_units()
    cfg = OrchestrationConfig(default_model="base",
                              models={"proposer": "m_prop", "challenger": "m_chal", "fallacy": "m_fall"})

    # Inject the role seams (no Hoglah daemon needed).
    def expand(node, framework_id):
        return []  # proposer: no expansion in this test

    def challenge(prompt, model):
        assert model == "m_chal"
        return json.dumps({"objections": [{"type": "claim", "text": "that ignores X", "targets": "c"}],
                           "counter_frameworks": []})

    def analyse(prompt, model):
        assert model == "m_fall"
        # locate a contradiction on step 1 -> that node becomes a fracture
        return json.dumps({"findings": [{"fallacy": "contradiction", "step": 1, "explanation": "cannot hold"}]})

    result = orchestrate(fw, units, config=cfg, expand=expand, challenge=challenge, analyse=analyse)

    # all four roles ran, each with its assigned model (provenance, not confidence)
    assert result.roles == {"proposer": "m_prop", "challenger": "m_chal",
                            "fallacy": "m_fall", "synthesis": "base"}
    assert [t["role"] for t in result.trace] == ["proposer", "challenger", "fallacy", "synthesis"]

    # challenger produced an objection
    assert len(result.challenge.objections) == 1
    # fallacy located a contradiction -> the node is now a fracture
    assert len(result.fallacies.findings) == 1
    located = result.fallacies.findings[0].location_unit_id
    assert result.ontology.nodes[located].placement is PS.CONTRADICTORY_PLACEMENT
    assert result.metrics.fracture_density > 0  # disagreement/fallacy raised a fracture


def test_orchestrate_records_no_agreement_signal():
    fw, units = _framework_and_units()
    result = orchestrate(fw, units, config=OrchestrationConfig(),
                         expand=lambda n, f: [],
                         challenge=lambda p, m: "{}",
                         analyse=lambda p, m: "{}")
    blob = to_jsonable(result)
    # ADR-001: provenance only; never an agreement/consensus score in the output.
    flat = json.dumps(blob).lower()
    assert "agreement" not in flat and "consensus" not in flat
    assert set(blob["roles"]) == {"proposer", "challenger", "fallacy", "synthesis"}
