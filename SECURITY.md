# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ |

## Reporting a Vulnerability

- **Do NOT open a public issue** for security vulnerabilities.
- Use GitHub Security Advisory: https://github.com/neuratechcompany-ops/kettu-eval/security/advisories/new
- Expect acknowledgment within 72 hours.

## Scope

- Adapter transport security
- Secret leakage in reports/logs
- Path traversal in dataset loading
- Arbitrary code execution via malicious datasets
- Prompt injection in tool outputs

## Data Safety

- API keys must use environment variables, never hardcoded
- Datasets are considered untrusted input
- Raw run artifacts may contain benchmark data — do not commit secrets
- `kettu-eval doctor` does not transmit data externally
