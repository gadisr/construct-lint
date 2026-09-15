"""CLI interface for construct-lint."""

import argparse
import json
import sys
from pathlib import Path

from construct_lint.models import Manifest
from construct_lint.validator import validate_manifest


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="construct-lint",
        description="CI checker for evaluation construct validity"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    check_parser = subparsers.add_parser(
        "check",
        help="Validate a metrics manifest"
    )
    check_parser.add_argument(
        "manifest",
        type=Path,
        help="Path to manifest file (JSON)"
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output findings as JSON"
    )
    
    args = parser.parse_args()
    
    if args.command == "check":
        sys.exit(check_manifest(args.manifest, json_output=args.json))


def check_manifest(manifest_path: Path, json_output: bool = False) -> int:
    """Check a manifest file and return exit code.
    
    Args:
        manifest_path: Path to manifest file
        json_output: Whether to output JSON instead of human-readable format
        
    Returns:
        0 if valid, 1 if validation errors found
    """
    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}", file=sys.stderr)
        return 1
    
    try:
        with open(manifest_path) as f:
            manifest_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {manifest_path}: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error reading {manifest_path}: {e}", file=sys.stderr)
        return 1
    
    try:
        manifest = Manifest.from_dict(manifest_data)
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error: Invalid manifest structure: {e}", file=sys.stderr)
        return 1
    
    findings = validate_manifest(manifest, manifest_data)
    
    if json_output:
        output = {
            "valid": len(findings) == 0,
            "findings": [f.to_dict() for f in findings]
        }
        print(json.dumps(output, indent=2))
    else:
        if not findings:
            print(f"✓ {manifest_path}: Valid")
            return 0
        
        print(f"✗ {manifest_path}: {len(findings)} issue(s) found\n")
        for finding in findings:
            symbol = "✗" if finding.severity == "error" else "⚠"
            path_str = f" ({finding.path})" if finding.path else ""
            print(f"{symbol} [{finding.rule_id}] {finding.message}{path_str}")
    
    return 1 if findings else 0


if __name__ == "__main__":
    main()
