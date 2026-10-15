"""Cash-only integer-share *proposals*; no broker client, no actual orders."""
from __future__ import annotations
import math
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Proposal:
    symbol: str
    side: str
    quantity_whole_shares: int
    reference_price_gbp: float
    estimated_fees_gbp: float
    estimated_total_gbp: float

def propose_buys(
    cash_gbp: float, prices_gbp: dict[str, float],
    desired_weights: dict[str, float], portfolio_equity_gbp: float,
    max_exposure: float = 0.94, max_name_weight: float = 0.35,
) -> dict:
    """Buy-side scenario only, deliberate overestimate of fees.

    Cannot submit transactions; normalises NO units. Caller must convert
    LSE GBp to GBP using independently audited symbol metadata.
    """
    values = (cash_gbp, portfolio_equity_gbp, max_exposure, max_name_weight)
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Non-finite finance inputs")
    if portfolio_equity_gbp <= 0 or cash_gbp < 0 or not (0 < max_exposure <= 0.94) or not (0 < max_name_weight <= .35):
        raise ValueError("Inadmissible risk limits")
    if not desired_weights or set(prices_gbp) != set(desired_weights):
        raise ValueError("Missing or unmatched quote(s)")
    if any(not isinstance(s, str) or not s.strip() for s in prices_gbp):
        raise ValueError("Invalid ticker")
    if any(not math.isfinite(p) or p <= 0 for p in prices_gbp.values()):
        raise ValueError("Invalid GBP prices")
    if any(not math.isfinite(w) or w < 0 or w > max_name_weight for w in desired_weights.values()):
        raise ValueError("Name weight exceeds cap")
    if sum(desired_weights.values()) > max_exposure + 1e-9:
        raise ValueError("Total allocation exceeds exposure limit")
    spent = 0.0
    orders = []
    for symbol in sorted(prices_gbp):
        price = prices_gbp[symbol]
        target = portfolio_equity_gbp * desired_weights[symbol]
        # Conservatively reserve 1 GBP commission, 5bps slippage and
        # 50bps UK buy-side duty. Additional broker charges not included.
        max_including_fees = min(target, cash_gbp - spent)
        quantity = max(0, math.floor((max_including_fees - 1.0) / (price * 1.0055)))
        if quantity < 1:
            continue
        notional = quantity * price
        fees = max(1.0, notional * .0005) + .0005 * notional + .005 * notional
        cost = notional + fees
        while quantity > 0 and cost > max_including_fees + 1e-9:
            quantity -= 1
            notional = quantity * price
            fees = max(1.0, notional * .0005) + .0055 * notional
            cost = notional + fees
        if quantity > 0:
            orders.append(asdict(Proposal(symbol, "BUY", quantity, price, round(fees, 4), round(cost, 4))))
            spent += cost
    if spent > cash_gbp + 1e-7 or spent > portfolio_equity_gbp * max_exposure + 1e-7:
        raise AssertionError("Exposure or buying power exceeded")
    return {
        "status": "SIMULATED PROPOSAL ONLY; never transmitted",
        "currency": "GBP", "price_unit": "GBP per whole share",
        "starting_cash_gbp": round(cash_gbp, 2),
        "estimated_spend_gbp": round(spent, 2),
        "estimated_cash_remaining_gbp": round(cash_gbp - spent, 2),
        "intents": orders, "orders_submitted": 0,
        "broker_connected": False, "execution_armed": False,
        "warnings": ["No market spread, venue fees, live order data or trading halts modelled",
                     "LSE GBp prices MUST be converted to GBP before calling this function",
                     "Does not reconcile existing positions; never use intents as an executable order list"],
    }
