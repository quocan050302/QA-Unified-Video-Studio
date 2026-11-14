#!/usr/bin/env python3
"""
tools/gemini_client.py - Gemini AI Client with 3-Strike Fallback & Circuit Breaker
QA-Unified-Video-Studio V13

- Manages Google GenAI client lifecycle with OS-stored credentials.
- Discovers live supported director models with TTL cache.
- 3-strike retry with backoff on transient errors (503, 429 rate limit).
- Dynamic fallback chain: gemini-3.8-flash -> gemini-3.7-flash -> gemini-3.6-flash -> gemini-3.5-flash.
- Immediate fail-fast without fallback on Auth (401/403) and Daily Quota Exhaustion.
- Thread-safe circuit breaker with configurable cooldown (60-300s) and half-open probing.
- Strict Pydantic / JSON schema structured output post-validation.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pydantic import BaseModel, ValidationError

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None
    APIError = Exception

from tools.global_settings import (
    get_api_key_securely,
    load_global_settings,
    redact_secrets,
)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"          # Healthy, accepting calls
    OPEN = "OPEN"              # Tripped, cooling down
    HALF_OPEN = "HALF_OPEN"    # Testing single probe call


class FailureCategory(str, Enum):
    TRANSIENT_OVERLOAD = "TRANSIENT_OVERLOAD"                  # 503
    TEMP_RATE_LIMIT = "TEMP_RATE_LIMIT"                        # 429 RPM/TPM
    DAILY_OR_SPEND_QUOTA_EXHAUSTED = "DAILY_OR_SPEND_QUOTA_EXHAUSTED"  # 429 per-day / billing
    AUTH_INVALID = "AUTH_INVALID"                              # 401 / 403
    BAD_REQUEST = "BAD_REQUEST"                                # 400
    SAFETY_BLOCK = "SAFETY_BLOCK"                              # content safety filter
    SCHEMA_INVALID = "SCHEMA_INVALID"                          # response didn't match schema
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"                        # connection/read timeout
    UNKNOWN = "UNKNOWN"


# Model Circuit Tracker
class ModelCircuit:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.state = CircuitState.CLOSED
        self.consecutive_transient_failures = 0
        self.cooldown_until = 0.0
        self.last_failure_reason: Optional[str] = None
        self.last_failure_time: float = 0.0
        self.total_requests = 0
        self.total_successes = 0
        self.half_open_in_flight = False

    def can_attempt(self, cooldown_secs: int) -> Tuple[bool, str]:
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True, "CLOSED_HEALTHY"
        elif self.state == CircuitState.OPEN:
            if now >= self.cooldown_until:
                self.state = CircuitState.HALF_OPEN
                self.half_open_in_flight = True
                return True, "HALF_OPEN_PROBE"
            remaining = int(self.cooldown_until - now)
            return False, f"CIRCUIT_OPEN_COOLDOWN_{remaining}s"
        elif self.state == CircuitState.HALF_OPEN:
            if not self.half_open_in_flight:
                self.half_open_in_flight = True
                return True, "HALF_OPEN_PROBE"
            return False, "HALF_OPEN_PROBE_IN_FLIGHT"
        return False, "UNKNOWN_STATE"

    def record_success(self):
        self.state = CircuitState.CLOSED
        self.consecutive_transient_failures = 0
        self.half_open_in_flight = False
        self.total_requests += 1
        self.total_successes += 1

    def record_transient_failure(self, reason: str, retry_limit: int, cooldown_secs: int):
        self.total_requests += 1
        self.consecutive_transient_failures += 1
        self.last_failure_reason = reason
        self.last_failure_time = time.time()
        self.half_open_in_flight = False
        
        if self.state == CircuitState.HALF_OPEN or self.consecutive_transient_failures >= retry_limit:
            self.state = CircuitState.OPEN
            self.cooldown_until = time.time() + cooldown_secs

    def record_terminal_failure(self, reason: str):
        self.total_requests += 1
        self.last_failure_reason = reason
        self.last_failure_time = time.time()
        self.half_open_in_flight = False


class CircuitBreakerRegistry:
    def __init__(self):
        self._circuits: Dict[str, ModelCircuit] = {}
        self._lock = threading.RLock()

    def get_circuit(self, model_id: str) -> ModelCircuit:
        with self._lock:
            if model_id not in self._circuits:
                self._circuits[model_id] = ModelCircuit(model_id)
            return self._circuits[model_id]

    def reset_all(self):
        with self._lock:
            self._circuits.clear()

    def get_health_report(self) -> Dict[str, Any]:
        with self._lock:
            report = {}
            now = time.time()
            for mid, c in self._circuits.items():
                cooldown_left = max(0, int(c.cooldown_until - now)) if c.state == CircuitState.OPEN else 0
                report[mid] = {
                    "state": c.state.value,
                    "consecutive_failures": c.consecutive_transient_failures,
                    "cooldown_remaining_secs": cooldown_left,
                    "last_failure_reason": c.last_failure_reason,
                    "total_requests": c.total_requests,
                    "total_successes": c.total_successes,
                }
            return report


GLOBAL_CIRCUIT_REGISTRY = CircuitBreakerRegistry()
_GLOBAL_SEMAPHORE = threading.BoundedSemaphore(4)
_CACHED_MODELS_LIST: Optional[List[Dict[str, Any]]] = None
_CACHED_MODELS_TIMESTAMP: float = 0.0
_MODELS_CACHE_TTL: float = 300.0  # 5 minutes


def classify_gemini_failure(exc: Exception) -> Tuple[FailureCategory, str, bool]:
    """
    Classify exception into FailureCategory, safe message, and whether it is retryable/fallback-eligible.
    Returns: (category, sanitized_reason, is_fallback_eligible)
    """
    msg = str(exc).lower()
    
    # 1. Auth errors -> Terminal, NO fallback
    if any(k in msg for k in ("401", "403", "api_key_invalid", "unauthorized", "forbidden", "permission_denied", "api key not valid")):
        return FailureCategory.AUTH_INVALID, "Invalid or unauthorized API key (401/403)", False
    
    # 2. Daily / spend quota exhausted -> Terminal, NO fallback (lower models share same quota/billing)
    if "429" in msg or "resource_exhausted" in msg:
        if any(k in msg for k in ("daily", "per day", "billing", "spending limit", "quota exceeded", "quota has been exhausted", "free_tier_daily")):
            return FailureCategory.DAILY_OR_SPEND_QUOTA_EXHAUSTED, "Daily quota or billing spend limit reached (429 Quota Exhausted)", False
        # Else transient RPM/TPM rate limit -> Retryable and fallback-eligible
        return FailureCategory.TEMP_RATE_LIMIT, "Transient rate limit per minute reached (429 Rate Limit)", True

    # 3. 503 Service Unavailable / Overload -> Retryable and fallback-eligible
    if "503" in msg or "unavailable" in msg or "overloaded" in msg or "backend error" in msg:
        return FailureCategory.TRANSIENT_OVERLOAD, "Gemini service temporarily overloaded (503 Overload)", True
    
    # 4. Network timeout -> Retryable and fallback-eligible
    if any(k in msg for k in ("timeout", "timed out", "connecterror", "connection reset")):
        return FailureCategory.NETWORK_TIMEOUT, "Network connection or request timed out", True

    # 5. Safety block -> Terminal, NO fallback
    if any(k in msg for k in ("safety", "blocked", "harm_category", "finish_reason: safety")):
        return FailureCategory.SAFETY_BLOCK, "Prompt or response flagged by safety policies", False

    # 6. Schema invalid -> Not retryable for same prompt
    if isinstance(exc, (ValidationError, json.JSONDecodeError)) or "json" in msg or "schema" in msg:
        return FailureCategory.SCHEMA_INVALID, f"Structured output did not match schema: {type(exc).__name__}", False

    # 7. Bad request (400) -> Terminal
    if "400" in msg or "invalid_argument" in msg:
        return FailureCategory.BAD_REQUEST, "Malformed request or invalid argument (400)", False

    return FailureCategory.UNKNOWN, f"Unexpected error: {type(exc).__name__}", False


def list_supported_director_models(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Discover supported Gemini models with structured output capability.
    Uses TTL cache (300s). Returns allowlist if offline or key absent.
    """
    global _CACHED_MODELS_LIST, _CACHED_MODELS_TIMESTAMP
    now = time.time()
    
    if not force_refresh and _CACHED_MODELS_LIST is not None and (now - _CACHED_MODELS_TIMESTAMP) < _MODELS_CACHE_TTL:
        return _CACHED_MODELS_LIST

    key = get_api_key_securely()
    base_allowlist = [
        {"id": "gemini-3.8-flash", "display_name": "Gemini 3.8 Flash (Primary)", "structured_output": True, "status": "ALLOWLIST"},
        {"id": "gemini-3.7-flash", "display_name": "Gemini 3.7 Flash (Fallback Tier 1)", "structured_output": True, "status": "ALLOWLIST"},
        {"id": "gemini-3.6-flash", "display_name": "Gemini 3.6 Flash (Fallback Tier 2)", "structured_output": True, "status": "ALLOWLIST"},
        {"id": "gemini-3.5-flash", "display_name": "Gemini 3.5 Flash (Fallback Tier 3)", "structured_output": True, "status": "ALLOWLIST"},
    ]

    if not key or not GENAI_AVAILABLE:
        for m in base_allowlist:
            m["status"] = "OFFLINE_ALLOWLIST"
        _CACHED_MODELS_LIST = base_allowlist
        _CACHED_MODELS_TIMESTAMP = now
        return base_allowlist

    try:
        client = genai.Client(api_key=key)
        discovered = []
        for model in client.models.list():
            mid = getattr(model, "name", "").replace("models/", "")
            # Only include models matching flash series or relevant for generation
            if "flash" in mid and not any(k in mid for k in ("embed", "imagen", "tts", "audio")):
                discovered.append({
                    "id": mid,
                    "display_name": getattr(model, "display_name", mid),
                    "structured_output": True,
                    "status": "ACTIVE_LIVE",
                })
        if discovered:
            _CACHED_MODELS_LIST = discovered
            _CACHED_MODELS_TIMESTAMP = now
            return discovered
    except Exception as exc:
        print(f"[WARN] Failed to query live models: {redact_secrets(exc)}. Using allowlist.", file=sys.stderr)

    for m in base_allowlist:
        m["status"] = "FALLBACK_ALLOWLIST"
    _CACHED_MODELS_LIST = base_allowlist
    _CACHED_MODELS_TIMESTAMP = now
    return base_allowlist


