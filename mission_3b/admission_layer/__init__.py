"""Mission 3B canonical admission layer.

Public API:
    PGDSLCanonicalLayer            — orchestrator (per-tool + composition).
    CanonicalAdmissionReport       — result struct.
    detected_at_admission          — defense-ASR decision rule.
    verify_compositions            — composition-replay primitive.
    composition_detects            — composition decision over a tool sequence.
"""
from .pgdsl_canonical import (
    PGDSLCanonicalLayer,
    CanonicalAdmissionReport,
    detected_at_admission,
)
from .composition_verifier import (
    verify_compositions,
    composition_detects,
    CompositionVerdict,
    BlockedPair,
    SAFE_BAND_LIT101,
    SAFE_BAND_LIT201,
    COMPOSITION_HORIZON_S,
    DEFAULT_INITIAL_STATES,
)

__all__ = [
    "PGDSLCanonicalLayer",
    "CanonicalAdmissionReport",
    "detected_at_admission",
    "verify_compositions",
    "composition_detects",
    "CompositionVerdict",
    "BlockedPair",
    "SAFE_BAND_LIT101",
    "SAFE_BAND_LIT201",
    "COMPOSITION_HORIZON_S",
    "DEFAULT_INITIAL_STATES",
]
