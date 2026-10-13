"""M2 — Inference Cost Levers: $/1M-token, batch x cache x cascade (deck §7).

Run: python missions/m2_inference_levers.py
"""
from __future__ import annotations
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from missions._common import load_csv, num
from finops import pricing

# $/1M tokens (input, output) — illustrative 2026.
MODEL_PRICES = {"small": (0.20, 0.40), "large": (3.00, 15.00)}

# Scenario assumptions, not observations: five reads per write, incremental
# write fee = 1.25x normal input rate. Write fees receive no batch discount.
CACHE_READS = 5.0
CACHE_WRITE_MULTIPLIER = 1.25


def optimized_request_cost(r: dict, reads: float = CACHE_READS,
                           include_write: bool = True) -> float:
    inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
    cached = min(inp, max(0, int(num(r["cached_input_tokens"]))))
    pin, pout = MODEL_PRICES[r["route_tier"]]
    write_rate = pin * CACHE_WRITE_MULTIPLIER
    enabled = pricing.cache_is_worth_it(reads, write_rate, pin) if include_write else True
    cost = pricing.request_cost(inp, out, pin, pout,
                                cached_in=cached if enabled else 0,
                                batch=bool(int(num(r["is_batch"]))))
    # For batch requests the read savings are also halved. Recheck that gate.
    batch_factor = 0.5 if int(num(r["is_batch"])) else 1.0
    if enabled and include_write:
        enabled = pricing.cache_is_worth_it(reads, write_rate, pin * batch_factor)
        if not enabled:
            return pricing.request_cost(inp, out, pin, pout,
                                        batch=bool(int(num(r["is_batch"]))))
        cost += cached / 1e6 * write_rate / reads
    return cost


def run(verbose: bool = True) -> dict:
    rows = load_csv("token_usage.csv")
    base_cost = opt_cost = 0.0
    total_tokens = 0
    for r in rows:
        inp, out = int(num(r["input_tokens"])), int(num(r["output_tokens"]))
        cached = int(num(r["cached_input_tokens"]))
        is_batch = bool(int(num(r["is_batch"])))
        total_tokens += inp + out
        # BASELINE: naive deployment — everything on the large model, no cache, no batch
        lin, lout = MODEL_PRICES["large"]
        base_cost += pricing.request_cost(inp, out, lin, lout)
        # OPTIMIZED: cascade (route_tier), prompt caching, batch API
        pin, pout = MODEL_PRICES[r["route_tier"]]
        opt_cost += optimized_request_cost(r)

    base_pm = pricing.dollars_per_million(base_cost, total_tokens)
    opt_pm = pricing.dollars_per_million(opt_cost, total_tokens)
    savings_pct = (1 - opt_cost / base_cost) * 100 if base_cost else 0.0

    if verbose:
        print("== M2 Inference Cost Levers ==")
        print(f"requests={len(rows)}  tokens={total_tokens:,}")
        print(f"baseline  : ${base_cost:,.2f}/day   ${base_pm:.3f}/1M-token")
        print(f"optimized : ${opt_cost:,.2f}/day   ${opt_pm:.3f}/1M-token")
        print(f"savings   : {savings_pct:.1f}%  (cascade + caching + batch)")
        print(f"discount stack (batch + 100% cache): {pricing.discount_stack(batch=True, cache_hit_frac=1.0):.3f} of naive")

    scenarios = []
    for reads in (1.0, CACHE_READS):
        cost = sum(optimized_request_cost(r, reads) for r in rows)
        scenarios.append({"reads": reads, "cost": cost,
                          "per_m": pricing.dollars_per_million(cost, total_tokens)})
    cascade = sum(pricing.request_cost(int(num(r["input_tokens"])),
                  int(num(r["output_tokens"])), *MODEL_PRICES[r["route_tier"]]) for r in rows)
    cache_only = sum(pricing.request_cost(int(num(r["input_tokens"])),
                     int(num(r["output_tokens"])), *MODEL_PRICES[r["route_tier"]],
                     cached_in=int(num(r["cached_input_tokens"]))) for r in rows)
    no_write = sum(optimized_request_cost(r, include_write=False) for r in rows)
    return {
        "cache_scenarios": scenarios,
        "stages": {"baseline": base_cost, "cascade": cascade,
                   "cache_no_write": cache_only, "batch_no_write": no_write,
                   "with_write": opt_cost},
        "baseline_daily": round(base_cost, 2), "optimized_daily": round(opt_cost, 2),
        "baseline_per_m": round(base_pm, 3), "optimized_per_m": round(opt_pm, 3),
        "savings_pct": round(savings_pct, 1), "total_tokens": total_tokens,
    }


if __name__ == "__main__":
    run()
