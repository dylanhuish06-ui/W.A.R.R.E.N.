"""SIMULATION ONLY. Deterministic whole-share rebalance plans and audit hashes.

No IBKR imports, TCP clients, network requests or order submission functions.
Plans are abstract *intents*, not orders. A human must separately approve any
future broker integration and live trading is excluded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import hashlib
import json

CENT = Decimal("0.01")
COMMISSION_MIN = Decimal("1")
COMMISSION_RATE = Decimal("0.0005")
SLIPPAGE = Decimal("0.0005")
STAMP_DUTY_ESTIMATE = Decimal("0.005")
MAX_QUOTE_AGE_SECONDS = 300
MAX_SNAPSHOT_AGE_SECONDS = 900


class SafetyBlock(ValueError):
    """Fail-closed input, risk, freshness or reconciliation violation."""


def money(value):
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SafetyBlock("Invalid monetary input") from exc
    if not x.is_finite():
        raise SafetyBlock("Nonfinite numeric input")
    return x


def timestamp(value):
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SafetyBlock("Malformed UTC timestamp") from exc
    if t.tzinfo is None:
        raise SafetyBlock("Timestamp must include timezone")
    return t.astimezone(timezone.utc)


def _hash(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate(snapshot, now):
    """Validate an explicitly synthetic portfolio/quote bundle."""
    now = now.astimezone(timezone.utc)
    if (snapshot.get("environment") != "SIMULATION_ONLY"
            or snapshot.get("broker_connected") is not False
            or snapshot.get("open_orders") != []):
        raise SafetyBlock("External broker state or pending orders prohibited")
    asof = timestamp(snapshot.get("asof_utc"))
    age = (now - asof).total_seconds()
    if not (0 <= age <= MAX_SNAPSHOT_AGE_SECONDS):
        raise SafetyBlock("Stale or future-dated snapshot")
    if snapshot.get("cash_currency") != "GBP":
        raise SafetyBlock("Portfolio cash must be GBP")
    cash = money(snapshot.get("cash_gbp"))
    if cash < 0:
        raise SafetyBlock("No borrowing/margin permitted")
    quotes = snapshot.get("quotes")
    positions = snapshot.get("positions")
    if not isinstance(quotes, dict) or not quotes or not isinstance(positions, dict):
        raise SafetyBlock("Missing quote/position maps")
    if not set(positions).issubset(quotes):
        raise SafetyBlock("Position without a corresponding quote")
    conids = set()
    normalized = {}
    for symbol, q in quotes.items():
        if (not isinstance(symbol, str) or not symbol.isascii() or not symbol or
                not symbol.replace(".", "").replace("-", "").isalnum()):
            raise SafetyBlock("Invalid ticker")
        if (q.get("currency") != "GBP" or q.get("exchange") != "LSE"
                or q.get("security_type") != "STK"
                or q.get("quote_unit") not in ("GBP", "GBp")):
            raise SafetyBlock("Unqualified quote currency, unit or instrument")
        conid = q.get("conid")
        if type(conid) is not int or conid <= 0 or conid in conids:
            raise SafetyBlock("Missing, invalid or duplicated contract identifier")
        conids.add(conid)
        quote_age = (now - timestamp(q.get("asof_utc"))).total_seconds()
        if not (0 <= quote_age <= MAX_QUOTE_AGE_SECONDS):
            raise SafetyBlock("Stale or future quote")
        scale = Decimal("0.01") if q["quote_unit"] == "GBp" else Decimal("1")
        bid, ask = money(q.get("bid")) * scale, money(q.get("ask")) * scale
        if bid <= 0 or ask < bid or (ask - bid) / ((ask + bid) / 2) > Decimal("0.02"):
            raise SafetyBlock("Invalid or excessive bid/ask spread")
        normalized[symbol] = {
            "bid": bid, "ask": ask, "mid": (bid + ask) / 2,
            "conid": conid, "quote_unit_source": q["quote_unit"],
        }
    for symbol, qty in positions.items():
        if type(qty) is not int or qty < 0:
            raise SafetyBlock("Positions must be nonnegative whole shares")
    return cash, {s: positions.get(s, 0) for s in sorted(quotes)}, normalized


def _fee(qty, price, side):
    notional = price * qty
    if notional <= 0:
        raise SafetyBlock("Nonpositive trade")
    commission = max(COMMISSION_MIN, notional * COMMISSION_RATE)
    friction = notional * (SLIPPAGE + (STAMP_DUTY_ESTIMATE if side == "BUY" else 0))
    return commission + friction


def plan_rebalance(snapshot, desired_weights, *, now, kill_switch=True,
                   allow_simulation=False, max_turnover_fraction="0.50",
                   max_name_fraction="0.35", max_gross_fraction="0.94"):
    """Require a deliberate local simulation unlock; never transmit orders."""
    if kill_switch or allow_simulation is not True:
        raise SafetyBlock("Kill switch on, simulation requires explicit local unlock")
    cash, positions, quotes = validate(snapshot, now)
    if not isinstance(desired_weights, dict) or not set(desired_weights).issubset(quotes):
        raise SafetyBlock("Unknown intended asset")
    gross_limit = money(max_gross_fraction)
    name_limit = money(max_name_fraction)
    turnover_limit = money(max_turnover_fraction)
    if not (0 < gross_limit <= Decimal(".94") and 0 < name_limit <= Decimal(".35")
            and 0 < turnover_limit <= Decimal("1.0")):
        raise SafetyBlock("Excessive risk configuration")
    weights = {sym: money(desired_weights.get(sym, 0)) for sym in sorted(quotes)}
    if any(w < 0 or w > name_limit for w in weights.values()) or sum(weights.values()) > gross_limit:
        raise SafetyBlock("Requested portfolio exceeds allocation caps")

    equity = cash + sum(qty * quotes[s]["mid"] for s, qty in positions.items())
    if equity <= 0:
        raise SafetyBlock("Invalid account equity")
    existing_gross = sum(qty * quotes[s]["mid"] for s, qty in positions.items())
    if existing_gross > equity * gross_limit + CENT:
        raise SafetyBlock("Existing exposure already exceeds cap")
    if any(qty * quotes[s]["mid"] > equity * name_limit + CENT
           for s, qty in positions.items()):
        raise SafetyBlock("Existing individual position exceeds cap")

    # Leave a buffer against commissions and price spread reducing total equity.
    desired = {s: int((equity * w * Decimal(".98") / quotes[s]["ask"])
                      .to_integral_value(rounding=ROUND_FLOOR))
               for s, w in weights.items()}
    after = dict(positions)
    intents = []
    turnover = Decimal("0")
    cash_after = cash
    # Sell everything that must be reduced before buying.
    for side in ("SELL", "BUY"):
        for sym in sorted(quotes):
            current, target = after[sym], desired[sym]
            qty = max(0, current - target) if side == "SELL" else max(0, target - current)
            if qty == 0:
                continue
            quote = quotes[sym]
            p = quote["bid"] if side == "SELL" else quote["ask"]
            notional = qty * p
            if notional < Decimal("10"):
                raise SafetyBlock("Small whole-share trade rejected due to minimum dealing costs")
            charge = _fee(qty, p, side)
            signed_cash = (notional - charge) if side == "SELL" else -(notional + charge)
            if side == "SELL" and signed_cash <= 0:
                raise SafetyBlock("Sell proceeds below expenses")
            if side == "BUY" and cash_after + signed_cash < 0:
                raise SafetyBlock("Insufficient after-cost cash for full allocation")
            after[sym] += -qty if side == "SELL" else qty
            cash_after += signed_cash
            turnover += notional
            intents.append({
                "symbol": sym, "conid": quote["conid"], "side": side,
                "quantity": qty, "price_gbp": str(p), "estimated_fee_gbp": str(charge),
                "cash_delta_gbp": str(signed_cash), "intent_type": "NON_TRANSMITTABLE_SIMULATION",
            })
    if turnover > equity * turnover_limit + CENT:
        raise SafetyBlock("Portfolio turnover budget exceeded")
    projected_value = cash_after + sum(qty * quotes[s]["mid"] for s, qty in after.items())
    gross_after = sum(qty * quotes[s]["mid"] for s, qty in after.items())
    if projected_value <= 0 or cash_after < 0 or gross_after > projected_value * gross_limit + CENT:
        raise SafetyBlock("Post-trade buying-power or exposure breach")
    if any(qty * quotes[s]["mid"] > projected_value * name_limit + CENT
           for s, qty in after.items()):
        raise SafetyBlock("Post-trade individual position breach")
    output = {
        "mode": "SIMULATION_ONLY", "broker_connected": False,
        "orders_submitted": 0, "execution_enabled": False,
        "snapshot_sha256": _hash(snapshot),
        "asof_utc": snapshot["asof_utc"], "target_weights": {s: str(w) for s,w in weights.items()},
        "initial_equity_gbp": str(equity), "initial_cash_gbp": str(cash),
        "final_cash_gbp": str(cash_after), "projected_equity_gbp": str(projected_value),
        "projected_positions": after, "turnover_gbp": str(turnover),
        "intents": intents, "synthetic_only": True,
        "disclaimer": "Planning and local replay only; not orders, not TWS/IBKR integration.",
    }
    output["plan_sha256"] = _hash(output)
    return output


def simulate_and_reconcile(snapshot, plan, *, now):
    """Model *instant full fills* offline and reconcile every position/cash value.

    This does not emulate broker partial fills or live reconciliation.
    """
    cash, positions, quotes = validate(snapshot, now)
    if plan.get("mode") != "SIMULATION_ONLY" or plan.get("orders_submitted") != 0:
        raise SafetyBlock("Not a strictly synthetic plan")
    digest = dict(plan)
    actual_hash = digest.pop("plan_sha256", None)
    if actual_hash != _hash(digest) or plan.get("snapshot_sha256") != _hash(snapshot):
        raise SafetyBlock("Tampered or mismatched plan")
    for line in plan["intents"]:
        s = line["symbol"]
        qty = line["quantity"]
        if s not in positions or type(qty) is not int or qty <= 0:
            raise SafetyBlock("Invalid intent for simulation")
        if line["side"] not in ("BUY", "SELL") or line["conid"] != quotes[s]["conid"]:
            raise SafetyBlock("Unknown contract or direction")
        signed = money(line["cash_delta_gbp"])
        if line["side"] == "SELL":
            if qty > positions[s]:
                raise SafetyBlock("Simulation would short a position")
            positions[s] -= qty
        else:
            positions[s] += qty
        cash += signed
        if cash < 0:
            raise SafetyBlock("Simulated margin breach")
    expected_cash = money(plan["final_cash_gbp"])
    if cash != expected_cash or positions != plan["projected_positions"]:
        raise SafetyBlock("Position or cash mismatch after simulated fills")
    return {
        "status": "SIMULATED_RECONCILED",
        "plan_sha256": actual_hash, "cash_gbp": str(cash),
        "positions": positions, "orders_submitted": 0, "broker_connected": False,
    }
