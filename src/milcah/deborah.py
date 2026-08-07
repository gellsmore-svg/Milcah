"""Deborah estate adapters — Milcah as a framed CALL capability.

Deborah's thin interpreter dispatches CALL steps through injectable handlers.
This module turns :func:`milcah.specialist.run_specialist` into a Deborah-shaped
handler that returns an **evaluate** cognition product (criteria, scores,
objections, confidence bands).

Deborah does **not** hard-depend on Milcah; harnesses import this module when
both packages are installed.
"""

from __future__ import annotations

from typing import Any, Callable

from milcah.specialist import SpecialistConfig, run_specialist

CapabilityDispatch = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def confidence_band(value: float) -> str:
    """Map specialist confidence [0,1] to Deborah confidence bands."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "unassessed"
    if v >= 0.7:
        return "high"
    if v >= 0.4:
        return "medium"
    if v > 0:
        return "low"
    return "unassessed"


def specialist_to_evaluate(result: Any) -> dict[str, Any]:
    """Map a :class:`~milcah.contract.SpecialistResult` to COGNITION evaluate product."""
    get = (
        (lambda k, d=None: result.get(k, d))
        if isinstance(result, dict)
        else (lambda k, d=None: getattr(result, k, d))
    )
    objections = list(get("objections") or [])
    claims = list(get("claims") or [])
    evidence = list(get("evidence") or [])
    citations = list(get("citations") or [])
    conf = float(get("confidence") or 0.0)
    band = confidence_band(conf)
    terminal = str(get("terminal_reason") or "")
    # Adversarial resilience drops when objections exist or run was thin.
    adv = "low" if objections or terminal in {"blocked", "insufficient_evidence"} else band
    ranking = (
        ["open", "revise", "accept"]
        if objections or terminal in {"blocked", "insufficient_evidence", "no_objections"}
        else ["accept", "open", "revise"]
    )
    return {
        "criteria": ["groundedness", "internal_consistency", "adversarial_resilience"],
        "scores": {
            "groundedness": band if evidence or claims else "low",
            "internal_consistency": band,
            "adversarial_resilience": adv,
        },
        "ranking": ranking,
        "objections": objections,
        "claims": claims,
        "evidence": evidence,
        "citations": citations,
        "terminal_reason": terminal,
        "confidence": {
            "evidence": band if evidence or claims else "low",
            "inference": band,
            "execution": "high" if terminal not in {"blocked"} else "low",
            "basis": f"milcah.specialist ({terminal or 'unknown'})",
        },
    }


def make_critique_handler(
    *,
    config: SpecialistConfig | None = None,
    run_fn: Callable[..., Any] | None = None,
    max_iterations: int = 2,
) -> CapabilityDispatch:
    """Build a Deborah EstateHandler dispatch callable for ``milcah.critique``.

    Parameters
    ----------
    config:
        Optional :class:`SpecialistConfig` (e.g. rule extractor for offline tests).
    run_fn:
        Injectable specialist runner (defaults to :func:`run_specialist`).
    max_iterations:
        Bound for the specialist call when context does not supply one.
    """
    runner = run_fn or run_specialist
    cfg = config

    def handler(step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        claim = (
            context.get("claim")
            or context.get("request")
            or step.get("action")
            or step.get("purpose")
            or "Pressure-test the claim."
        )
        claim = str(claim).strip()
        # Prefer prior infer step artifacts as context for the specialist.
        artifacts = context.get("artifacts") or {}
        prior_bits: list[str] = []
        for val in artifacts.values():
            if isinstance(val, dict):
                if val.get("claim_restatement"):
                    prior_bits.append(str(val["claim_restatement"]))
                elif val.get("statement"):
                    prior_bits.append(str(val["statement"]))
                elif val.get("evidence"):
                    for e in val["evidence"] if isinstance(val["evidence"], list) else []:
                        if isinstance(e, dict) and e.get("statement"):
                            prior_bits.append(str(e["statement"]))
                        elif isinstance(e, str):
                            prior_bits.append(e)
            elif isinstance(val, str) and val.strip():
                prior_bits.append(val.strip())
        framework_ctx = "\n".join(prior_bits)[:6000] if prior_bits else str(claim)[:6000]
        iters = int(context.get("max_iterations") or max_iterations)
        request = {
            "query": claim if claim else "Is this framework coherent?",
            "mode": str(context.get("mode") or "coherence"),
            "context": framework_ctx,
            "max_iterations": max(0, iters),
            "trace_id": context.get("trace_id"),
            "session_id": context.get("session_id"),
        }
        try:
            result = runner(request, config=cfg) if cfg is not None else runner(request)
        except Exception as exc:  # boundary: never raise into Deborah runtime
            return {
                "status": "blocked",
                "reason": f"milcah.critique failed: {type(exc).__name__}: {exc}",
                "residual": True,
            }

        get = (
            (lambda k, d=None: result.get(k, d))
            if isinstance(result, dict)
            else (lambda k, d=None: getattr(result, k, d))
        )
        terminal = str(get("terminal_reason") or "")
        if terminal == "blocked":
            errors = (get("trace_metadata") or {}).get("validation_errors") if isinstance(
                get("trace_metadata"), dict
            ) else None
            return {
                "status": "blocked",
                "reason": f"milcah specialist blocked: {errors or terminal}",
                "residual": True,
                "result": specialist_to_evaluate(result),
            }

        return {
            "status": "completed",
            "result": specialist_to_evaluate(result),
        }

    return handler


def critique_handler(step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Default critique handler (rule-based extractor, no Hoglah required)."""
    return make_critique_handler(config=SpecialistConfig(extractor="rule"))(step, context)


