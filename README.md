# spring-initializr-cli

[![CI](https://github.com/yosefther/spring-initializr-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/yosefther/spring-initializr-cli/actions/workflows/ci.yml)

`spring-initializr-cli` is a production-focused command-line tool for generating Spring Boot projects from [start.spring.io](https://start.spring.io).

It is designed for both interactive use and automation (CI/scripts), with live metadata, JSON output, resilient networking, and repeatable defaults via presets.

![demo](docs/demo.gif)
<!-- TODO(yosef): record GIF -->

## Features

- Generate projects with `new` (interactive or non-interactive)
- Inspect live metadata with `list`
- Find dependencies quickly with `search`
- Validate runtime and connectivity with `doctor`
- JSON output for scripting workflows
- Metadata cache with stale fallback for offline/unstable network scenarios
- Retry/backoff and timeout controls
- Optional post-generation hooks:
  - initialize Git repository
  - create README
  - add Dockerfile and `.dockerignore`
  - add GitHub Actions workflow
- Preset configuration support via `.spring-init.toml`

## Requirements

- Python `3.12+`
- Network access to `https://start.spring.io` (unless using cached metadata)

## Installation

### Global install (recommended)

Use `pipx` to make `spring-init` available system-wide for your user:

```bash
pipx install .
spring-init --help
```

Upgrade:

```bash
pipx upgrade spring-initializr-cli
```

If `spring-init` is not found after install:

```bash
pipx ensurepath
```

Open a new terminal afterward.

### Alternative install

```bash
python3 -m pip install --user .
```

Ensure your user scripts directory is on `PATH`.

## Quick Start

```bash
# show available commands
spring-init --help

# list dependency IDs from live metadata
spring-init list dependencies

# generate a project
spring-init new \
  --artifact-id demo \
  --group-id com.acme \
  --dependencies web,data-jpa,h2
```

Run the generated app:

```bash
cd demo
./mvnw spring-boot:run
```

Or for Gradle projects:

```bash
./gradlew bootRun
```

## JSON Output (Scripting)

### `list` JSON

```bash
spring-init list dependencies --format json
spring-init list types --format json
```

### `new` spec JSON

Use dry-run mode to emit a normalized generation payload without writing files:

```bash
spring-init new \
  --artifact-id demo \
  --group-id com.acme \
  --dependencies web \
  --dry-run \
  --print-spec json
```

## Command Overview

- `spring-init new`
  - generate Spring Boot project archives
  - supports `--interactive`, `--dry-run`, `--show-url`, `--print-spec`
- `spring-init list <section>`
  - sections: `boot-versions`, `java-versions`, `types`, `languages`, `packaging`, `dependencies`
- `spring-init search <query>`
  - dependency search by ID or name
- `spring-init doctor`
  - checks Python version, launcher availability, Git, cache state, and live API reachability

## Presets (`.spring-init.toml`)

If a `.spring-init.toml` exists in the current directory, it is loaded automatically.  
CLI arguments always take precedence over preset values.

Start from `.spring-init.example.toml`.

Example:

```toml
[defaults]
group-id = "com.acme"
artifact-id = "demo"
java-version = "21"
dependencies = ["web", "actuator"]
use-cache = true
cache-ttl = 43200

[new]
init-readme = true
add-docker = true
add-github-actions = true
print-spec = "text"

[list]
format = "json"
```

Use a specific preset file:

```bash
spring-init new --preset ./my-team.toml
```

## Runtime Controls

Available on `new`, `list`, `search`, and `doctor`:

- `--use-cache / --no-use-cache`
- `--refresh-metadata / --no-refresh-metadata`
- `--cache-ttl <seconds>`
- `--timeout <seconds>`
- `--retries <count>`
- `--backoff <seconds>`

## Post-Generation Hooks

`new` supports:

- `--git-init`
- `--init-readme`
- `--add-docker`
- `--add-github-actions`

## Development

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Compile check:

```bash
python3 -m compileall main.py spring_initializr_cli tests
```

CI workflow: `.github/workflows/ci.yml`

## Architecture

- `spring_initializr_cli/client.py`: HTTP client, retry/backoff, cache, endpoint discovery
- `spring_initializr_cli/service.py`: project spec defaults and validation
- `spring_initializr_cli/commands.py`: command handlers (`new`, `list`, `search`, `doctor`)
- `spring_initializr_cli/config.py`: preset loading and argument merge rules
- `spring_initializr_cli/hooks.py`: optional post-generation project automation
- `spring_initializr_cli/models.py`: domain model (`ProjectSpec`)
- `spring_initializr_cli/cli.py`: parser and command dispatch
- `spring_initializr_cli/__main__.py`: process entrypoint and top-level error handling
- `main.py`: compatibility entrypoint

## License

MIT. See [LICENSE](LICENSE).
