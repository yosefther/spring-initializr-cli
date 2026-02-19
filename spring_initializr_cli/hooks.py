"""Post-generation project hooks."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .models import ProjectSpec


def apply_post_generation_hooks(
    project_dir: Path,
    spec: ProjectSpec,
    args: argparse.Namespace,
) -> list[str]:
    actions: list[str] = []

    if bool(args.git_init):
        actions.append(_init_git(project_dir))

    if bool(args.init_readme):
        created = _write_if_missing(project_dir / "README.md", _readme_content(spec))
        actions.append("created README.md" if created else "README.md already exists")

    build_tool = _detect_build_tool(project_dir, spec)

    if bool(args.add_docker):
        created_dockerfile = _write_if_missing(
            project_dir / "Dockerfile",
            _dockerfile_content(build_tool, spec.java_version),
        )
        created_dockerignore = _write_if_missing(project_dir / ".dockerignore", _dockerignore_content())
        if created_dockerfile:
            actions.append("created Dockerfile")
        else:
            actions.append("Dockerfile already exists")
        if created_dockerignore:
            actions.append("created .dockerignore")
        else:
            actions.append(".dockerignore already exists")

    if bool(args.add_github_actions):
        workflow_path = project_dir / ".github" / "workflows" / "ci.yml"
        created_workflow = _write_if_missing(
            workflow_path,
            _github_workflow_content(build_tool, spec.java_version),
        )
        if created_workflow:
            actions.append("created .github/workflows/ci.yml")
        else:
            actions.append(".github/workflows/ci.yml already exists")

    return actions


def _init_git(project_dir: Path) -> str:
    git_dir = project_dir / ".git"
    if git_dir.exists():
        return "git repository already exists"

    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=project_dir,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ValueError("Cannot initialize git: 'git' command was not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise ValueError(f"Cannot initialize git{detail}") from exc

    output = (result.stdout or "").strip()
    if output:
        return f"initialized git repository ({output.splitlines()[-1]})"
    return "initialized git repository"


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _detect_build_tool(project_dir: Path, spec: ProjectSpec) -> str:
    if (project_dir / "mvnw").exists() or spec.project_type.startswith("maven"):
        return "maven"
    if (project_dir / "gradlew").exists() or spec.project_type.startswith("gradle"):
        return "gradle"
    return "unknown"


def _java_major(java_version: str) -> int:
    try:
        return int(java_version)
    except (TypeError, ValueError):
        return 21


def _readme_content(spec: ProjectSpec) -> str:
    return (
        f"# {spec.name}\n\n"
        "Generated with spring-init.\n\n"
        "## Run\n\n"
        "- Maven: `./mvnw spring-boot:run`\n"
        "- Gradle: `./gradlew bootRun`\n"
    )


def _dockerfile_content(build_tool: str, java_version: str) -> str:
    java_major = _java_major(java_version)

    if build_tool == "maven":
        build_cmd = (
            "./mvnw -B -DskipTests package && "
            "cp \"$(find target -maxdepth 1 -name '*.jar' | head -n 1)\" /workspace/app.jar"
        )
    elif build_tool == "gradle":
        build_cmd = (
            "./gradlew bootJar --no-daemon && "
            "cp \"$(find build/libs -maxdepth 1 -name '*.jar' | head -n 1)\" /workspace/app.jar"
        )
    else:
        build_cmd = (
            "if [ -f ./mvnw ]; then "
            "./mvnw -B -DskipTests package && "
            "cp \"$(find target -maxdepth 1 -name '*.jar' | head -n 1)\" /workspace/app.jar; "
            "elif [ -f ./gradlew ]; then "
            "./gradlew bootJar --no-daemon && "
            "cp \"$(find build/libs -maxdepth 1 -name '*.jar' | head -n 1)\" /workspace/app.jar; "
            "else echo 'No Maven or Gradle wrapper found' && exit 1; fi"
        )

    return (
        f"FROM eclipse-temurin:{java_major}-jdk AS build\n"
        "WORKDIR /workspace\n"
        "COPY . .\n"
        f"RUN {build_cmd}\n\n"
        f"FROM eclipse-temurin:{java_major}-jre\n"
        "WORKDIR /app\n"
        "COPY --from=build /workspace/app.jar app.jar\n"
        "EXPOSE 8080\n"
        "ENTRYPOINT [\"java\", \"-jar\", \"/app/app.jar\"]\n"
    )


def _dockerignore_content() -> str:
    return (
        ".git\n"
        ".github\n"
        ".idea\n"
        ".vscode\n"
        "build\n"
        "target\n"
        "*.iml\n"
        "*.log\n"
    )


def _github_workflow_content(build_tool: str, java_version: str) -> str:
    java_major = _java_major(java_version)

    if build_tool == "gradle":
        cache = "gradle"
        build_step = "./gradlew build --no-daemon"
    else:
        cache = "maven"
        build_step = "./mvnw -B verify"

    return (
        "name: CI\n\n"
        "on:\n"
        "  push:\n"
        "  pull_request:\n\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - uses: actions/setup-java@v4\n"
        "        with:\n"
        "          distribution: temurin\n"
        f"          java-version: '{java_major}'\n"
        f"          cache: {cache}\n"
        "      - name: Build\n"
        f"        run: {build_step}\n"
    )
