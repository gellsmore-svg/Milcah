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


def deborah_dispatch(
    *,
    config: SpecialistConfig | None = None,
    run_fn: Callable[..., Any] | None = None,
) -> dict[str, CapabilityDispatch]:
    """Map both bare and namespaced stems used in Deborah ASSUMES / CALL steps."""
    h = make_critique_handler(config=config, run_fn=run_fn)
    return {
        "milcah.critique": h,
        "critique": h,
        "milcah.coherence_check": h,
        "coherence_check": h,
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