def _prior_evaluate(context: dict[str, Any]) -> dict[str, Any] | None:
    for val in (context.get("artifacts") or {}).values():
        if isinstance(val, dict) and (
            val.get("criteria") or val.get("objections") is not None or val.get("scores")
        ):
            return val
    return None


def _prior_infer(context: dict[str, Any]) -> dict[str, Any] | None:
    for val in (context.get("artifacts") or {}).values():
        if isinstance(val, dict) and (val.get("claim") or val.get("evidence_refs") is not None):
            if "criteria" not in val:  # not an evaluate product
                return val
    return None


def make_validate_against_intent_handler(
    *,
    config: SpecialistConfig | None = None,
    run_fn: Callable[..., Any] | None = None,
) -> CapabilityDispatch:
    """Check provisional reading / critique against declared intent + outcomes.

    Reuses critique when no prior evaluate artifact; always scores intent_alignment.
    """
    critique = make_critique_handler(config=config, run_fn=run_fn)

    def handler(step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        intent = str(
            context.get("intent")
            or (context.get("plan") or {}).get("intent")
            or context.get("claim")
            or context.get("request")
            or ""
        ).strip()
        outcomes = context.get("outcomes") or (context.get("plan") or {}).get("outcomes") or []
        if isinstance(outcomes, str):
            outcomes = [outcomes]

        prior = _prior_evaluate(context)
        if prior is None:
            out = critique(step, context)
            prior = out.get("result") if isinstance(out, dict) else None
            if not isinstance(prior, dict):
                prior = {}

        objections = list(prior.get("objections") or [])
        infer = _prior_infer(context) or {}
        claim_text = str(infer.get("claim") or infer.get("claim_original") or context.get("claim") or "")

        # Heuristic alignment: intent keywords appear in claim restatement / objections empty
        intent_tokens = {t.lower() for t in intent.replace(",", " ").split() if len(t) > 3}
        claim_tokens = {t.lower() for t in claim_text.replace(",", " ").split() if len(t) > 3}
        overlap = len(intent_tokens & claim_tokens) if intent_tokens else 0
        if not intent:
            align = "unassessed"
            objections = objections + ["no intent declared for alignment check"]
        elif objections:
            align = "low"
        elif overlap >= 2 or (intent_tokens and intent_tokens <= claim_tokens):
            align = "high"
        elif overlap >= 1:
            align = "medium"
        else:
            align = "low"
            objections = objections + ["provisional reading may drift from declared intent"]

        scores = dict(prior.get("scores") or {})
        scores["intent_alignment"] = align
        criteria = list(prior.get("criteria") or [])
        if "intent_alignment" not in criteria:
            criteria = [*criteria, "intent_alignment"]

        product = {
            **prior,
            "criteria": criteria,
            "scores": scores,
            "objections": objections,
            "intent": intent,
            "outcomes_checked": [str(o) for o in outcomes] if isinstance(outcomes, list) else [],
            "confidence": {
                **(prior.get("confidence") or {}),
                "inference": align if align != "unassessed" else "low",
                "basis": "milcah.validate_against_intent",
            },
        }
        residual = align in {"low", "unassessed"} or bool(objections)
        return {
            "status": "completed",
            "result": product,
            "residual": residual,
            "reason": "intent alignment low" if residual else None,
        }

    return handler


def make_assess_confidence_handler() -> CapabilityDispatch:
    """Aggregate confidence bands from prior observe/infer/evaluate artifacts."""

    def handler(step: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        dims = {"evidence": [], "inference": [], "execution": []}
        sources: list[str] = []
        for sid, val in (context.get("artifacts") or {}).items():
            if not isinstance(val, dict):
                continue
            conf = val.get("confidence")
            if not isinstance(conf, dict):
                continue
            sources.append(str(sid))
            for d in dims:
                if conf.get(d):
                    dims[d].append(str(conf[d]).lower())

        rank = {"high": 3, "medium": 2, "low": 1, "unassessed": 0}

        def weakest(bands: list[str]) -> str:
            if not bands:
                return "unassessed"
            return min(bands, key=lambda b: rank.get(b, 0))

        evidence_b = weakest(dims["evidence"])
        inference_b = weakest(dims["inference"])
        execution_b = weakest(dims["execution"])

        floor_ok = rank.get(inference_b, 0) >= rank.get(
            str(context.get("confidence_floor") or "low").lower(), 1
        )
        product = {
            "criteria": ["confidence_floor", "evidence_band", "inference_band"],
            "scores": {
                "confidence_floor": "high" if floor_ok else "low",
                "evidence_band": evidence_b,
                "inference_band": inference_b,
            },
            "ranking": ["open", "revise", "accept"]
            if not floor_ok or inference_b == "low"
            else ["accept", "open", "revise"],
            "objections": (
                []
                if floor_ok
                else [f"inference confidence {inference_b!r} below floor"]
            ),
            "assessed_from_steps": sources,
            "confidence": {
                "evidence": evidence_b,
                "inference": inference_b,
                "execution": execution_b,
                "basis": "milcah.assess_confidence (aggregate prior steps)",
            },
        }
        return {
            "status": "completed",
            "result": product,
            "residual": not floor_ok,
        }

    return handler


def deborah_dispatch(
    *,
    config: SpecialistConfig | None = None,
    run_fn: Callable[..., Any] | None = None,
) -> dict[str, CapabilityDispatch]:
    """Map both bare and namespaced stems used in Deborah ASSUMES / CALL steps."""
    h = make_critique_handler(config=config, run_fn=run_fn)
    v = make_validate_against_intent_handler(config=config, run_fn=run_fn)
    a = make_assess_confidence_handler()
    return {
        "milcah.critique": h,
        "critique": h,
        "milcah.coherence_check": h,
        "coherence_check": h,
        "milcah.validate_against_intent": v,
        "validate_against_intent": v,
        "milcah.assess_confidence": a,
        "assess_confidence": a,
    }


def capability_index_entries() -> dict[str, dict[str, Any]]:
    """Metadata for Deborah :class:`DictCapabilityIndex` (no Keturah required)."""
    return {
        "milcah.critique": {
            "name": "milcah.critique",
            "product": "milcah",
            "kind": "tool",
            "alias_of": "coherence_check",
            "tags": ["critique", "evaluate", "specialist"],
            "negotiable": True,
        },
        "milcah.coherence_check": {
            "name": "milcah.coherence_check",
            "product": "milcah",
            "kind": "tool",
            "tags": ["specialist", "coherence"],
            "negotiable": True,
        },
        "milcah.validate_against_intent": {
            "name": "milcah.validate_against_intent",
            "product": "milcah",
            "kind": "tool",
            "tags": ["evaluate", "intent", "specialist"],
            "negotiable": True,
        },
        "milcah.assess_confidence": {
            "name": "milcah.assess_confidence",
            "product": "milcah",
            "kind": "tool",
            "tags": ["evaluate", "confidence", "specialist"],
        },
    }


def critique_negotiator(proposal: dict[str, Any], history: list, round_index: int) -> Any:
    """Capability-side content gate for milcah.critique.

    Prefers Deborah's shared implementation when installed; otherwise a local
    thin underspecified/out-of-scope check (no LLM).
    """
    try:
        from deborah.runtime.negotiate import (  # type: ignore[import-not-found]
            critique_content_negotiator,
        )

        return critique_content_negotiator(proposal, history, round_index)
    except ImportError:
        pass

    # Local fallback (no deborah): minimal shape check
    claim = str(proposal.get("claim") or proposal.get("intent") or "").strip()
    # Duck-type message
    from types import SimpleNamespace

    if len(claim) < 8:
        return SimpleNamespace(
            type="clarification_request",
            role="capability",
            payload={"need": "a single assertion to pressure-test", "failure_mode": "underspecified-claim"},
        )
    return SimpleNamespace(
        type="acceptance",
        role="capability",
        payload={"note": "milcah local negotiator accept", "assumes": proposal.get("assumes")},
    )
