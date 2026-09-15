"""Data models for construct-lint manifests."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Exclusion:
    """An excluded item with required reason."""
    
    id: str
    reason: str


@dataclass
class Manifest:
    """Metrics manifest describing pass-rate computation."""
    
    population: list[str]
    exclusions: list[Exclusion]
    included: list[str]
    successes: list[str]
    pass_rate: float
    sentinels: list[Any] | None = None
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        """Parse manifest from dictionary."""
        exclusions = []
        for exc in data.get("exclusions", []):
            if isinstance(exc, dict):
                exclusions.append(Exclusion(
                    id=exc["id"],
                    reason=exc["reason"]
                ))
            else:
                exclusions.append(Exclusion(id=str(exc), reason=""))
        
        return cls(
            population=data.get("population", []),
            exclusions=exclusions,
            included=data.get("included", []),
            successes=data.get("successes", []),
            pass_rate=data.get("pass_rate", 0.0),
            sentinels=data.get("sentinels")
        )


@dataclass
class Finding:
    """A validation finding (error or warning)."""
    
    rule_id: str
    severity: str
    message: str
    path: str = ""
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON output."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "path": self.path
        }
