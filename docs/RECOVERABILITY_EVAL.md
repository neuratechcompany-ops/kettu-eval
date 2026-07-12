# Recoverability Evaluation

Every ref produced by a context adapter must be:
1. Resolvable via expand()
2. Belong to correct session
3. Return byte-exact content for line ranges
4. Fail predictably for: malformed ref, unknown ref, wrong session, OOB range

## Tests

- Valid ref → expand returns content
- Malformed ref → structured error
- Unknown ref → structured error
- Wrong session → error or empty
- OOB range → error or clamped
- Byte-exact: expanded bytes == original bytes

## Hard Gate

Broken references > 0 → FAIL
