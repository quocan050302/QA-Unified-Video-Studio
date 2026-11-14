#!/usr/bin/env python3
"""
tools/global_settings.py - Global Studio Configuration & OS Secret Storage
QA-Unified-Video-Studio V13

- Manages studio-wide settings stored in .studio/global_settings.json (metadata only).
- Securely stores API keys in OS credential store (Keyring / Windows Credential Manager).
- Never writes plaintext API keys to JSON, .env, localStorage, or project configs.
- Redacts secrets from logs, exceptions, and response payloads.
"""

from __future__ import annotations

import abc
import json
import os
import re
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
STUDIO_DIR = ROOT_DIR / ".studio"
GLOBAL_SETTINGS_FILE = STUDIO_DIR / "global_settings.json"

SERVICE_NAME = "QAUnifiedVideoStudio"
KEY_USERNAME = "gemini_api_key"

_SETTINGS_LOCK = threading.RLock()


# ===============================================================================
# SecretStore Protocol & Concrete Implementations (V14 Test Isolation)
# ===============================================================================

class SecretStore(abc.ABC):
    """Abstract protocol for secure credential storage."""

    @abc.abstractmethod
    def get_key(self) -> Optional[str]:
        """Retrieve stored secret key."""
        pass

    @abc.abstractmethod
    def set_key(self, key: str) -> str:
        """
        Store secret key.
        Returns 'DURABLE_STORED' on verified persistence, or 'STORE_FAILED'.
        """
        pass

    @abc.abstractmethod
    def delete_key(self) -> bool:
        """Delete stored secret key. Returns True if deleted."""
        pass

    @abc.abstractmethod
    def probe(self) -> bool:
        """Check if credential is configured and accessible."""
        pass

    @abc.abstractmethod
    def describe_source(self) -> str:
        """Describe storage backend: 'keyring', 'in_memory', 'env', 'none'."""
        pass


class OSKeyringSecretStore(SecretStore):
    """Production secret store backed by OS Credential Manager / Keyring."""

    def __init__(self, service_name: str = SERVICE_NAME, username: str = KEY_USERNAME):
        self.service_name = service_name
        self.username = username

    def _check_test_mode_guard(self) -> None:
        """Prevent tests from accidentally touching production credentials."""
        if os.environ.get("QA_STUDIO_TEST_MODE") == "1" and self.service_name == SERVICE_NAME:
            raise RuntimeError(
                "LIVE_CREDENTIAL_ACCESS_FORBIDDEN: Attempted to access production credentials in test mode! "
                "Use InMemorySecretStore or an isolated service name in tests."
            )

    def get_key(self) -> Optional[str]:
        self._check_test_mode_guard()
        try:
            import keyring
            val = keyring.get_password(self.service_name, self.username)
            if val and val.strip():
                return val.strip()
        except Exception:
            pass

        # Ephemeral env fallback (read-only external configuration, never mutated by store)
        env_val = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_val:
            return env_val
        return None

    def set_key(self, key: str) -> str:
        self._check_test_mode_guard()
        if not isinstance(key, str) or not key.strip():
            raise ValueError("API key must be a non-empty string.")

        clean_key = key.strip()
        try:
            import keyring
            keyring.set_password(self.service_name, self.username, clean_key)
            # Verify readback persistence immediately
            probe_val = keyring.get_password(self.service_name, self.username)
            if probe_val == clean_key:
                return "DURABLE_STORED"
            return "STORE_FAILED"
        except Exception as exc:
            print(f"[WARN] OS keyring store failed: {exc}.", file=sys.stderr)
            # V14 P0-A requirement: DO NOT silently write key into os.environ while claiming success!
            return "STORE_FAILED"

    def delete_key(self) -> bool:
        self._check_test_mode_guard()
        deleted = False
        try:
            import keyring
            try:
                keyring.delete_password(self.service_name, self.username)
                deleted = True
            except Exception:
                pass
        except Exception:
            pass

        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
            deleted = True
        return deleted

    def probe(self) -> bool:
        k = self.get_key()
        return bool(k and len(k) >= 10)

    def describe_source(self) -> str:
        self._check_test_mode_guard()
        try:
            import keyring
            val = keyring.get_password(self.service_name, self.username)
            if val and val.strip():
                return "keyring"
        except Exception:
            pass
        if os.environ.get("GEMINI_API_KEY", "").strip():
            return "env"
        return "none"


