"""
Gemini model selection with automatic failover.

Goal: always use the newest *stable* Gemini Flash text model the API key can
reach, and never let one bad model (retired, preview-only, out of quota) take
the app down.

How it works:
1. List the models available to this key (cached for an hour).
2. Keep only stable text Flash models: names like `gemini-3.5-flash`.
   Preview, experimental, TTS, image, audio, live and other variants are skipped.
3. Sort by parsed version number (3.10 > 3.9 > 2.5), not alphabetically.
   Then the `gemini-flash-latest` alias, then Flash-Lite models as the last
   resort (lower quality, but fast and usually available).
5. Callers try candidates in order; a model that fails is put on a cooldown
   so the next request skips it instead of paying the same error again.
6. The last model that worked is tried first ("sticky"), so users don't pay
   for failovers on every request. The preference resets whenever the model
   list is refreshed (hourly), so the newest model gets retried regularly.
7. Errors are read, not just counted (`cooldown_for_error`): a model whose
   free-tier quota is 0 is paid-only and is skipped for a day; a rate-limited
   model is skipped for exactly the retry delay Google reports. Together with
   the startup probe in `analyzer.probe_models`, this makes the app settle on
   whichever model the API key can actually use for free.

`GEMINI_MODEL` (env) pins a model to try first, e.g. for reproducible evals.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Callable, Iterable

log = logging.getLogger("career_stat_card.models")

# Stable Flash text models: "models/gemini-3.5-flash", "gemini-2.5-flash".
_STABLE_FLASH = re.compile(r"^(?:models/)?gemini-(\d+(?:\.\d+)*)-flash$")
_STABLE_FLASH_LITE = re.compile(r"^(?:models/)?gemini-(\d+(?:\.\d+)*)-flash-lite$")

# Used when the model list cannot be fetched at all.
STATIC_FALLBACKS = [
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
]

LIST_TTL_SECONDS = 3600

DAY = 24 * 60 * 60
COOLDOWN_RATE_LIMIT_DEFAULT = 15 * 60
COOLDOWN_SERVER = 5 * 60

_RETRY_DELAY = re.compile(r"retryDelay['\"]?\s*:\s*['\"](\d+(?:\.\d+)?)s")


def cooldown_for_error(status: int | None, message: str = "") -> float:
    """How long to skip a model after an API error, in seconds.

    - 429 with `limit: 0`: the model is not available on this key's tier
      (paid only), so skip it for a day.
    - 429 otherwise: rate or daily quota hit; use Google's RetryInfo delay
      (per-minute limits clear in seconds, daily ones in hours).
    - 400 / 404: retired or unsupported for this key; skip for a day.
    - 5xx, timeouts, network errors: overloaded or down; skip for 5 minutes.
    """
    message = message or ""
    if status == 429:
        if "limit: 0" in message:
            return DAY
        if m := _RETRY_DELAY.search(message):
            return min(DAY, max(30.0, float(m.group(1))))
        return COOLDOWN_RATE_LIMIT_DEFAULT
    if status in (400, 404):
        return DAY
    return COOLDOWN_SERVER


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _short(name: str) -> str:
    return name.removeprefix("models/")


def rank_models(models: Iterable[tuple[str, list[str] | None]]) -> list[str]:
    """Rank available models, best first.

    `models` is an iterable of (name, supported_actions). Pure function so it
    can be unit tested without the API.
    """
    flash: list[tuple[tuple[int, ...], str]] = []
    lite: list[tuple[tuple[int, ...], str]] = []
    names: set[str] = set()

    for name, actions in models:
        short = _short(name)
        names.add(short)
        if actions is not None and "generateContent" not in actions:
            continue
        if m := _STABLE_FLASH.match(short):
            flash.append((_version_key(m.group(1)), short))
        elif m := _STABLE_FLASH_LITE.match(short):
            lite.append((_version_key(m.group(1)), short))

    ranked = [n for _, n in sorted(flash, reverse=True)]
    if "gemini-flash-latest" in names:
        ranked.append("gemini-flash-latest")
    ranked += [n for _, n in sorted(lite, reverse=True)]
    if "gemini-flash-lite-latest" in names:
        ranked.append("gemini-flash-lite-latest")
    return ranked


class ModelSelector:
    """Thread-safe ranked model list with per-model cooldowns."""

    def __init__(
        self,
        list_models: Callable[[], Iterable[tuple[str, list[str] | None]]],
        pinned: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._list_models = list_models
        self._pinned = _short(pinned) if pinned else None
        self._clock = clock
        self._lock = threading.Lock()
        self._ranked: list[str] = []
        self._listed_at: float | None = None
        self._cooldown_until: dict[str, float] = {}
        self._preferred: str | None = None

    def _refresh_if_stale(self) -> None:
        now = self._clock()
        if self._listed_at is not None and now - self._listed_at < LIST_TTL_SECONDS:
            return
        try:
            ranked = rank_models(self._list_models())
        except Exception as exc:  # network, auth, SDK change...
            log.warning("Model listing failed (%s); using static fallbacks", exc)
            ranked = []
        self._ranked = ranked or list(STATIC_FALLBACKS)
        self._listed_at = now
        self._preferred = None
        log.info("Model candidates: %s", ", ".join(self._ranked[:5]))

    def candidates(self) -> list[str]:
        """Models to try, best first, skipping ones on cooldown.

        Never returns an empty list: if every model is cooling down, the full
        list is returned so the request still gets a chance.
        """
        with self._lock:
            self._refresh_if_stale()
            ordered = list(self._ranked)
            if self._preferred and self._preferred in ordered:
                ordered = [self._preferred] + [m for m in ordered if m != self._preferred]
            if self._pinned:
                ordered = [self._pinned] + [m for m in ordered if m != self._pinned]
            # Static fallbacks go last as a safety net in case listing was wrong.
            ordered += [m for m in STATIC_FALLBACKS if m not in ordered]
            now = self._clock()
            ready = [m for m in ordered if self._cooldown_until.get(m, 0) <= now]
            return ready or ordered

    def mark_failed(self, model: str, cooldown_seconds: float) -> None:
        with self._lock:
            self._cooldown_until[model] = self._clock() + cooldown_seconds
        log.warning("Model %s on cooldown for %ss", model, int(cooldown_seconds))

    @property
    def preferred(self) -> str | None:
        return self._preferred

    def mark_ok(self, model: str) -> None:
        with self._lock:
            self._cooldown_until.pop(model, None)
            self._preferred = model


def default_pinned_model() -> str | None:
    return os.getenv("GEMINI_MODEL") or None
