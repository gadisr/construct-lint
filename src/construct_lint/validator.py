"""Validation logic for construct-lint."""

from construct_lint.models import Finding, Manifest


FLOAT_TOLERANCE = 1e-9


def validate_manifest(manifest: Manifest, manifest_data: dict) -> list[Finding]:
    """Validate a metrics manifest against all rules.
    
    Args:
        manifest: Parsed manifest object
        manifest_data: Raw manifest dictionary for detecting undeclared fields
        
    Returns:
        List of validation findings (errors/warnings)
    """
    findings: list[Finding] = []
    
    findings.extend(_check_population_non_empty(manifest))
    findings.extend(_check_exclusion_reasons(manifest))
    findings.extend(_check_ids_in_population(manifest))
    findings.extend(_check_no_overlap(manifest))
    findings.extend(_check_sentinels(manifest))
    findings.extend(_check_pass_rate_arithmetic(manifest))
    findings.extend(_check_undeclared_fields(manifest_data))
    
    return findings


def _check_population_non_empty(manifest: Manifest) -> list[Finding]:
    """Rule: Population must be non-empty."""
    if not manifest.population:
        return [Finding(
            rule_id="empty_population",
            severity="error",
            message="Population must be non-empty",
            path="population"
        )]
    return []


def _check_exclusion_reasons(manifest: Manifest) -> list[Finding]:
    """Rule: Every exclusion must have a non-empty reason."""
    findings = []
    for i, exclusion in enumerate(manifest.exclusions):
        if not exclusion.reason or not exclusion.reason.strip():
            findings.append(Finding(
                rule_id="missing_exclusion_reason",
                severity="error",
                message=f"Exclusion '{exclusion.id}' is missing required reason",
                path=f"exclusions[{i}].reason"
            ))
    return findings


def _check_ids_in_population(manifest: Manifest) -> list[Finding]:
    """Rule: Every scored id must be in population ∪ exclusions."""
    findings = []
    
    population_set = set(manifest.population)
    exclusion_set = {exc.id for exc in manifest.exclusions}
    allowed = population_set | exclusion_set
    
    for id_ in manifest.included:
        if id_ not in allowed:
            findings.append(Finding(
                rule_id="id_not_in_population",
                severity="error",
                message=f"Included id '{id_}' not found in population or exclusions",
                path="included"
            ))
    
    for id_ in manifest.successes:
        if id_ not in allowed:
            findings.append(Finding(
                rule_id="id_not_in_population",
                severity="error",
                message=f"Success id '{id_}' not found in population or exclusions",
                path="successes"
            ))
    
    return findings


def _check_no_overlap(manifest: Manifest) -> list[Finding]:
    """Rule: No id may appear in both included/scored-success and exclusions."""
    findings = []
    
    exclusion_ids = {exc.id for exc in manifest.exclusions}
    
    for id_ in manifest.included:
        if id_ in exclusion_ids:
            findings.append(Finding(
                rule_id="exclusion_overlap",
                severity="error",
                message=f"Id '{id_}' appears in both included and exclusions",
                path="included"
            ))
    
    for id_ in manifest.successes:
        if id_ in exclusion_ids:
            findings.append(Finding(
                rule_id="exclusion_overlap",
                severity="error",
                message=f"Id '{id_}' appears in both successes and exclusions",
                path="successes"
            ))
    
    return findings


def _check_sentinels(manifest: Manifest) -> list[Finding]:
    """Rule: Declared sentinels must not appear as successful outcomes."""
    findings = []
    
    if manifest.sentinels is None:
        return findings
    
    sentinel_set = set(manifest.sentinels)
    
    for success in manifest.successes:
        if success in sentinel_set:
            findings.append(Finding(
                rule_id="sentinel_as_success",
                severity="error",
                message=f"Success value '{success}' is declared as a sentinel",
                path="successes"
            ))
    
    return findings


def _check_pass_rate_arithmetic(manifest: Manifest) -> list[Finding]:
    """Rule: Pass-rate arithmetic must match: successes / |population − exclusions|."""
    findings = []
    
    excluded_ids = {exc.id for exc in manifest.exclusions}
    effective_population = len([id_ for id_ in manifest.population if id_ not in excluded_ids])
    
    if effective_population == 0:
        if manifest.pass_rate != 0.0:
            findings.append(Finding(
                rule_id="arithmetic_mismatch",
                severity="error",
                message="Pass rate must be 0.0 when effective population is zero",
                path="pass_rate"
            ))
        return findings
    
    expected_pass_rate = len(manifest.successes) / effective_population
    
    if abs(manifest.pass_rate - expected_pass_rate) > FLOAT_TOLERANCE:
        findings.append(Finding(
            rule_id="arithmetic_mismatch",
            severity="error",
            message=f"Pass rate mismatch: declared {manifest.pass_rate}, computed {expected_pass_rate:.6f} (successes={len(manifest.successes)}, effective_population={effective_population})",
            path="pass_rate"
        ))
    
    return findings


def _check_undeclared_fields(manifest_data: dict) -> list[Finding]:
    """Rule: Unknown/undeclared fields that look like silent filters should fail."""
    findings = []
    
    known_fields = {
        "population", "exclusions", "included", "successes", 
        "pass_rate", "sentinels", "metadata", "description", "name"
    }
    
    suspicious_patterns = ["filter", "exclude", "ignore", "skip", "omit", "hidden"]
    
    for field in manifest_data.keys():
        if field not in known_fields:
            if any(pattern in field.lower() for pattern in suspicious_patterns):
                findings.append(Finding(
                    rule_id="undeclared_exclusion_field",
                    severity="error",
                    message=f"Undeclared exclusion-like field '{field}' detected",
                    path=field
                ))
    
    return findings
