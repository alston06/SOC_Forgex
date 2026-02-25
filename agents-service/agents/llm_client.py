"""LLM client with caching and OpenRouter/OpenAI support."""
import hashlib
import json
import time
from typing import Any, Dict, Optional
import httpx
import structlog

from .crewai.config import settings

logger = structlog.get_logger(__name__)

# Simple in-memory cache for LLM responses
_llm_cache: Dict[str, tuple[Any, float]] = {}
_cache_hits = 0
_cache_misses = 0


def _cache_key(prompt: str, model: str, temperature: float) -> str:
    """Generate cache key from prompt and parameters."""
    key_str = f"{model}:{temperature}:{prompt}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]


def _clean_cache() -> None:
    """Clean expired cache entries."""
    global _llm_cache, _cache_hits, _cache_misses
    current_time = time.time()
    ttl = settings.llm_cache_ttl_seconds

    to_remove = []
    for key, (response, timestamp) in _llm_cache.items():
        if current_time - timestamp > ttl:
            to_remove.append(key)

    for key in to_remove:
        del _llm_cache[key]

    if to_remove:
        logger.info("Cleaned expired cache entries", count=len(to_remove))


async def call_llm(
    prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    skip_cache: bool = False,
) -> str:
    """Call LLM with caching support.

    Args:
        prompt: The prompt to send to the LLM
        model: Model name (defaults to settings.llm_model)
        temperature: Temperature (defaults to settings.llm_temperature)
        max_tokens: Max tokens (defaults to settings.llm_max_tokens)
        skip_cache: If True, bypass the cache

    Returns:
        LLM response text
    """
    global _cache_hits, _cache_misses

    # Use defaults from settings
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature
    max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

    # Check cache first
    if settings.llm_cache_enabled and not skip_cache:
        key = _cache_key(prompt, model, temperature)
        _clean_cache()

        if key in _llm_cache:
            response, _ = _llm_cache[key]
            _cache_hits += 1
            logger.debug(
                "LLM cache hit",
                model=model,
                cache_hits=_cache_hits,
                cache_misses=_cache_misses,
            )
            return response

    _cache_misses += 1

    # Determine API base URL and headers
    if settings.llm_provider == "openrouter":
        api_base = settings.llm_api_base
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://soc-forgex.local",  # Required by OpenRouter
        }
    else:  # openai
        api_base = "https://api.openai.com/v1"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    # Make API call
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a security analyst providing detailed analysis."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data["choices"][0]["message"]["content"]

            logger.info(
                "LLM API call successful",
                model=model,
                provider=settings.llm_provider,
                prompt_length=len(prompt),
                response_length=len(response_text),
                cache_hits=_cache_hits,
                cache_misses=_cache_misses,
            )

            # Cache the response
            if settings.llm_cache_enabled and not skip_cache:
                key = _cache_key(prompt, model, temperature)
                _llm_cache[key] = (response_text, time.time())

            return response_text

        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM API call failed",
                status_code=e.response.status_code,
                response=e.response.text,
            )
            raise
        except Exception as e:
            logger.error("LLM API call error", error=str(e))
            raise


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    total = _cache_hits + _cache_misses
    hit_rate = (_cache_hits / total * 100) if total > 0 else 0
    return {
        "cache_hits": _cache_hits,
        "cache_misses": _cache_misses,
        "hit_rate_percent": round(hit_rate, 2),
        "cache_entries": len(_llm_cache),
    }


def clear_cache() -> None:
    """Clear all cached LLM responses."""
    global _llm_cache, _cache_hits, _cache_misses
    count = len(_llm_cache)
    _llm_cache.clear()
    _cache_hits = 0
    _cache_misses = 0
    logger.info("LLM cache cleared", entries=count)
