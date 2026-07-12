# COS v1.0 — Context Optimization Score

Vendor-agnostic, implementation-independent.

## Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Fidelity | 30 | Critical field recall, identifier preservation |
| Recoverability | 25 | Reference validity, byte-exact recovery |
| Context Safety | 20 | No cross-session leaks, no broken refs |
| Compression Efficiency | 15 | Token reduction |
| Performance | 10 | Latency |

## Hard Gates

COS = FAIL regardless of numeric score if:
- Broken references > 0
- Cross-session ref leakage > 0
- Byte-exact recovery < 100%
- Critical field recall < 99.5%
- Source-code critical omission > 0
- Unicode crash > 0
- Changed-line preservation < 100%

## Status Levels

- OFFICIAL: all required categories measured, hard gates clean
- PARTIAL: some categories not covered
- INCOMPLETE: insufficient data
- FAIL: hard gate violation

## Coverage

COS must report:
- Scenario coverage (X/Y scenarios)
- Category coverage (X/Y categories)
- Metric coverage (X/Y metrics measured)
