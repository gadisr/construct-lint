# construct-lint

[![Test](https://github.com/construct-lint/construct-lint/actions/workflows/test.yml/badge.svg)](https://github.com/construct-lint/construct-lint/actions/workflows/test.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**construct-lint** is a CI checker for evaluation **construct validity**: pass-rate (and similar) metrics must have a well-defined population, declared exclusions, and no silent sentinels that inflate scores.

## Why?

When reporting evaluation metrics like pass rates or accuracy:

- **Silent exclusions** inflate scores (e.g., filtering "hard cases" without disclosure)
- **Sentinel values** (`TIMEOUT`, `ERROR`, empty strings) counted as successes corrupt metrics
- **Undefined populations** make comparisons meaningless
- **Arithmetic drift** between declared and computed rates indicates bugs

`construct-lint` enforces construct validity in CI by failing builds when metrics manifests violate these rules.

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

## Contributing

Contributions welcome! This is a v0 release focused on core validation rules. Future enhancements:

- YAML support
- Custom rule plugins
- Configurable strictness levels
- Integration with common eval frameworks

Please open an issue before starting significant work.
