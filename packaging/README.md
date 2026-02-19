# Distribution Manifests

This folder contains templates to publish `spring-init` through package managers.

## Files

- `homebrew/spring-init.rb`: Homebrew formula template
- `scoop/spring-init.json`: Scoop manifest template
- `winget/spring-initializr-cli.template.yaml`: winget manifest template

## Release workflow

1. Build a release archive (zip/tar.gz) from a tagged version.
2. Compute SHA256 for the archive.
3. Replace placeholders in template files:
   - `__VERSION__`
   - `__URL__`
   - `__SHA256__`
4. Publish manifests to the respective package-manager repositories.