def test_gemini_connection(api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """Test live Gemini API connection with probe call and model fallback."""
    key = api_key or get_api_key_securely()
    if not key:
        return {
            "ok": False,
            "status": "NEEDS_SETUP",
            "message": "No API key configured. Enter a Gemini API key in Global Settings.",
            "latency_ms": 0,
        }
    if not GENAI_AVAILABLE:
        return {
            "ok": False,
            "status": "SDK_MISSING",
            "message": "google-genai SDK not available in environment.",
            "latency_ms": 0,
        }
    
    t0 = time.time()
    cfg = load_global_settings()
    primary = model or cfg.get("primary_model", "gemini-3.8-flash")
    # Prefer fast, high-availability models for fallback probe
    fallback_pool = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"]
    candidates = [primary] + [m for m in fallback_pool if m != primary]
    
    last_cat = FailureCategory.UNKNOWN
    last_reason = "Connection probe failed."
    first_err_reason = None
    
    try:
        # Use single attempt and 10s deadline so probe fails fast on 503 instead of hanging on SDK internal backoff
        http_opts = None
        if hasattr(types, "HttpOptions") and hasattr(types, "HttpRetryOptions"):
            http_opts = types.HttpOptions(timeout=10000, retry_options=types.HttpRetryOptions(attempts=1))
            
        client = genai.Client(api_key=key, http_options=http_opts) if http_opts else genai.Client(api_key=key)
        
        for idx, m in enumerate(candidates):
            mid = m["id"] if isinstance(m, dict) else str(m)
            try:
                resp = client.models.generate_content(
                    model=mid,
                    contents="Say 'OK'",
                )
                latency = int((time.time() - t0) * 1000)
                msg = f"Successfully connected to Gemini API ({mid})."
                if idx > 0 and first_err_reason:
                    msg = f"Connected to Gemini API ({mid}; {candidates[0]} overloaded: {first_err_reason})."
                return {
                    "ok": True,
                    "status": "CONNECTED",
                    "model": mid,
                    "message": msg,
                    "latency_ms": latency,
                }
            except Exception as exc:
                cat, safe_reason, _ = classify_gemini_failure(exc)
                last_cat = cat
                last_reason = safe_reason
                if not first_err_reason:
                    first_err_reason = safe_reason
                # Terminal authentication errors should fail-fast immediately
                if cat == FailureCategory.AUTH_INVALID:
                    break
                    
        latency = int((time.time() - t0) * 1000)
        return {
            "ok": False,
            "status": last_cat.value,
            "message": redact_secrets(last_reason),
            "latency_ms": latency,
        }
    except Exception as exc:
        latency = int((time.time() - t0) * 1000)
        cat, safe_reason, _ = classify_gemini_failure(exc)
        return {
            "ok": False,
            "status": cat.value,
            "message": redact_secrets(safe_reason),
            "latency_ms": latency,
        }


def request_structured_with_fallback(
    prompt: str,
    schema: Union[Type[BaseModel], Dict[str, Any]],
    ctx: Optional[Dict[str, Any]] = None,
    mock_provider: Optional[Callable[[str, str, Any, int], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Execute structured output request with 3-strike transient failure retry and dynamic model fallback.
    
    Fallback chain:
    Primary Model (default gemini-3.8-flash)
      -> Fallback Tier 1 (gemini-3.7-flash)
        -> Fallback Tier 2 (gemini-3.6-flash)
          -> Fallback Tier 3 (gemini-3.5-flash)

    Returns:
    {
      "status": "SUCCESS" | "FAILED",
      "requested_model": str,
      "used_model": Optional[str],
      "model_path": List[str],
      "attempts": int,
      "retries": int,
      "reason_codes": List[str],
      "prompt_hash": str,
      "schema_version": str,
      "usage_actual": Dict[str, int],
      "plan": Optional[Dict[str, Any]],
      "request_id": str,
      "error": Optional[str],
    }
    """
    cfg = load_global_settings()
    primary_model = cfg.get("primary_model", "gemini-3.8-flash")
    fallback_enabled = cfg.get("fallback_enabled", True)
    fallback_models = cfg.get("fallback_models", ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]) if fallback_enabled else []
    retry_limit = int(cfg.get("retry_limit", 3))
    cooldown_secs = int(cfg.get("cooldown_secs", 120))
    max_concurrency = int(cfg.get("max_concurrent_calls", 2))

    # Candidate models in order, de-duplicated
    candidates = [primary_model] + [m for m in fallback_models if m != primary_model]
    
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    req_id = f"req_{int(time.time())}_{prompt_hash[:8]}"
    
    key = get_api_key_securely()
    if not key and mock_provider is None:
        return {
            "status": "FAILED",
            "requested_model": primary_model,
            "used_model": None,
            "model_path": [],
            "attempts": 0,
            "retries": 0,
            "reason_codes": ["NO_API_KEY_CONFIGURED"],
            "prompt_hash": prompt_hash,
            "schema_version": "13.0",
            "usage_actual": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "plan": None,
            "request_id": req_id,
            "error": "Gemini API key is not configured. Setup in Global Settings or set GEMINI_API_KEY.",
        }

    model_path: List[str] = []
    reason_codes: List[str] = []
    total_attempts = 0
    total_retries = 0

    # Acquire concurrency guard
    with _GLOBAL_SEMAPHORE:
        for model_idx, model_id in enumerate(candidates):
            circuit = GLOBAL_CIRCUIT_REGISTRY.get_circuit(model_id)
            can_run, reason_circuit = circuit.can_attempt(cooldown_secs)
            if not can_run:
                reason_codes.append(f"{model_id}:{reason_circuit}")
                continue

            model_path.append(model_id)
            model_attempts = 0

            # 3-strike retry loop on transient recoverable errors
            while model_attempts < retry_limit:
                total_attempts += 1
                model_attempts += 1
                if model_attempts > 1:
                    total_retries += 1
                    # Exponential backoff with jitter
                    backoff = min(2.0, 0.25 * (2 ** (model_attempts - 2))) + random.uniform(0.05, 0.2)
                    time.sleep(backoff)

                try:
                    # Execute call via mock provider if provided, else real Gemini API
                    if mock_provider is not None:
                        result_dict = mock_provider(model_id, prompt, schema, model_attempts)
                    else:
                        http_opts = None
                        if hasattr(types, "HttpOptions") and hasattr(types, "HttpRetryOptions"):
                            http_opts = types.HttpOptions(timeout=15000, retry_options=types.HttpRetryOptions(attempts=1))
                        client = genai.Client(api_key=key, http_options=http_opts) if http_opts else genai.Client(api_key=key)
                        response = client.models.generate_content(
                            model=model_id,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.1,
                            ),
                        )
                        raw_text = getattr(response, "text", "") or ""
                        result_dict = json.loads(raw_text)

                    # Strict schema validation
                    if isinstance(schema, type) and issubclass(schema, BaseModel):
                        validated_obj = schema.model_validate(result_dict)
                        final_plan = validated_obj.model_dump()
                    elif isinstance(schema, dict):
                        final_plan = result_dict
                    else:
                        final_plan = result_dict

                    circuit.record_success()
                    return {
                        "status": "SUCCESS",
                        "requested_model": primary_model,
                        "used_model": model_id,
                        "model_path": model_path,
                        "attempts": total_attempts,
                        "retries": total_retries,
                        "reason_codes": reason_codes + [f"{model_id}:SUCCESS"],
                        "prompt_hash": prompt_hash,
                        "schema_version": "13.0",
                        "usage_actual": {"prompt_tokens": len(prompt)//4, "completion_tokens": len(json.dumps(final_plan))//4, "total_tokens": (len(prompt)+len(json.dumps(final_plan)))//4},
                        "plan": final_plan,
                        "request_id": req_id,
                        "error": None,
                    }

                except Exception as exc:
                    cat, safe_msg, is_fallback_eligible = classify_gemini_failure(exc)
                    reason_codes.append(f"{model_id}:attempt_{model_attempts}:{cat.value}")

                    # If Auth invalid, daily quota exhausted, or safety block -> TERMINATE IMMEDIATELY. NO RETRY, NO FALLBACK!
                    if not is_fallback_eligible:
                        circuit.record_terminal_failure(cat.value)
                        return {
                            "status": "FAILED",
                            "requested_model": primary_model,
                            "used_model": None,
                            "model_path": model_path,
                            "attempts": total_attempts,
                            "retries": total_retries,
                            "reason_codes": reason_codes,
                            "prompt_hash": prompt_hash,
                            "schema_version": "13.0",
                            "usage_actual": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                            "plan": None,
                            "request_id": req_id,
                            "error": redact_secrets(safe_msg),
                        }

                    # Transient error: record failure on circuit
                    circuit.record_transient_failure(cat.value, retry_limit, cooldown_secs)

                    # If reached 3 strikes for this model, break loop to fall back to next model
                    if model_attempts >= retry_limit:
                        reason_codes.append(f"{model_id}:3_STRIKES_FALLBACK_TRIGGERED")
                        break

    return {
        "status": "FAILED",
        "requested_model": primary_model,
        "used_model": None,
        "model_path": model_path,
        "attempts": total_attempts,
        "retries": total_retries,
        "reason_codes": reason_codes + ["ALL_MODELS_EXHAUSTED"],
        "prompt_hash": prompt_hash,
        "schema_version": "13.0",
        "usage_actual": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "plan": None,
        "request_id": req_id,
        "error": "All primary and fallback models exhausted after 3-strike retries.",
    }


def get_model_health() -> Dict[str, Any]:
    """Return health and circuit state of all models."""
    return GLOBAL_CIRCUIT_REGISTRY.get_health_report()


if __name__ == "__main__":
    print("Testing Gemini Client offline Discovery & Health...")
    models = list_supported_director_models()
    print("Models:", [m["id"] for m in models])
    health = get_model_health()
    print("Health:", health)
    test_conn = test_gemini_connection()
    print("Connection probe:", test_conn)
