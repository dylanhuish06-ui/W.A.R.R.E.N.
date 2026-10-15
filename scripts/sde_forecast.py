"""Causal, analytic SDE-style probabilistic forecasts for offline UK equity research.

Daily time units. GBM: dS/S=mu dt+sigma dW, predicting Gaussian log-returns.
OU: dX=kappa(theta-X)dt+eta dW for daily log-return X; an AR(1)
discretization yields a correlated Gaussian sum for the forecast horizon.

This forecasts a distribution, not a certainty or calibrated AI alpha signal.
No broker calls, external dependencies, or future observations.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, expm1, isfinite, log, sqrt
from statistics import NormalDist
from typing import Sequence

STANDARD_NORMAL = NormalDist()


@dataclass(frozen=True)
class Forecast:
    model: str
    horizon_sessions: int
    mean_log_return: float
    sd_log_return: float
    expected_simple_return: float
    probability_positive: float
    lower_decile_return: float
    upper_decile_return: float
    ar1_phi: float | None = None


def predict(
    closes: Sequence[float],
    horizon: int,
    model: str = "gbm",
    drift_shrinkage: float = 0.35,
) -> Forecast:
    """Fit through the LAST close supplied, then predict the next horizon.

    closes must be a strictly past-to-present window, never including an
    execution day's close. GBM uses Gaussian iid daily log returns.
    OU models daily log-return mean reversion using a stable AR(1), equivalent
    to the exact sampling rule of a mean-reverting OU diffusion.
    """
    if len(closes) < 21 or horizon < 1 or horizon > 63:
        raise ValueError("Need >=21 prices and 1..63 forecast sessions")
    if not (isfinite(drift_shrinkage) and 0 <= drift_shrinkage <= 1):
        raise ValueError("Invalid drift shrinkage")
    if any(not isfinite(p) or p <= 0 for p in closes):
        raise ValueError("Invalid close")
    returns = [log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    if any(not isfinite(r) or abs(r) > 0.75 for r in returns):
        raise ValueError("Extreme/unverified daily price jump: forecast abstains")
    n = len(returns)
    raw_mean = sum(returns) / n
    sample_var = sum((v - raw_mean) ** 2 for v in returns) / (n - 1)
    phi: float | None = None

    if model == "gbm":
        mean = horizon * raw_mean * drift_shrinkage
        variance = horizon * sample_var
    elif model == "ou":
        # AR(1) fit to stationary daily log returns. Clamp unstable estimates;
        # OU decay phi=exp(-kappa), with finite reversion speed kappa.
        a, b = returns[:-1], returns[1:]
        denom = sum((v - raw_mean) ** 2 for v in a)
        raw_phi = (sum((x - raw_mean) * (y - raw_mean) for x, y in zip(a, b))
                   / denom) if denom > 1e-18 else 0.0
        phi = min(0.95, max(0.0, raw_phi))
        residuals = [(y - raw_mean) - phi * (x - raw_mean)
                     for x, y in zip(a, b)]
        innovation_variance = sum(r * r for r in residuals) / max(1, len(residuals) - 1)
        theta = raw_mean * drift_shrinkage
        mean = (horizon * theta
                + (returns[-1] - theta) * phi * (1 - phi ** horizon) / (1 - phi))
        variance = innovation_variance * sum(
            ((1 - phi ** k) / (1 - phi)) ** 2 for k in range(1, horizon + 1))
    else:
        raise ValueError(f"Unsupported predictive model: {model}")

    sd = sqrt(max(0.0, variance))
    probability = STANDARD_NORMAL.cdf(mean / sd) if sd > 1e-12 else (
        1.0 if mean > 0 else (0.0 if mean < 0 else 0.5))
    low = expm1(mean + sd * STANDARD_NORMAL.inv_cdf(0.10))
    high = expm1(mean + sd * STANDARD_NORMAL.inv_cdf(0.90))
    expected = expm1(mean + 0.5 * variance)
    if not all(isfinite(v) for v in (mean, sd, probability, low, high, expected)):
        raise ValueError("Non-finite stochastic forecast")
    return Forecast(model, horizon, mean, sd, expected, probability, low, high, phi)
