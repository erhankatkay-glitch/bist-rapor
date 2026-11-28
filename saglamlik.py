# SPDX-License-Identifier: Apache-2.0
# Kaynak: QuantDinger (Open Byte Inc.), backend_api_python/app/services/strategy_evolution/statistics.py
# Apache License 2.0 — https://www.apache.org/licenses/LICENSE-2.0 . Değişiklik: yalnız gerekli fonksiyonlar alındı, _histogram sadeleştirildi, Türkçe açıklama eklendi.
"""Geçmiş test sağlamlık istatistikleri (strateji seçiminde şans / aşırı uyum kontrolü):
- deflated_sharpe: çok sayıda kural denendiğinde gözlenen Sharpe'ın şans payına göre düzeltilmiş anlamlılık olasılığı.
- probability_of_backtest_overfitting (PBO): eğitimde en iyi olan kuralın sınamada ortanın altında kalma olasılığı.
- monte_carlo_bootstrap: işlem getirilerini blok blok yeniden örnekleyerek sonuç ve en büyük düşüş dağılımı.
Getiriler monte_carlo_bootstrap'ta oran (0,05 = %5), sonuç yüzdeler %."""
from __future__ import annotations

import math
import random
from statistics import NormalDist, mean, median, pstdev
from typing import Any, Iterable


def _histogram(values, *, bins):
    if not values: return []
    lo, hi = min(values), max(values)
    if hi <= lo: return [{"from": lo, "to": hi, "count": len(values)}]
    w = (hi - lo) / bins; out = []
    for b in range(bins):
        a = lo + b * w; c = a + w
        out.append({"from": round(a, 4), "to": round(c, 4), "count": sum(1 for v in values if a <= v < c or (b == bins - 1 and v == hi))})
    return out


def deflated_sharpe(returns: list[float], *, observed_sharpe: float, trials: int) -> dict[str, float | int | bool | str]:
    values = [float(value) for value in returns if math.isfinite(float(value))]
    sample_count = len(values)
    if sample_count < 3:
        return {"available": False, "reason": "insufficientObservations", "probability": 0.0, "benchmarkSharpe": 0.0, "observations": sample_count}
    avg = mean(values)
    sigma = pstdev(values)
    if sigma <= 1e-12:
        return {"available": False, "reason": "insufficientVariation", "probability": 0.0, "benchmarkSharpe": 0.0, "observations": sample_count}
    skew = mean(((value - avg) / sigma) ** 3 for value in values)
    kurtosis = mean(((value - avg) / sigma) ** 4 for value in values)
    effective_trials = max(1, int(trials))
    denominator = math.sqrt(max(1e-12, 1.0 - skew * observed_sharpe + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2))
    if effective_trials == 1:
        benchmark = 0.0
    else:
        gamma = 0.5772156649
        normal = NormalDist()
        sharpe_standard_error = denominator / math.sqrt(sample_count - 1)
        benchmark = sharpe_standard_error * (
            (1.0 - gamma) * normal.inv_cdf(1.0 - 1.0 / effective_trials)
            + gamma * normal.inv_cdf(1.0 - 1.0 / (effective_trials * math.e))
        )
    statistic = (observed_sharpe - benchmark) * math.sqrt(sample_count - 1) / denominator
    return {
        "available": True,
        "probability": round(NormalDist().cdf(statistic), 6),
        "observedSharpe": round(observed_sharpe, 6),
        "benchmarkSharpe": round(benchmark, 6),
        "observations": sample_count,
        "skew": round(skew, 6),
        "kurtosis": round(kurtosis, 6),
    }


