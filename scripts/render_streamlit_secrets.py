from __future__ import annotations

import os
from pathlib import Path


def _candidate_targets() -> list[Path]:
    cwd_target = Path.cwd() / ".streamlit" / "secrets.toml"
    home_target = Path.home() / ".streamlit" / "secrets.toml"
    candidates: list[Path] = []
    for candidate in (cwd_target, home_target):
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def main() -> int:
    raw_secrets = os.getenv("STREAMLIT_SECRETS_TOML", "")
    if not raw_secrets.strip():
        return 0

    last_error: Exception | None = None
    for target in _candidate_targets():
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(raw_secrets, encoding="utf-8")
            return 0
        except OSError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
