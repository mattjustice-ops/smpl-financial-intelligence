"""Print whether OpenAI settings load (no secret values). Run from backend/: python scripts/check-openai-config.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.config import _BACKEND_ROOT, clear_settings_cache, get_settings  # noqa: E402

clear_settings_cache()
s = get_settings()
secrets = _BACKEND_ROOT / "secrets.env"
print("backend_root:", _BACKEND_ROOT)
print("secrets_env_exists:", secrets.is_file())
print("env_OPENAI_API_KEY_set:", bool(os.environ.get("OPENAI_API_KEY")))
print("settings_openai_configured:", bool(s.openai_api_key))
if s.openai_api_key:
    print("key_prefix:", s.openai_api_key[:12])
