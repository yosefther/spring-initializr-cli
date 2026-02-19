"""Interactive prompt helpers."""


def ask(prompt: str, default: str | None = None) -> str:
    if default is None:
        return input(f"{prompt}: ").strip()

    value = input(f"{prompt} [{default}]: ").strip()
    return value or default
