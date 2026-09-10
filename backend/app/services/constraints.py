"""GC content, homopolymer length and fragment QC status."""

from __future__ import annotations

from app.constants import GC_WARNING_MARGIN, HOMOPOLYMER_WARNING_EXTRA
from app.models import EncodeConfig, FragmentStatus


def gc_percent(sequence: str) -> float:
    if not sequence:
        return 0.0
    gc = sum(1 for base in sequence if base in ("G", "C"))
    return round(100.0 * gc / len(sequence), 4)


def max_homopolymer(sequence: str) -> int:
    if not sequence:
        return 0
    longest = current = 1
    previous = sequence[0]
    for base in sequence[1:]:
        if base == previous:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 1
            previous = base
    return longest


def classify_status(
    gc: float,
    homopolymer: int,
    config: EncodeConfig,
) -> FragmentStatus:
    gc_ok = config.gc_min <= gc <= config.gc_max
    hp_ok = homopolymer <= config.homopolymer_max
    if gc_ok and hp_ok:
        return "VALID"

    gc_warn = (config.gc_min - GC_WARNING_MARGIN) <= gc <= (
        config.gc_max + GC_WARNING_MARGIN
    )
    hp_warn = homopolymer <= config.homopolymer_max + HOMOPOLYMER_WARNING_EXTRA
    if gc_warn and hp_warn:
        return "WARNING"
    return "INVALID"


def constraint_score(gc: float, homopolymer: int, config: EncodeConfig) -> tuple[int, float]:
    """Lower is better. Rank by status, then distance from 50% GC, then homopolymer."""
    status = classify_status(gc, homopolymer, config)
    rank = {"VALID": 0, "WARNING": 1, "INVALID": 2}[status]
    target = (config.gc_min + config.gc_max) / 2.0
    return rank, abs(gc - target) + homopolymer * 0.1
