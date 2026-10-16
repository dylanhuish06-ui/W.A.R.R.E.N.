"""Configurable UK equities cost sensitivity, entirely broker-disconnected.

All fee profiles are HYPOTHETICAL until a dated IBKR statement and actual
UK duty/levy applicability have been independently verified. No order APIs.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import json
from pathlib import Path


def D(value) -> Decimal:
    try:
        val=Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid amount") from exc
    if not val.is_finite():
        raise ValueError("Nonfinite amount")
    return val


@dataclass(frozen=True)
class HypotheticalFees:
    label: str
    minimum_commission_gbp: str
    commission_rate: str
    venue_fee_gbp: str
    slippage_bps: str
    duty_rate: str

    def checked(self):
        if not isinstance(self.label,str) or not self.label:
            raise ValueError("Missing fee scenario label")
        values=[D(getattr(self, field)) for field in (
            "minimum_commission_gbp","commission_rate","venue_fee_gbp",
            "slippage_bps","duty_rate")]
        if any(v < 0 for v in values) or values[1] > Decimal(".05") or values[3] > 500 or values[4] > Decimal(".1"):
            raise ValueError("Implausible hypothetical fee parameters")
        return self


SCENARIOS=(
    HypotheticalFees("optimistic-unverified", "1", ".0005", "0", "5", ".005"),
    HypotheticalFees("illustrative-fixed-unverified", "3", ".0005", "0.25", "10", ".005"),
    HypotheticalFees("adverse-stress-unverified", "3", ".0015", "1", "25", ".005"),
)


def trade(side: str, whole_shares: int, bid_gbp, ask_gbp,
          fees: HypotheticalFees, stamp_duty_applies: bool) -> dict:
    """One synthetic execution incl bid/ask + extra adverse slippage."""
    fees.checked()
    if side not in ("BUY","SELL") or type(whole_shares) is not int or whole_shares <= 0:
        raise ValueError("Only positive whole-share buys/sells")
    if type(stamp_duty_applies) is not bool:
        raise ValueError("Stamp-duty applicability must be explicit")
    bid,ask = D(bid_gbp),D(ask_gbp)
    if bid <= 0 or ask < bid:
        raise ValueError("Invalid bid/ask")
    adverse = D(fees.slippage_bps) / Decimal(10000)
    price = ask*(1+adverse) if side=="BUY" else bid*(1-adverse)
    if price <= 0:
        raise ValueError("Slippage exceeds price")
    notional = price*whole_shares
    commission = max(D(fees.minimum_commission_gbp),
                     notional*D(fees.commission_rate))
    venue = D(fees.venue_fee_gbp)
    stamp = notional*D(fees.duty_rate) if (side=="BUY" and stamp_duty_applies) else Decimal(0)
    total_fee = commission+venue+stamp
    cash_flow = -(notional+total_fee) if side=="BUY" else notional-total_fee
    return {"side":side,"whole_shares":whole_shares,
            "price_gbp":str(price),"notional_gbp":str(notional),
            "commission_gbp":str(commission),"venue_gbp":str(venue),
            "stamp_duty_gbp":str(stamp),"total_fee_gbp":str(total_fee),
            "signed_cash_gbp":str(cash_flow)}


def round_trip(target_budget_gbp, bid_gbp, ask_gbp,
               fees: HypotheticalFees, *, stamp_duty_applies: bool) -> dict:
    """Hypothetical immediate buy + sell; demonstrates fee/spread drag."""
    budget=D(target_budget_gbp)
    if budget <= 0:
        raise ValueError("Invalid cash budget")
    ask=D(ask_gbp)
    if ask <= 0:
        raise ValueError("Invalid ask")
    # Initial budget is strict all-in, so commission and duty need reserve.
    max_shares = int((budget / ask).to_integral_value(rounding=ROUND_FLOOR))
    for qty in range(max_shares,0,-1):
        b=trade("BUY",qty,bid_gbp,ask_gbp,fees,stamp_duty_applies)
        if -D(b["signed_cash_gbp"]) <= budget:
            s=trade("SELL",qty,bid_gbp,ask_gbp,fees,stamp_duty_applies)
            pnl=D(b["signed_cash_gbp"])+D(s["signed_cash_gbp"])
            return {
                "scenario":fees.label,"capital_committed_gbp":str(budget),
                "share_count":qty,"buy":b,"sell":s,
                "instant_round_trip_pnl_gbp":str(pnl),
                "instant_round_trip_cost_pct_of_budget":str(-100*pnl/budget),
                "stamp_duty_applies":stamp_duty_applies,
                "orders_sent":0,"broker_connected":False,
            }
    raise ValueError("No tradable whole share after estimated fees")


def build_report() -> dict:
    """Representative £300 allocation within a £1,000 hypothetical account."""
    return {
        "project":"W.A.R.R.E.N.","status":"FEE_SCENARIO_RESEARCH_ONLY",
        "input_capital_gbp":1000,"target_tranche_gbp":300,
        "illustrative_spread": {"bid_gbp":"20.00","ask_gbp":"20.04"},
        "trials":[round_trip(300,"20","20.04",f,stamp_duty_applies=stamp)
                  for f in SCENARIOS for stamp in (True,False)],
        "pricing_verified_against_ibkr_account":False,
        "tax_applicability_verified":False,
        "paper_execution_enabled":False,
        "limitations":[
            "Fee schedules are explicit hypothetical scenarios, NOT an IBKR account quote",
            "UK stamp duty is security/transaction dependent and must be externally verified",
            "Immediate round trip is fee sensitivity, not forecasted strategy P&L",
            "Real quote units, market hours, venue fees, FX conversion and partial fills may differ",
        ],
    }


def main():
    parser=argparse.ArgumentParser(description="Offline fee sensitivity, zero orders")
    parser.add_argument("--output",type=Path,default=Path("outputs/cost_sensitivity.json"))
    args=parser.parse_args()
    report=build_report()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "scenarios":len(report["trials"]),
        "pricing_verified":False,"broker_connected":False,"orders_sent":0
    },indent=2))


if __name__=="__main__":
    main()
