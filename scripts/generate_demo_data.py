"""Generate SYNTHETIC daily-close data solely for end-to-end tests and demos."""
import argparse
import csv
from datetime import date, timedelta
from math import sin
from pathlib import Path


def generate(path: Path, sessions: int = 120, instruments: int = 25) -> None:
    if sessions < 25 or instruments < 2:
        raise ValueError("Use >=25 sessions and >=2 instruments")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "symbol", "close"])
        day = date(2025, 1, 1)
        i = 0
        while i < sessions:
            if day.weekday() < 5:
                for j in range(instruments):
                    close = 70 + j + i * (0.012 + j * 0.0018) + 0.45 * sin(i / (4.0 + j * 0.08) + j)
                    writer.writerow([day.isoformat(), f"DEMO{j:02d}", f"{close:.5f}"])
                i += 1
            day += timedelta(days=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/demo_prices.csv")
    options = parser.parse_args()
    generate(Path(options.output))