def probability_of_backtest_overfitting(score_matrix: list[list[float]], *, max_combinations: int = 2000) -> dict[str, Any]:
    matrix = [row for row in score_matrix if len(row) >= 4]
    if len(matrix) < 2:
        return {"available": False, "reason": "insufficientCandidates", "probability": 0.0, "samples": 0, "logits": []}
    periods = min(len(row) for row in matrix)
    if periods < 4:
        return {"available": False, "reason": "insufficientFolds", "probability": 0.0, "samples": 0, "logits": []}
    half = periods // 2
    combinations = list(_combinations(range(periods), half))
    if len(combinations) > max_combinations:
        rng = random.Random(1776)
        combinations = rng.sample(combinations, max_combinations)
    logits: list[float] = []
    for train_indexes in combinations:
        train_set = set(train_indexes)
        test_indexes = [index for index in range(periods) if index not in train_set]
        train_scores = [mean(row[index] for index in train_indexes) for row in matrix]
        winner = max(range(len(matrix)), key=lambda index: train_scores[index])
        test_scores = [mean(row[index] for index in test_indexes) for row in matrix]
        ordered = sorted(test_scores)
        rank = ordered.index(test_scores[winner]) + 1
        percentile = min(1.0 - 1e-9, max(1e-9, rank / (len(matrix) + 1.0)))
        logits.append(math.log(percentile / (1.0 - percentile)))
    probability = sum(1 for value in logits if value <= 0.0) / len(logits) if logits else 0.0
    return {
        "available": bool(logits),
        "probability": round(probability, 6),
        "samples": len(logits),
        "medianLogit": round(median(logits), 6) if logits else 0.0,
        "logits": [round(value, 5) for value in logits[:200]],
    }


def monte_carlo_bootstrap(returns: list[float], *, paths: int, block_size: int, seed: int) -> dict[str, Any]:
    samples = [float(value) for value in returns if math.isfinite(float(value))]
    if len(samples) < 2:
        return {"available": False, "reason": "insufficientObservations", "paths": 0, "terminalReturns": [], "percentiles": {}, "drawdownPercentiles": {}, "lossProbability": 0.0}
    if pstdev(samples) <= 1e-12:
        return {"available": False, "reason": "insufficientVariation", "paths": 0, "terminalReturns": [], "percentiles": {}, "drawdownPercentiles": {}, "lossProbability": 0.0}
    rng = random.Random(seed)
    terminal: list[float] = []
    drawdowns: list[float] = []
    length = len(samples)
    adaptive_block = max(1, int(round(length ** (1.0 / 3.0))))
    block = max(1, min(block_size, adaptive_block, length - 1))
    for _ in range(paths):
        path: list[float] = []
        while len(path) < length:
            start = rng.randrange(length)
            path.extend(samples[(start + offset) % length] for offset in range(block))
        equity = 1.0
        peak = 1.0
        worst = 0.0
        for value in path[:length]:
            equity *= 1.0 + value
            peak = max(peak, equity)
            worst = min(worst, (equity / peak - 1.0) * 100.0)
        terminal.append((equity - 1.0) * 100.0)
        drawdowns.append(worst)
    return {
        "available": True,
        "paths": paths,
        "observations": length,
        "requestedBlockSize": block_size,
        "effectiveBlockSize": block,
        "uniqueTerminalReturns": len({round(value, 10) for value in terminal}),
        "terminalReturns": _histogram(terminal, bins=24),
        "percentiles": _percentiles(terminal),
        "drawdownPercentiles": _percentiles(drawdowns),
        "lossProbability": round(sum(1 for value in terminal if value < 0) / paths, 6),
    }


def sample_sharpe(returns: list[float]) -> float:
    values = [float(value) for value in returns if math.isfinite(float(value))]
    if len(values) < 2:
        return 0.0
    sigma = pstdev(values)
    return mean(values) / sigma if sigma > 1e-12 else 0.0


def _percentiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {str(item): round(_quantile(ordered, item / 100.0), 4) for item in (1, 5, 25, 50, 75, 95, 99)}


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    return values[lower] * (upper - position) + values[upper] * (position - lower)


def _combinations(values: Iterable[int], size: int):
    values = tuple(values)
    if size == 0:
        yield ()
        return
    for index in range(len(values)):
        for tail in _combinations(values[index + 1 :], size - 1):
            yield (values[index],) + tail
