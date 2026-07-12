"""Application settings loaded from environment variables."""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# --- Auto-bootstrap .env -------------------------------------------------
# If .env is missing, auto-create it from .env.example on first run.
# This eliminates the "forgot to copy .env.example" problem permanently.
_env_path = Path(__file__).resolve().parent.parent / ".env"
_env_example = _env_path.with_suffix(".env.example")

if not _env_path.exists() and _env_example.exists():
    _env_path.write_text(_env_example.read_text())
    print(f"[settings] Created {_env_path} from {_env_example.name}", file=sys.stderr)
elif not _env_path.exists() and not _env_example.exists():
    print(
        f"[settings] WARNING: Neither {_env_path.name} nor {_env_example.name} found. "
        "Create one of them with your Supabase keys.",
        file=sys.stderr,
    )

# Load .env file from the backend directory
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


@dataclass
class Settings:
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # CORS
    cors_origins: list = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","))


settings = Settings()