# Versioning — Kettu Eval

## Semantic Versioning

Kettu Eval follows SemVer with adapter-contract-specific additions.

```
MAJOR.MINOR.PATCH
```

### MAJOR (X.0.0)
- Breaking changes to adapter interfaces
- Method removal or signature change
- Capability dependency changes that invalidate existing manifests
- Hard gate semantic changes
- Metric model breaking changes

### MINOR (0.X.0)
- New adapter methods (optional, with defaults)
- New capabilities
- New evaluator profiles
- New CLI commands
- New report formats (additive)
- New dataset versions

### PATCH (0.0.X)
- Bug fixes
- Validation improvements (stricter, not looser)
- Performance improvements
- Documentation updates
- Test additions

## Current Version: 0.1.0

Status: **Experimental.** Adapter contract frozen for 0.1.x. No breaking changes until 0.2.0.

## Dataset Versioning

Datasets use independent versioning:

```
memory-core v1.0.0
```

Dataset changes:
- PATCH: fixture fixes, typo corrections
- MINOR: new scenarios added
- MAJOR: scenario removal, metric changes, breaking fixture format changes

## Release Cadence

- PATCH: as needed (bug fixes)
- MINOR: after completing a Phase (adapter, evaluator, profile)
- MAJOR: only when adapter contract must break (avoid if possible)

## Freeze Policy

- Adapter interfaces: frozen for 0.1.x
- Capability dependency map: frozen for 0.1.x
- Metric model: frozen for 0.1.x
- Hard gate semantics: frozen for 0.1.x

Any change to these requires a MINOR version bump and explicit documentation in CHANGELOG.
