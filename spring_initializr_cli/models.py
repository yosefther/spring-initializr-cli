"""Domain models for CLI requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectSpec:
    """Normalized project specification before sending to Initializr."""

    project_type: str
    language: str
    boot_version: str
    group_id: str
    artifact_id: str
    name: str
    package_name: str
    java_version: str
    packaging: str
    dependencies: list[str]

    @property
    def dependencies_csv(self) -> str:
        return ",".join(self.dependencies)

    def to_query_params(self) -> dict[str, str]:
        return {
            "type": self.project_type,
            "language": self.language,
            "bootVersion": self.boot_version,
            "groupId": self.group_id,
            "artifactId": self.artifact_id,
            "name": self.name,
            "packageName": self.package_name,
            "javaVersion": self.java_version,
            "packaging": self.packaging,
            "dependencies": self.dependencies_csv,
        }
