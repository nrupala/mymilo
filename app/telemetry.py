# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2026 Nrupal Akolkar
"""Engine telemetry shaping (Token-Efficiency Engine, slice 4).

The chat endpoint records one telemetry row per request (plan vs
actual) via ``Database.record_telemetry``. This module turns the raw
rows into the rollup the operator reads: what the engine actually
saved versus naive full-history prompting, how much of each prompt
the backend's KV cache served for free, and whether the token
estimator is drifting (bias beyond ±10% over ≥20 estimator-sourced
samples raises a calibration warning).

The savings baseline is an estimate by construction: at request time
the endpoint records ``full_history_tokens`` — the session's whole
stored transcript converted at the estimator's char ratio — i.e. what
a naive full-history prompt would have carried for the conversation
portion. It excludes persona/skill/RAG overhead on both sides of the
comparison, so the percentage is honest about the tiering effect and
slightly conservative overall.
"""

from __future__ import annotations

from typing import Any

CALIBRATION_BIAS_PCT = 10.0
CALIBRATION_MIN_SAMPLES = 20


def build_chat_record(
    *,
    route: str,
    plan: dict | None,
    data: dict,
    degraded_from: str | None = None,
    full_history_tokens: int | None = None,
) -> dict[str, Any]:
    """Assemble a telemetry row from the token plan + backend response."""
    usage = data.get("usage") or {}
    timings = data.get("timings") or {}
    choices = data.get("choices") or [{}]
    plan = plan or {}
    return {
        "route": route,
        "status": "ok",
        "degraded_from": degraded_from,
        "estimate_source": plan.get("estimate_source"),
        "estimated_input": plan.get("estimated_input"),
        "actual_prompt": usage.get("prompt_tokens"),
        "actual_completion": usage.get("completion_tokens"),
        "planned_max_tokens": plan.get("planned_max_tokens"),
        "utilization": plan.get("utilization"),
        "trimmed_messages": plan.get("trimmed_messages") or 0,
        "cache_n": timings.get("cache_n"),
        "prompt_n": timings.get("prompt_n"),
        "full_history_tokens": full_history_tokens,
        "finish_reason": choices[0].get("finish_reason"),
    }


def shape_rollup(raw: dict, days: int) -> dict[str, Any]:
    """Shape raw ``Database.telemetry_rollup`` aggregates for display."""
    totals = raw.get("totals") or {}
    bias = raw.get("bias") or {}
    prompt_n = totals.get("promptn_sum") or 0
    cache_n = totals.get("cache_sum") or 0
    full = totals.get("full_sum") or 0
    saved = full - (totals.get("prompt_with_full_sum") or 0) if full else 0
    est = bias.get("est") or 0
    samples = bias.get("n") or 0
    bias_pct = (
        round((est - bias.get("act", 0)) / est * 100, 1) if est and samples else None
    )
    return {
        "days": days,
        "requests": totals.get("ok_n") or 0,
        "refused_oversize": totals.get("refused_n") or 0,
        "degraded": totals.get("degraded_n") or 0,
        "prompt_tokens": totals.get("prompt_sum") or 0,
        "completion_tokens": totals.get("completion_sum") or 0,
        "cache_reuse_pct": round(cache_n / prompt_n * 100, 1) if prompt_n else None,
        "full_history_baseline_tokens": full,
        "tokens_saved_vs_full_history": saved,
        "savings_pct": round(saved / full * 100, 1) if full else None,
        "estimator_bias_pct": bias_pct,
        "estimator_samples": samples,
        "calibration_warning": bool(
            bias_pct is not None
            and abs(bias_pct) > CALIBRATION_BIAS_PCT
            and samples >= CALIBRATION_MIN_SAMPLES
        ),
        "over_utilization_requests": totals.get("over80_n") or 0,
        "routes": raw.get("routes") or [],
    }
