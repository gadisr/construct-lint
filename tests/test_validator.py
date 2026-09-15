"""Tests for construct-lint validator."""

import pytest

from construct_lint.models import Exclusion, Manifest
from construct_lint.validator import validate_manifest


def test_valid_manifest():
    """Test that a valid manifest passes all checks."""
    manifest = Manifest(
        population=["t1", "t2", "t3", "t4"],
        exclusions=[Exclusion(id="t2", reason="Infrastructure failure")],
        included=["t1", "t3", "t4"],
        successes=["t1", "t3"],
        pass_rate=2/3,
        sentinels=["ERROR", "TIMEOUT"]
    )
    manifest_data = {
        "population": ["t1", "t2", "t3", "t4"],
        "exclusions": [{"id": "t2", "reason": "Infrastructure failure"}],
        "included": ["t1", "t3", "t4"],
        "successes": ["t1", "t3"],
        "pass_rate": 2/3,
        "sentinels": ["ERROR", "TIMEOUT"]
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert len(findings) == 0


def test_empty_population():
    """Test that empty population is detected."""
    manifest = Manifest(
        population=[],
        exclusions=[],
        included=[],
        successes=[],
        pass_rate=0.0
    )
    manifest_data = {"population": [], "exclusions": [], "included": [], "successes": [], "pass_rate": 0.0}
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "empty_population" for f in findings)


def test_missing_exclusion_reason():
    """Test that exclusions without reasons are detected."""
    manifest = Manifest(
        population=["t1", "t2"],
        exclusions=[Exclusion(id="t1", reason="")],
        included=["t2"],
        successes=["t2"],
        pass_rate=1.0
    )
    manifest_data = {
        "population": ["t1", "t2"],
        "exclusions": [{"id": "t1", "reason": ""}],
        "included": ["t2"],
        "successes": ["t2"],
        "pass_rate": 1.0
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "missing_exclusion_reason" for f in findings)


def test_id_not_in_population():
    """Test that scored IDs not in population are detected."""
    manifest = Manifest(
        population=["t1", "t2"],
        exclusions=[],
        included=["t1", "t2", "t3"],
        successes=["t1"],
        pass_rate=0.5
    )
    manifest_data = {
        "population": ["t1", "t2"],
        "exclusions": [],
        "included": ["t1", "t2", "t3"],
        "successes": ["t1"],
        "pass_rate": 0.5
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "id_not_in_population" for f in findings)


def test_exclusion_overlap():
    """Test that IDs in both included and exclusions are detected."""
    manifest = Manifest(
        population=["t1", "t2", "t3"],
        exclusions=[Exclusion(id="t2", reason="Test failure")],
        included=["t1", "t2"],
        successes=["t1"],
        pass_rate=1.0
    )
    manifest_data = {
        "population": ["t1", "t2", "t3"],
        "exclusions": [{"id": "t2", "reason": "Test failure"}],
        "included": ["t1", "t2"],
        "successes": ["t1"],
        "pass_rate": 1.0
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "exclusion_overlap" for f in findings)


def test_sentinel_as_success():
    """Test that sentinels appearing as successes are detected."""
    manifest = Manifest(
        population=["t1", "t2", "t3"],
        exclusions=[],
        included=["t1", "t2", "t3"],
        successes=["t1", "ERROR"],
        pass_rate=2/3,
        sentinels=["ERROR", "TIMEOUT"]
    )
    manifest_data = {
        "population": ["t1", "t2", "t3"],
        "exclusions": [],
        "included": ["t1", "t2", "t3"],
        "successes": ["t1", "ERROR"],
        "pass_rate": 2/3,
        "sentinels": ["ERROR", "TIMEOUT"]
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "sentinel_as_success" for f in findings)


