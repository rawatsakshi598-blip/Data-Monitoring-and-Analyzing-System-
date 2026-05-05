"""
Test: config.py
Verifies configuration loads correctly from env vars and defaults.
"""

import os
import sys
import importlib

# Add parent dir to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config as cfg_module


def test_default_config():
    """Config should have sensible defaults without any env vars."""
    for key in [
        "DATABASE_URL",
        "LLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "SERVER_PORT",
    ]:
        os.environ.pop(key, None)

    importlib.reload(cfg_module)
    c = cfg_module.Config()

    assert c.db.url is not None
    assert "sqlite" in c.db.url.lower()
    assert c.llm.base_url == "https://api.openai.com/v1"
    assert c.llm.model == "gpt-4o-mini"
    assert c.llm.max_tokens == 2000
    assert c.llm.temperature == 0.1
    assert c.server.port == 3001
    assert c.server.host == "0.0.0.0"
    assert "*" in c.server.cors_origins


def test_config_from_env():
    """Config should read from environment variables."""
    os.environ["LLM_BASE_URL"] = "https://api.groq.com/openai/v1"
    os.environ["LLM_API_KEY"] = "gsk-test123"
    os.environ["LLM_MODEL"] = "llama-3.1-70b"
    os.environ["SERVER_PORT"] = "4000"

    importlib.reload(cfg_module)
    c = cfg_module.Config.from_env()

    assert c.llm.base_url == "https://api.groq.com/openai/v1"
    assert c.llm.api_key == "gsk-test123"
    assert c.llm.model == "llama-3.1-70b"
    assert c.server.port == 4000

    for key in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "SERVER_PORT"]:
        os.environ.pop(key, None)


def test_db_path_points_to_custom_db():
    """Default DB path should point to db/custom.db."""
    c = cfg_module.Config()
    assert "custom.db" in c.db.url


def test_llm_temperature_range():
    """Temperature should be between 0 and 2."""
    c = cfg_module.Config()
    assert 0 <= c.llm.temperature <= 2
