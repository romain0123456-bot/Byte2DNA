from __future__ import annotations

from app.services.constraints import classify_status, gc_percent, max_homopolymer
from app.models import EncodeConfig


def test_gc_percent_examples() -> None:
    assert gc_percent("GCGC") == 100.0
    assert gc_percent("ATAT") == 0.0
    assert gc_percent("ACGT") == 50.0
    assert gc_percent("ACGTACGT") == 50.0


def test_homopolymer_examples() -> None:
    assert max_homopolymer("AAAA") == 4
    assert max_homopolymer("ACGT") == 1
    assert max_homopolymer("AAATTT") == 3
    assert max_homopolymer("AAAACCCCGGGGTTTT") == 4


def test_status_valid_warning_invalid() -> None:
    config = EncodeConfig(gc_min=40, gc_max=60, homopolymer_max=3)
    assert classify_status(50.0, 2, config) == "VALID"
    assert classify_status(36.0, 3, config) == "WARNING"
    assert classify_status(10.0, 8, config) == "INVALID"
