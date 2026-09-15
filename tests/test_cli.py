"""Tests for construct-lint CLI."""

import json
from pathlib import Path

import pytest

from construct_lint.cli import check_manifest


@pytest.fixture
def valid_manifest(tmp_path):
    """Create a valid manifest file."""
    manifest = {
        "population": ["t1", "t2", "t3"],
        "exclusions": [{"id": "t2", "reason": "Test"}],
        "included": ["t1", "t3"],
        "successes": ["t1"],
        "pass_rate": 0.5
    }
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(manifest))
    return path


@pytest.fixture
def invalid_manifest(tmp_path):
    """Create an invalid manifest file."""
    manifest = {
        "population": ["t1", "t2"],
        "exclusions": [{"id": "t1", "reason": ""}],
        "included": ["t1", "t2"],
        "successes": ["t1"],
        "pass_rate": 0.5
    }
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(manifest))
    return path


def test_check_valid_manifest(valid_manifest):
    """Test checking a valid manifest returns 0."""
    exit_code = check_manifest(valid_manifest)
    assert exit_code == 0


def test_check_invalid_manifest(invalid_manifest):
    """Test checking an invalid manifest returns 1."""
    exit_code = check_manifest(invalid_manifest)
    assert exit_code == 1


def test_check_nonexistent_file(tmp_path):
    """Test checking a nonexistent file returns 1."""
    exit_code = check_manifest(tmp_path / "nonexistent.json")
    assert exit_code == 1


def test_check_invalid_json(tmp_path):
    """Test checking invalid JSON returns 1."""
    path = tmp_path / "invalid.json"
    path.write_text("{invalid json")
    exit_code = check_manifest(path)
    assert exit_code == 1


def test_json_output_valid(valid_manifest, capsys):
    """Test JSON output for valid manifest."""
    exit_code = check_manifest(valid_manifest, json_output=True)
    captured = capsys.readouterr()
    
    output = json.loads(captured.out)
    assert output["valid"] is True
    assert len(output["findings"]) == 0
    assert exit_code == 0


def test_json_output_invalid(invalid_manifest, capsys):
    """Test JSON output for invalid manifest."""
    exit_code = check_manifest(invalid_manifest, json_output=True)
    captured = capsys.readouterr()
    
    output = json.loads(captured.out)
    assert output["valid"] is False
    assert len(output["findings"]) > 0
    assert exit_code == 1
    
    finding = output["findings"][0]
    assert "rule_id" in finding
    assert "severity" in finding
    assert "message" in finding
