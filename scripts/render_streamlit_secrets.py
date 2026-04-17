from __future__ import annotations

import os
from pathlib import Path


def main() -> int:
    raw_secrets = os.getenv("STREAMLIT_SECRETS_TOML", "")
    if not raw_secrets.strip():
        return 0

    target = Path.home() / ".streamlit" / "secrets.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(raw_secrets, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
