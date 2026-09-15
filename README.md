# construct-lint

[![Test](https://github.com/construct-lint/construct-lint/actions/workflows/test.yml/badge.svg)](https://github.com/construct-lint/construct-lint/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**construct-lint** is a CI checker for evaluation **construct validity** in pass-rate and accuracy metrics. It enforces that every reported score has a well-defined population, explicit exclusions with documented reasons, and no silent sentinels (like `TIMEOUT` or `ERROR`) counted as successes. When metrics manifests violate these rules, CI fails before inflated or misleading scores reach scoreboards, papers, or deployment decisions.

## Public Use Cases

### 1. Benchmark Scoreboard CI

**Scenario**: You maintain a public leaderboard (e.g., SWE-bench, MMLU, HumanEval variants) and want to prevent submissions with silent exclusions or sentinel-inflated scores.

**Manifest**: `leaderboard_submission.json`
```json
{
  "name": "team_x_swe_bench_lite",
  "population": ["django__001", "django__002", "flask__001", "requests__001"],
  "exclusions": [
    {
      "id": "flask__001",
      "reason": "Timeout due to CI infrastructure failure (not model fault)"
    }
  ],
  "included": ["django__001", "django__002", "requests__001"],
  "successes": ["django__001", "requests__001"],
  "pass_rate": 0.6666666666666666,
  "sentinels": ["TIMEOUT", "ERROR", "INFRA_FAIL"]
}
```

**CI check**:
```bash
construct-lint check leaderboard_submission.json
# Exit 0 if valid, 1 if excluded tasks lack reasons or sentinels appear in successes
```

**Caught issues**: Missing exclusion reasons, sentinel values counted as passes, arithmetic drift (2/3 vs claimed 0.75).

---

### 2. Private Eval Suite Freeze Validation

**Scenario**: Your team runs nightly evals on a frozen private benchmark. Before archiving results or comparing across model versions, you enforce that every exclusion is documented and the denominator is stable.

**Manifest**: `nightly_run_2026_09_15.json`
```json
{
  "name": "internal_coding_suite_v2.3",
  "population": ["task_001", "task_002", "task_003", "task_004", "task_005"],
  "exclusions": [
    {
      "id": "task_003",
      "reason": "Flaky test environment (filed bug #1234)"
    }
  ],
  "included": ["task_001", "task_002", "task_004", "task_005"],
  "successes": ["task_001", "task_004", "task_005"],
  "pass_rate": 0.75,
  "sentinels": ["TIMEOUT", null, ""]
}
```

**CI check**:
```bash
construct-lint check nightly_run_2026_09_15.json --json > validation.json
```

**Ensures**: No silent filters added (e.g., `hidden_exclude_hard_cases`), all excluded IDs have audit trail, pass-rate arithmetic is correct.

---

### 3. Meta-Harness Evolution: Metrics Hygiene

**Scenario**: You're evolving an evaluation harness and want to prevent regressions where new error modes (e.g., `PARSE_ERROR`, `OOM`) accidentally inflate scores by being counted as successes instead of failures.

**Manifest**: `harness_v3_smoke_test.json`
```json
{
  "name": "harness_v3_migration_check",
  "population": ["smoke_01", "smoke_02", "smoke_03"],
  "exclusions": [],
  "included": ["smoke_01", "smoke_02", "smoke_03"],
  "successes": ["smoke_01", "smoke_02"],
  "pass_rate": 0.6666666666666666,
  "sentinels": ["TIMEOUT", "ERROR", "PARSE_ERROR", "OOM", null]
}
```

**CI check**:
```bash
# In your harness test suite
construct-lint check harness_v3_smoke_test.json || exit 1
```

**Prevents**: New sentinel values (e.g., `PARSE_ERROR`) from being silently counted as successes when the harness changes.

## Installation

```bash
pip install construct-lint
```

Or install from source:

```bash
git clone https://github.com/construct-lint/construct-lint.git
cd construct-lint
pip install -e .
```

## Usage

### Basic CLI

```bash
# Check a manifest
construct-lint check path/to/manifest.json

# Get JSON output for CI integration
construct-lint check manifest.json --json
```

### Python API

```python
from construct_lint import Manifest, validate_manifest

# Load and validate
with open("manifest.json") as f:
    data = json.load(f)

manifest = Manifest.from_dict(data)
findings = validate_manifest(manifest, data)

if findings:
    for finding in findings:
        print(f"{finding.severity}: {finding.message}")
```

## Manifest Format

A metrics manifest is a JSON file describing how a pass-rate was computed:

```json
{
  "population": ["task_001", "task_002", "task_003", "task_004", "task_005"],
  "exclusions": [
    {
      "id": "task_003",
      "reason": "Test environment failure (infrastructure issue, not agent fault)"
    }
  ],
  "included": ["task_001", "task_002", "task_004", "task_005"],
  "successes": ["task_001", "task_004", "task_005"],
  "pass_rate": 0.75,
  "sentinels": ["TIMEOUT", "ERROR", null, ""]
}
```

### Required Fields

- **`population`**: List of all task/episode IDs in the evaluation set
- **`exclusions`**: List of excluded IDs with required `reason` for each
- **`included`**: List of IDs actually scored (population minus exclusions)
- **`successes`**: List of IDs that passed
- **`pass_rate`**: Declared pass rate (must match arithmetic)

### Optional Fields

- **`sentinels`**: Values that must never be counted as success (e.g., `"TIMEOUT"`, `"ERROR"`, `null`)
- **`metadata`**, **`description`**, **`name`**: Allowed documentation fields

## Validation Rules

`construct-lint` enforces these rules (CI fails on violation):

### 1. Population Non-Empty
**Rule**: Population must contain at least one item.

```json
✗ {"population": []}  // FAIL
```

### 2. Exclusion Reasons Required
**Rule**: Every exclusion must have a non-empty `reason`.

```json
✗ {"exclusions": [{"id": "task_1", "reason": ""}]}  // FAIL
✓ {"exclusions": [{"id": "task_1", "reason": "Infrastructure failure"}]}  // PASS
```

### 3. IDs in Population
**Rule**: Every scored ID (in `included` or `successes`) must be in `population ∪ exclusions`.

```json
✗ {
  "population": ["t1", "t2"],
  "included": ["t1", "t2", "t3"]  // t3 not in population
}
```

### 4. No Overlap
**Rule**: No ID may appear in both `included`/`successes` and `exclusions`.

```json
✗ {
  "exclusions": [{"id": "t1", "reason": "Test"}],
  "included": ["t1"]  // t1 is excluded!
}
```

### 5. Sentinel Safety
**Rule**: Declared `sentinels` must not appear in `successes`.

```json
✗ {
  "sentinels": ["TIMEOUT", "ERROR"],
  "successes": ["task_1", "TIMEOUT"]  // Sentinel counted as success!
}
```

### 6. Arithmetic Correctness
**Rule**: `pass_rate` must equal `len(successes) / len(included)` (within 1e-9 tolerance).

```json
✗ {
  "included": ["t1", "t2", "t3", "t4"],
  "successes": ["t1", "t2"],
  "pass_rate": 0.75  // Should be 0.5!
}
```

### 7. No Silent Filters
**Rule**: Undeclared fields that look like filters (e.g., `hidden_filter`, `ignore_list`) cause CI failure.

```json
✗ {
  "population": ["t1", "t2"],
  "hidden_filter": ["t3"]  // Undeclared exclusion-like field!
}
```

## Examples

See [`examples/`](examples/) for sample manifests:

- [`valid_manifest.json`](examples/valid_manifest.json) — Clean manifest that passes all checks
- [`invalid_missing_reason.json`](examples/invalid_missing_reason.json) — Exclusion without reason
- [`invalid_sentinel_success.json`](examples/invalid_sentinel_success.json) — Sentinel counted as success
- [`invalid_arithmetic.json`](examples/invalid_arithmetic.json) — Pass rate doesn't match computation

## CI Integration

### GitHub Actions

```yaml
- name: Validate metrics
  run: |
    pip install construct-lint
    construct-lint check results/manifest.json
```

### Exit Codes

- `0`: Valid manifest
- `1`: Validation errors found or file errors

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run with coverage
pytest --cov=construct_lint --cov-report=term-missing
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## With failstrata

If you're using [failstrata](https://github.com/cursor/failstrata) for stratified failure analysis, construct-lint provides a complementary layer: failstrata identifies *why* tasks fail (infra vs. agent fault), while construct-lint enforces that those stratifications are declared in your metrics manifests and don't silently inflate pass rates. Use both for rigorous eval hygiene.

## Contributing

Contributions welcome! This is a v0 release focused on core validation rules. Future enhancements:

- YAML support
- Custom rule plugins
- Configurable strictness levels
- Integration with common eval frameworks

Please open an issue before starting significant work.