class InMemorySecretStore(SecretStore):
    """Completely isolated in-memory secret store for testing."""

    def __init__(self, initial_key: Optional[str] = None):
        self._key: Optional[str] = initial_key.strip() if initial_key else None

    def get_key(self) -> Optional[str]:
        return self._key

    def set_key(self, key: str) -> str:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("API key must be a non-empty string.")
        self._key = key.strip()
        return "DURABLE_STORED"

    def delete_key(self) -> bool:
        if self._key is not None:
            self._key = None
            return True
        return False

    def probe(self) -> bool:
        return bool(self._key and len(self._key) >= 10)

    def describe_source(self) -> str:
        return "in_memory" if self._key else "none"


class TestKeyringSecretStore(OSKeyringSecretStore):
    """Temporary OS keyring secret store with unique namespaced service name for integration tests."""

    def __init__(self, test_service_name: str, test_username: str = "test_key"):
        if test_service_name == SERVICE_NAME:
            raise ValueError("Test service name cannot equal production SERVICE_NAME!")
        super().__init__(service_name=test_service_name, username=test_username)

    def _check_test_mode_guard(self) -> None:
        # Isolated test service name is permitted in test mode
        pass


# Active secret store instance (delegated by module functions)
_ACTIVE_SECRET_STORE: SecretStore = OSKeyringSecretStore()
_STORE_LOCK = threading.RLock()


def get_active_secret_store() -> SecretStore:
    """Retrieve currently active SecretStore backend."""
    with _STORE_LOCK:
        return _ACTIVE_SECRET_STORE


def set_active_secret_store(store: SecretStore) -> None:
    """Inject SecretStore backend (used for test isolation)."""
    with _STORE_LOCK:
        global _ACTIVE_SECRET_STORE
        _ACTIVE_SECRET_STORE = store


class isolated_secret_store:
    """Context manager to run code within an isolated SecretStore backend."""

    def __init__(self, store: Optional[SecretStore] = None):
        self.new_store = store or InMemorySecretStore()
        self.old_store = None

    def __enter__(self) -> SecretStore:
        with _STORE_LOCK:
            self.old_store = get_active_secret_store()
            set_active_secret_store(self.new_store)
            return self.new_store

    def __exit__(self, exc_type, exc_val, exc_tb):
        with _STORE_LOCK:
            if self.old_store is not None:
                set_active_secret_store(self.old_store)

SUPPORTED_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

DEFAULT_SETTINGS: Dict[str, Any] = {
    "version": "13.0",
    "provider": "gemini",
    "primary_model": "gemini-3.8-flash",
    "fallback_models": ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"],
    "fallback_enabled": True,
    "retry_limit": 3,
    "cooldown_secs": 120,
    "max_concurrent_calls": 2,
    "ai_director_enabled": True,
    "budgets": {
        "token_budget_monthly": 1_000_000,
        "tokens_used": 0,
    },
    "sfx_sources_status": {
        "real_sfx_count": 0,
        "licenses_count": 0,
        "procedural_fallback_active": True,
    },
}

PUBLIC_WHITELIST_KEYS = {
    "version",
    "provider",
    "primary_model",
    "fallback_models",
    "fallback_enabled",
    "retry_limit",
    "cooldown_secs",
    "max_concurrent_calls",
    "ai_director_enabled",
    "budgets",
    "sfx_sources_status",
}

# Regex patterns for secret redaction
_SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    re.compile(r"(?i)(?:key|token|secret|password|authorization)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{12,}"),
    re.compile(r"[?&]key=[A-Za-z0-9_\-\.]{10,}"),
]


