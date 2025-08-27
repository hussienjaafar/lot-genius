"""
Cache metrics registry for tracking cache performance across the application.

Provides simple counters and metrics collection with optional emission in API results.
"""

import os
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class CacheStats:
    """Cache statistics for a specific cache."""

    hits: int = 0
    misses: int = 0
    stores: int = 0
    evictions: int = 0

    @property
    def hit_ratio(self) -> float:
        """Calculate cache hit ratio."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_operations(self) -> int:
        """Total cache operations."""
        return self.hits + self.misses + self.stores + self.evictions


class CacheMetricsRegistry:
    """Thread-safe registry for cache metrics across the application."""

    def __init__(self):
        self._stats: Dict[str, CacheStats] = defaultdict(CacheStats)
        self._lock = threading.Lock()

    def record_hit(self, cache_name: str) -> None:
        """Record a cache hit."""
        with self._lock:
            self._stats[cache_name].hits += 1

    def record_miss(self, cache_name: str) -> None:
        """Record a cache miss."""
        with self._lock:
            self._stats[cache_name].misses += 1

    def record_store(self, cache_name: str) -> None:
        """Record a cache store operation."""
        with self._lock:
            self._stats[cache_name].stores += 1

    def record_eviction(self, cache_name: str) -> None:
        """Record a cache eviction."""
        with self._lock:
            self._stats[cache_name].evictions += 1

    def get_stats(self, cache_name: str) -> CacheStats:
        """Get stats for a specific cache."""
        with self._lock:
            return CacheStats(**asdict(self._stats[cache_name]))

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all cache statistics."""
        with self._lock:
            result = {}
            for name, stats in self._stats.items():
                result[name] = {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "stores": stats.stores,
                    "evictions": stats.evictions,
                    "hit_ratio": stats.hit_ratio,
                    "total_operations": stats.total_operations,
                }
            return result

    def reset_stats(self, cache_name: Optional[str] = None) -> None:
        """Reset statistics for a specific cache or all caches."""
        with self._lock:
            if cache_name:
                self._stats[cache_name] = CacheStats()
            else:
                self._stats.clear()


# Global registry instance
_registry = CacheMetricsRegistry()


def get_registry() -> CacheMetricsRegistry:
    """Get the global cache metrics registry."""
    return _registry


def should_emit_metrics() -> bool:
    """Check if cache metrics should be emitted in API responses."""
    return os.getenv("CACHE_METRICS", "0").lower() in ("1", "true", "yes", "on")


def record_cache_hit(cache_name: str) -> None:
    """Convenience function to record a cache hit."""
    _registry.record_hit(cache_name)


def record_cache_miss(cache_name: str) -> None:
    """Convenience function to record a cache miss."""
    _registry.record_miss(cache_name)


def record_cache_store(cache_name: str) -> None:
    """Convenience function to record a cache store."""
    _registry.record_store(cache_name)


def record_cache_eviction(cache_name: str) -> None:
    """Convenience function to record a cache eviction."""
    _registry.record_eviction(cache_name)


def get_cache_stats(cache_name: str) -> Dict[str, Any]:
    """Get cache statistics as a dictionary."""
    stats = _registry.get_stats(cache_name)
    return {
        "hits": stats.hits,
        "misses": stats.misses,
        "stores": stats.stores,
        "evictions": stats.evictions,
        "hit_ratio": stats.hit_ratio,
        "total_operations": stats.total_operations,
    }


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """Get all cache statistics."""
    return _registry.get_all_stats()
