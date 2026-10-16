"""Strict daily close loader; reject duplicates, gaps and corrupt values."""
import csv
from datetime import date
from math import isfinite
from pathlib import Path


def load_close_panel(path: str | Path) -> list[tuple[date, dict[str, float]]]:
    rows: dict[date, dict[str, float]] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"date", "symbol", "close"}.issubset(reader.fieldnames):
            raise ValueError("Expected CSV columns: date,symbol,close")
        for record in reader:
            day = date.fromisoformat(record["date"])
            symbol = record["symbol"].strip().upper()
            close = float(record["close"])
            if not symbol or not (isfinite(close) and close > 0):
                raise ValueError(f"Invalid symbol/close on {day}")
            one_day = rows.setdefault(day, {})
            if symbol in one_day:
                raise ValueError(f"Duplicate symbol {symbol} on {day}")
            one_day[symbol] = close
    if not rows:
        raise ValueError("Price CSV is empty")
    ordered = sorted(rows.items())
    symbols = set(ordered[0][1])
    if len(symbols) < 2:
        raise ValueError("Need at least two instruments")
    for day, closes in ordered:
        if set(closes) != symbols:
            raise ValueError(f"Incomplete price panel on {day}; no silent forward filling")
    return ordered