def redact_secrets(obj: Any) -> Any:
    """Recursively scrub API keys, bearer tokens, and secrets from dict, list, string, or Exception."""
    if isinstance(obj, str):
        redacted = obj
        for pattern in _SECRET_PATTERNS:
            def _replace_match(m: re.Match) -> str:
                full = m.group(0)
                if full.lower().startswith("bearer "):
                    return "Bearer [REDACTED_SECRET]"
                if "key=" in full.lower():
                    return full.split("key=")[0] + "key=[REDACTED_SECRET]"
                return "[REDACTED_SECRET]"
            redacted = pattern.sub(_replace_match, redacted)
        return redacted
    elif isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in ("key", "secret", "password", "token", "auth")):
                if isinstance(v, str) and v:
                    out[k] = "[REDACTED_SECRET]"
                else:
                    out[k] = redact_secrets(v)
            else:
                out[k] = redact_secrets(v)
        return out
    elif isinstance(obj, list):
        return [redact_secrets(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(redact_secrets(item) for item in obj)
    elif isinstance(obj, Exception):
        return type(obj)(redact_secrets(str(obj)))
    return obj


def validate_global_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize global settings dict."""
    cleaned = dict(config)
    
    # Primary model
    primary = cleaned.get("primary_model", DEFAULT_SETTINGS["primary_model"])
    if not isinstance(primary, str) or not primary.strip():
        primary = DEFAULT_SETTINGS["primary_model"]
    cleaned["primary_model"] = primary.strip()
    
    # Fallback models
    fallbacks = cleaned.get("fallback_models", DEFAULT_SETTINGS["fallback_models"])
    if not isinstance(fallbacks, list):
        fallbacks = list(DEFAULT_SETTINGS["fallback_models"])
    cleaned["fallback_models"] = [str(m).strip() for m in fallbacks if str(m).strip() and str(m).strip() != cleaned["primary_model"]][:5]
    
    # Fallback enabled
    cleaned["fallback_enabled"] = bool(cleaned.get("fallback_enabled", True))
    
    # Retry limit: bounded [1, 5], default 3
    retry_limit = cleaned.get("retry_limit", 3)
    try:
        retry_limit = int(retry_limit)
        retry_limit = max(1, min(5, retry_limit))
    except (ValueError, TypeError):
        retry_limit = 3
    cleaned["retry_limit"] = retry_limit
    
    # Cooldown seconds: bounded [60, 300], default 120
    cooldown = cleaned.get("cooldown_secs", 120)
    try:
        cooldown = int(cooldown)
        cooldown = max(60, min(300, cooldown))
    except (ValueError, TypeError):
        cooldown = 120
    cleaned["cooldown_secs"] = cooldown
    
    # Max concurrent calls: bounded [1, 4], default 2
    concurrency = cleaned.get("max_concurrent_calls", 2)
    try:
        concurrency = int(concurrency)
        concurrency = max(1, min(4, concurrency))
    except (ValueError, TypeError):
        concurrency = 2
    cleaned["max_concurrent_calls"] = concurrency
    
    # AI Director enabled
    cleaned["ai_director_enabled"] = bool(cleaned.get("ai_director_enabled", True))
    
    # Budgets
    budgets = cleaned.get("budgets", {})
    if not isinstance(budgets, dict):
        budgets = dict(DEFAULT_SETTINGS["budgets"])
    cleaned["budgets"] = {
        "token_budget_monthly": max(0, int(budgets.get("token_budget_monthly", 1_000_000))),
        "tokens_used": max(0, int(budgets.get("tokens_used", 0))),
    }
    
    return cleaned


def load_global_settings() -> Dict[str, Any]:
    """Load studio settings from .studio/global_settings.json, merging with defaults."""
    with _SETTINGS_LOCK:
        STUDIO_DIR.mkdir(parents=True, exist_ok=True)
        if not GLOBAL_SETTINGS_FILE.exists():
            cfg = dict(DEFAULT_SETTINGS)
            save_global_settings(cfg)
            return cfg
        try:
            with open(GLOBAL_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return validate_global_settings(merged)
        except Exception as exc:
            print(f"[WARN] Failed to read {GLOBAL_SETTINGS_FILE}: {exc}. Using defaults.", file=sys.stderr)
            return dict(DEFAULT_SETTINGS)


def save_global_settings(config: Dict[str, Any]) -> bool:
    """Save whitelisted non-secret metadata atomically to .studio/global_settings.json."""
    with _SETTINGS_LOCK:
        STUDIO_DIR.mkdir(parents=True, exist_ok=True)
        validated = validate_global_settings(config)
        
        # Strictly whitelist public keys to guarantee NO API keys are written to disk
        filtered = {k: validated[k] for k in PUBLIC_WHITELIST_KEYS if k in validated}
        # Double check no secret patterns exist in JSON
        json_str = json.dumps(filtered, indent=2, ensure_ascii=False)
        for pattern in _SECRET_PATTERNS:
            if pattern.search(json_str):
                raise ValueError("Security violation: Attempted to save secret to global_settings.json!")
        
        # Atomic write
        temp_fd, temp_path = tempfile.mkstemp(dir=STUDIO_DIR, prefix="settings_", suffix=".tmp")
        try:
            with open(temp_fd, "w", encoding="utf-8") as f:
                f.write(json_str)
            os.replace(temp_path, GLOBAL_SETTINGS_FILE)
            return True
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise


def store_api_key_securely(key: str) -> bool:
    """Store Gemini API key in active SecretStore. Returns True ONLY on durable storage."""
    store = get_active_secret_store()
    res = store.set_key(key)
    return res == "DURABLE_STORED"


def store_api_key_with_status(key: str) -> Dict[str, Any]:
    """Store Gemini API key, returning status code and backend description."""
    store = get_active_secret_store()
    status = store.set_key(key)
    return {
        "status": status,
        "durable": (status == "DURABLE_STORED"),
        "backend": store.describe_source(),
    }


def get_api_key_securely() -> Optional[str]:
    """Retrieve Gemini API key from active SecretStore."""
    return get_active_secret_store().get_key()


def delete_api_key_securely() -> bool:
    """Delete Gemini API key from active SecretStore."""
    return get_active_secret_store().delete_key()


def get_global_settings_public() -> Dict[str, Any]:
    """
    Return sanitized public settings dictionary suitable for HTTP GET response.
    NEVER returns the raw API key.
    """
    cfg = load_global_settings()
    store = get_active_secret_store()
    has_key = store.probe()
    key_source = store.describe_source()
    
    # Count real SFX assets and licenses
    sfx_dir = ROOT_DIR / "audio" / "real_sfx"
    licenses_dir = ROOT_DIR / "audio" / "licenses"
    real_count = len(list(sfx_dir.glob("*.wav"))) if sfx_dir.exists() else 0
    lic_count = len(list(licenses_dir.glob("*.json"))) if licenses_dir.exists() else 0
    
    return {
        "has_key": has_key,
        "key_configured": has_key,
        "key_source": key_source,
        "provider": cfg.get("provider", "gemini"),
        "primary_model": cfg.get("primary_model", "gemini-3.8-flash"),
        "fallback_models": cfg.get("fallback_models", ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]),
        "fallback_enabled": cfg.get("fallback_enabled", True),
        "retry_limit": cfg.get("retry_limit", 3),
        "cooldown_secs": cfg.get("cooldown_secs", 120),
        "max_concurrent_calls": cfg.get("max_concurrent_calls", 2),
        "ai_director_enabled": cfg.get("ai_director_enabled", True),
        "budgets": cfg.get("budgets", {}),
        "sfx_sources_status": {
            "real_sfx_count": real_count,
            "licenses_count": lic_count,
            "procedural_fallback_active": True,
        },
    }


if __name__ == "__main__":
    pub = get_global_settings_public()
    print("Public Global Settings:")
    print(json.dumps(pub, indent=2))
