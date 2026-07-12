"""Kettu Eval CLI — Typer-based interface."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from kettu_eval.adapters.base import AdapterManifest, validate_manifest
from kettu_eval.core.models import (
    AdapterType,
    EvalStatus,
    RunRecord,
    Coverage,
    MetricResult,
    HardGate,
    RunStatus,
)
from kettu_eval.storage.run_storage import RunStorage

app = typer.Typer(
    name="kettu-eval",
    help="Independent evaluation framework for AI agent systems",
    no_args_is_help=True,
)


# ── init ──────────────────────────────────────────────────────────────────────

@app.command()
def init():
    """Initialize Kettu Eval workspace."""
    base = Path(".kettu-eval")
    dirs = ["runs", "artifacts", "reports", "baselines", "cache", "logs"]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    typer.echo(f"✓ Initialized {base.resolve()}")
    for d in dirs:
        typer.echo(f"  {d}/")


# ── adapters ─────────────────────────────────────────────────────────────────

@app.command()
def adapters_list():
    """List available adapters."""
    typer.echo("Built-in adapters:")
    typer.echo("  null-baseline  — memory, context, agent, retrieval (no-op)")
    typer.echo("")
    typer.echo("Reference adapters (Phase 2):")
    typer.echo("  kettu-mem      — Kettu Mem memory adapter")
    typer.echo("  kettu-squeeze  — Kettu Squeeze context adapter")
    typer.echo("  sqlite-simple  — Simple SQLite memory baseline")


@app.command()
def adapters_inspect(name: str):
    """Inspect an adapter by name."""
    if name == "null-baseline":
        typer.echo("Adapter: null-baseline")
        typer.echo("  Type: multi (memory, context, agent, retrieval)")
        typer.echo("  Description: No-op baseline. Returns nothing, remembers nothing.")
        typer.echo("  Capabilities: all = false (no-op)")
    else:
        typer.echo(f"Unknown adapter: {name}", err=True)
        raise typer.Exit(code=1)


@app.command()
def validate_adapter(manifest_path: str):
    """Validate an adapter manifest YAML."""
    try:
        manifest = AdapterManifest.from_yaml(manifest_path)
        issues = validate_manifest(manifest)
        if issues:
            typer.echo(f"✗ {len(issues)} issues found:")
            for issue in issues:
                typer.echo(f"  - {issue}")
            raise typer.Exit(code=1)
        typer.echo(f"✓ Manifest valid: {manifest.name} v{manifest.version}")
        typer.echo(f"  Type: {manifest.adapter_type.value}")
        typer.echo(f"  Transport: {manifest.transport}")
        caps = [k for k, v in manifest.capabilities.items() if v]
        typer.echo(f"  Capabilities: {len(caps)} enabled")
    except Exception as e:
        typer.echo(f"✗ Error: {e}", err=True)
        raise typer.Exit(code=1)


# ── datasets ─────────────────────────────────────────────────────────────────

@app.command()
def datasets_list():
    """List available datasets."""
    typer.echo("Planned datasets (Phase 3+):")
    typer.echo("  memory-core     v1.0.0 — fact retention, update, isolation (30 scenarios)")
    typer.echo("  retrieval-core  v1.0.0 — 500 docs, precision/recall/MRR")
    typer.echo("  context-core    v1.0.0 — COS evaluation (ported from Kettu Squeeze)")
    typer.echo("  agent-core      v1.0.0 — 20 tasks, bug finding, repair, planning")
    typer.echo("")
    typer.echo("Status: datasets not yet implemented (Phase 3+).")


# ── run ──────────────────────────────────────────────────────────────────────

@app.command()
def run(suite: str, adapter: str = "null-baseline"):
    """Run a benchmark suite against an adapter."""
    typer.echo(f"Suite: {suite}, Adapter: {adapter}")
    typer.echo("Status: runner not yet implemented (Phase 3+).")
    typer.echo("Use 'kettu-eval doctor' to verify installation.")


# ── report ───────────────────────────────────────────────────────────────────

@app.command()
def report(run_id: str = ""):
    """Show report for a run ID."""
    storage = RunStorage()
    if run_id:
        records = storage.read_all()
        found = [r for r in records if r.get("run_id") == run_id]
        if found:
            import json
            typer.echo(json.dumps(found[0], indent=2, default=str))
        else:
            typer.echo(f"Run not found: {run_id}", err=True)
            raise typer.Exit(code=1)
    else:
        count = storage.count()
        typer.echo(f"Total runs: {count}")
        if count > 0:
            last = storage.last()
            typer.echo(f"Last run: {last.get('run_id', '?')} — {last.get('scenario_id', '?')}")


# ── compare ──────────────────────────────────────────────────────────────────

@app.command()
def compare(baseline: str, candidate: str):
    """Compare two adapters (blind A/B)."""
    typer.echo(f"Compare: {baseline} vs {candidate}")
    typer.echo("Status: comparison not yet implemented (Phase 3+).")


# ── reproduce ────────────────────────────────────────────────────────────────

@app.command()
def reproduce(run_path: str):
    """Reproduce a previous run."""
    typer.echo(f"Reproduce: {run_path}")
    typer.echo("Status: reproduction not yet implemented (Phase 3+).")


# ── doctor ───────────────────────────────────────────────────────────────────

@app.command()
def doctor():
    """Run system checks."""
    ok = True

    typer.echo("🔍 Kettu Eval Doctor")
    typer.echo("─" * 40)

    # Python version
    v = sys.version_info
    if v >= (3, 11):
        typer.echo(f"  Python: ✓ {v.major}.{v.minor}.{v.micro}")
    else:
        typer.echo(f"  Python: ✗ {v.major}.{v.minor}.{v.micro} (need 3.11+)")
        ok = False

    # Dependencies
    for dep in ["pydantic", "typer", "yaml"]:
        try:
            __import__(dep)
            typer.echo(f"  {dep}: ✓")
        except ImportError:
            typer.echo(f"  {dep}: ✗ not installed")
            ok = False

    # Storage
    storage = RunStorage()
    typer.echo(f"  Run storage: ✓ ({storage.count()} records)")

    # Core models
    try:
        from kettu_eval.core.models import RunRecord, MetricResult, HardGate, Coverage
        typer.echo("  Core models: ✓")
    except Exception as e:
        typer.echo(f"  Core models: ✗ {e}")
        ok = False

    # Adapters
    try:
        from kettu_eval.adapters.null_adapter import (
            NullMemoryAdapter, NullContextAdapter, NullAgentAdapter, NullRetrievalAdapter
        )
        typer.echo("  Null adapters: ✓ (4/4)")
    except Exception as e:
        typer.echo(f"  Null adapters: ✗ {e}")
        ok = False

    typer.echo("─" * 40)
    if ok:
        typer.echo("✅ All checks passed")
    else:
        typer.echo("⚠ Some checks failed — review above")


if __name__ == "__main__":
    app()