def test_arithmetic_mismatch():
    """Test that pass rate arithmetic mismatches are detected."""
    manifest = Manifest(
        population=["t1", "t2", "t3", "t4"],
        exclusions=[],
        included=["t1", "t2", "t3", "t4"],
        successes=["t1", "t2"],
        pass_rate=0.75,
        sentinels=[]
    )
    manifest_data = {
        "population": ["t1", "t2", "t3", "t4"],
        "exclusions": [],
        "included": ["t1", "t2", "t3", "t4"],
        "successes": ["t1", "t2"],
        "pass_rate": 0.75,
        "sentinels": []
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "arithmetic_mismatch" for f in findings)


def test_arithmetic_with_exclusions():
    """Test pass rate calculation with exclusions."""
    manifest = Manifest(
        population=["t1", "t2", "t3", "t4", "t5"],
        exclusions=[Exclusion(id="t3", reason="Infra issue")],
        included=["t1", "t2", "t4", "t5"],
        successes=["t1", "t4", "t5"],
        pass_rate=0.75,
        sentinels=[]
    )
    manifest_data = {
        "population": ["t1", "t2", "t3", "t4", "t5"],
        "exclusions": [{"id": "t3", "reason": "Infra issue"}],
        "included": ["t1", "t2", "t4", "t5"],
        "successes": ["t1", "t4", "t5"],
        "pass_rate": 0.75,
        "sentinels": []
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert len(findings) == 0


def test_undeclared_exclusion_field():
    """Test that undeclared exclusion-like fields are detected."""
    manifest = Manifest(
        population=["t1", "t2"],
        exclusions=[],
        included=["t1", "t2"],
        successes=["t1"],
        pass_rate=0.5
    )
    manifest_data = {
        "population": ["t1", "t2"],
        "exclusions": [],
        "included": ["t1", "t2"],
        "successes": ["t1"],
        "pass_rate": 0.5,
        "hidden_filter": ["t3"]
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert any(f.rule_id == "undeclared_exclusion_field" for f in findings)


def test_zero_effective_population():
    """Test handling when all population items are excluded."""
    manifest = Manifest(
        population=["t1", "t2"],
        exclusions=[
            Exclusion(id="t1", reason="Reason 1"),
            Exclusion(id="t2", reason="Reason 2")
        ],
        included=[],
        successes=[],
        pass_rate=0.0
    )
    manifest_data = {
        "population": ["t1", "t2"],
        "exclusions": [
            {"id": "t1", "reason": "Reason 1"},
            {"id": "t2", "reason": "Reason 2"}
        ],
        "included": [],
        "successes": [],
        "pass_rate": 0.0
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert len(findings) == 0


def test_manifest_from_dict():
    """Test parsing manifest from dictionary."""
    data = {
        "population": ["t1", "t2"],
        "exclusions": [{"id": "t1", "reason": "Test"}],
        "included": ["t2"],
        "successes": ["t2"],
        "pass_rate": 1.0,
        "sentinels": ["ERROR"]
    }
    
    manifest = Manifest.from_dict(data)
    assert len(manifest.population) == 2
    assert len(manifest.exclusions) == 1
    assert manifest.exclusions[0].reason == "Test"
    assert manifest.sentinels == ["ERROR"]


def test_multiple_violations():
    """Test manifest with multiple validation errors."""
    manifest = Manifest(
        population=["t1"],
        exclusions=[Exclusion(id="t2", reason="")],
        included=["t1", "t3"],
        successes=["t1", "ERROR"],
        pass_rate=0.9,
        sentinels=["ERROR"]
    )
    manifest_data = {
        "population": ["t1"],
        "exclusions": [{"id": "t2", "reason": ""}],
        "included": ["t1", "t3"],
        "successes": ["t1", "ERROR"],
        "pass_rate": 0.9,
        "sentinels": ["ERROR"]
    }
    
    findings = validate_manifest(manifest, manifest_data)
    assert len(findings) >= 3
    rule_ids = {f.rule_id for f in findings}
    assert "missing_exclusion_reason" in rule_ids
    assert "id_not_in_population" in rule_ids
    assert "sentinel_as_success" in rule_ids
