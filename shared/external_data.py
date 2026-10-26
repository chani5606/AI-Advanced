from __future__ import annotations

# Simulated external source (could be replaced with real HTTP/API)
# The harness treats this as an external tool call.
COURSE_HINTS: dict[str, list[str]] = {
    "algorithms": [
        "Practice 2 graph problems daily.",
        "Review dynamic programming state transitions.",
    ],
    "databases": [
        "Write SQL by hand before running queries.",
        "Indexing: compare B-tree vs hash tradeoffs.",
    ],
    "statistics": [
        "Focus on confidence intervals with worked examples.",
        "Build intuition with small sampling simulations.",
    ],
}
