from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from .cache_metrics import (
    record_cache_eviction,
    record_cache_hit,
    record_cache_miss,
    record_cache_store,
    should_emit_metrics,
)
from .config import settings

# Simple file cache (sqlite) with TTL
_DB_PATH = Path("data/cache/keepa_cache.sqlite")
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


def _db():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
        k TEXT PRIMARY KEY,
        v TEXT NOT NULL,
        ts INTEGER NOT NULL
    )"""
    )
    # Add index on timestamp for efficient TTL scanning
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(ts);")
    return conn


def _cache_get(key: str, ttl_sec: int) -> Optional[dict]:
    with _lock:
        conn = _db()
        cur = conn.execute("SELECT v, ts FROM cache WHERE k = ?", (key,))
        row = cur.fetchone()
        conn.close()
    if not row:
        record_cache_miss("keepa")
        return None
    v, ts = row
    if int(time.time()) - ts > ttl_sec:
        record_cache_miss("keepa")
        # Optional: Clean up expired entries
        _cleanup_expired(key, ttl_sec)
        return None
    record_cache_hit("keepa")
    try:
        return json.loads(v)
    except Exception:
        record_cache_miss("keepa")
        return None


def _cache_set(key: str, payload: dict):
    with _lock:
        conn = _db()
        conn.execute(
            "INSERT OR REPLACE INTO cache (k, v, ts) VALUES (?, ?, ?)",
            (key, json.dumps(payload), int(time.time())),
        )
        conn.commit()
        conn.close()
    record_cache_store("keepa")


def _cleanup_expired(current_key: str, ttl_sec: int) -> None:
    """Clean up expired cache entries."""
    try:
        with _lock:
            conn = _db()
            cutoff_time = int(time.time()) - ttl_sec
            cursor = conn.execute("DELETE FROM cache WHERE ts < ?", (cutoff_time,))
            evicted_count = cursor.rowcount
            conn.commit()
            conn.close()
            if evicted_count > 0:
                # Record evictions for the cleaned up entries
                for _ in range(evicted_count):
                    record_cache_eviction("keepa")
    except Exception:
        pass  # Ignore cleanup errors


@dataclass
class KeepaConfig:
    api_key: str
    domain: int = 1  # 1 = US
    timeout_sec: int = 20
    ttl_days: int = 7
    ttl_sec: Optional[int] = None  # Override for tests
    backoff_initial: float = 0.7
    backoff_max: float = 8.0
    max_retries: int = 3


class KeepaClient:
    def __init__(self, cfg: Optional[KeepaConfig] = None):
        api_key = settings.KEEPA_API_KEY or ""
        if cfg is None:
            # Check for test TTL override via environment
            ttl_sec_override = os.getenv("KEEPA_CACHE_TTL_SEC")
            cfg = KeepaConfig(
                api_key=api_key,
                domain=1,
                timeout_sec=20,
                ttl_days=settings.KEEPA_CACHE_TTL_DAYS,
                ttl_sec=int(ttl_sec_override) if ttl_sec_override else None,
            )
        self.cfg = cfg
        self.session = requests.Session()

        # Eager DB init to ensure file exists and PRAGMAs are applied
        try:
            conn = _db()
            conn.close()
        except Exception:
            pass

    def _get(self, url: str, params: dict, cache_key: str) -> dict:
        # Use ttl_sec override if provided, otherwise use ttl_days
        ttl = (
            self.cfg.ttl_sec
            if self.cfg.ttl_sec is not None
            else int(self.cfg.ttl_days * 86400)
        )
        cached = _cache_get(cache_key, ttl)
        if cached is not None:
            result = {"ok": True, "cached": True, "data": cached}
            if should_emit_metrics():
                from .cache_metrics import get_cache_stats

                result["cache_stats"] = get_cache_stats("keepa")
            return result

        # retry with backoff
        delay = self.cfg.backoff_initial
        for attempt in range(self.cfg.max_retries):
            try:
                resp = self.session.get(
                    url, params=params, timeout=self.cfg.timeout_sec
                )
                if resp.status_code == 200:
                    data = resp.json()
                    _cache_set(cache_key, data)
                    result = {"ok": True, "cached": False, "data": data}
                    if should_emit_metrics():
                        from .cache_metrics import get_cache_stats

                        result["cache_stats"] = get_cache_stats("keepa")
                    return result
                # throttle/429 or temporary server errors → backoff
                if resp.status_code in (429, 502, 503, 504):
                    time.sleep(delay)
                    delay = min(self.cfg.backoff_max, delay * 2)
                    continue
                # hard error
                return {"ok": False, "status": resp.status_code, "error": resp.text}
            except requests.RequestException:
                time.sleep(delay)
                delay = min(self.cfg.backoff_max, delay * 2)
        return {"ok": False, "error": "request failed after retries"}

    def lookup_by_code(self, code: str) -> dict:
        """
        Resolves UPC/EAN/ASIN via Keepa /product endpoint.
        Returns {'ok':bool, 'cached':bool, 'data':raw_json or None}
        """
        if not self.cfg.api_key:
            return {"ok": False, "error": "KEEPA_API_KEY not set"}
        url = "https://api.keepa.com/product"
        params = {
            "key": self.cfg.api_key,
            "domain": self.cfg.domain,
            "code": code,
            "stats": 0,  # lighter payload; we just need ASIN and basic meta in this step
        }
        return self._get(url, params, cache_key=f"product:{self.cfg.domain}:{code}")

    def search_by_title(self, query: str) -> dict:
        """
        OPTIONAL/Stub: For now, we call the same product endpoint with 'product' search disabled
        (Keepa has different endpoints; we keep this as a placeholder to avoid scope creep).
        For Step 5, return a consistent 'not implemented' structure.
        """
        return {
            "ok": True,
            "cached": True,
            "data": {"products": [], "note": "title-search stub"},
        }

    def fetch_stats_by_code(self, code: str) -> dict:
        """Get Keepa product payload with stats=1 using UPC/EAN code."""
        if not self.cfg.api_key:
            return {"ok": False, "error": "KEEPA_API_KEY not set"}
        url = "https://api.keepa.com/product"
        params = {
            "key": self.cfg.api_key,
            "domain": self.cfg.domain,
            "code": code,
            "stats": 1,
        }
        return self._get(
            url, params, cache_key=f"product_stats:code:{self.cfg.domain}:{code}"
        )

    def fetch_stats_by_asin(self, asin: str) -> dict:
        """Get Keepa product payload with stats=1 using ASIN."""
        if not self.cfg.api_key:
            return {"ok": False, "error": "KEEPA_API_KEY not set"}
        url = "https://api.keepa.com/product"
        params = {
            "key": self.cfg.api_key,
            "domain": self.cfg.domain,
            "asin": asin,
            "stats": 1,
        }
        return self._get(
            url, params, cache_key=f"product_stats:asin:{self.cfg.domain}:{asin}"
        )


def extract_primary_asin(keepa_payload: dict) -> Optional[str]:
    try:
        products = keepa_payload.get("products") or []
        if not products:
            return None
        # pick the first product's ASIN
        asin = products[0].get("asin")
        return asin
    except Exception:
        return None
