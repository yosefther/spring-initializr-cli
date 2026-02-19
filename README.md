# spring-initializr-cli

CLI to generate Spring Boot projects from [start.spring.io](https://start.spring.io).

## What You Get

- `new`: create Spring Boot projects (interactive or non-interactive)
- `list`: list live metadata (versions, types, dependencies)
- `search`: find dependencies by ID or name
- `doctor`: check runtime and connectivity
- JSON output modes for scripting
- metadata cache + offline fallback
- retry/backoff and timeout controls
- optional post-generation hooks (git, README, Docker, GitHub Actions)
- preset defaults via `.spring-init.toml`

## Requirements

- Python 3.12+
- Network access to `https://start.spring.io` (unless using cached metadata)

## Install Globally (Use From Anywhere)

Recommended (`pipx`):

```bash
pipx install .
spring-init --help
```

Upgrade later:

```bash
pipx upgrade spring-initializr-cli
```

Alternative (`pip --user`):

```bash
python3 -m pip install --user .
```

Then ensure your user scripts directory is on `PATH`.

## Local Dev Run

```bash
python3 -m spring_initializr_cli --help
python3 main.py --help
```

## Command Examples

```bash
# list metadata
spring-init list boot-versions
spring-init list dependencies

# search dependency IDs
spring-init search jpa
spring-init search security --limit 10

# create project
spring-init new --artifact-id demo --group-id com.acme --dependencies web,data-jpa,h2

# interactive mode
spring-init new --interactive

# dry-run
spring-init new --artifact-id demo --dependencies web --dry-run --show-url --print-spec text
```

## JSON Output For Scripting

`list` JSON:

```bash
spring-init list dependencies --format json
spring-init list types --format json
```

`new` JSON spec:

```bash
spring-init new \
  --artifact-id demo \
  --group-id com.acme \
  --dependencies web \
  --dry-run \
  --print-spec json
```

## Presets (`.spring-init.toml`)

If `.spring-init.toml` exists in current directory, it is loaded automatically. CLI flags override preset values.

You can start from `.spring-init.example.toml`.

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

Available on `new`, `list`, `search`, `doctor`:

- `--use-cache / --no-use-cache`
- `--refresh-metadata / --no-refresh-metadata`
- `--cache-ttl <seconds>`
- `--timeout <seconds>`
- `--retries <count>`
- `--backoff <seconds>`

## Post-Generation Hooks

Use with `new`:

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

## Project Structure

- `spring_initializr_cli/client.py`: HTTP, retries, cache, endpoint discovery
- `spring_initializr_cli/service.py`: spec defaults + validation
- `spring_initializr_cli/commands.py`: command handlers
- `spring_initializr_cli/config.py`: preset loading/merging
- `spring_initializr_cli/hooks.py`: post-generation hooks
- `spring_initializr_cli/models.py`: project spec model
- `spring_initializr_cli/cli.py`: parser + command dispatch
- `spring_initializr_cli/__main__.py`: application entrypoint
- `main.py`: compatibility entrypoint
