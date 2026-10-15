"""Research-only CLI: absolutely no order entry or broker connectivity."""
import argparse
import json
from pathlib import Path
from .backtest import run_backtest
from .config import ResearchConfig
from .data import load_close_panel


def main() -> None:
    parser = argparse.ArgumentParser(prog="warren", description="W.A.R.R.E.N. offline research")
    subparsers = parser.add_subparsers(dest="command", required=True)
    test_cmd = subparsers.add_parser("backtest", help="Run backtest from historical daily closes")
    test_cmd.add_argument("--prices", required=True, help="Long CSV: date,symbol,close")
    test_cmd.add_argument("--output", help="Optional local JSON report path")
    args = parser.parse_args()
    if args.command == "backtest":
        result = run_backtest(load_close_panel(args.prices), ResearchConfig())
        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        summary = {k: v for k, v in result.items() if k != "history"}
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
