"""Resolve OPENAI_API_KEY from the environment or a repo-local .env file.

Convention: never commit API keys. Use one of:
  - Environment variable OPENAI_API_KEY (recommended for CI and shells)
  - A file named .env in the repo root with a line: OPENAI_API_KEY=sk-...
    (.env is gitignored)
"""
from __future__ import annotations

import os
from pathlib import Path


def load_openai_api_key(*, base_dir: Path) -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if key:
        return key
    env_path = base_dir / ".env"
    if not env_path.is_file():
        return ""
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() != "OPENAI_API_KEY":
            continue
        return value.strip().strip('"').strip("'")
    return ""
