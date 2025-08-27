"""Cache for external comps data with TTL support."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import settings

# Cache database path
_DB_PATH = Path("data/cache/external_comps.sqlite")
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_lock = threading.Lock()


def _db():
    """Create and configure database connection, migrating schema if needed."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")

    # Create table with desired composite primary key if it doesn't exist
    conn.execute(
        """CREATE TABLE IF NOT EXISTS comps_cache (
        query_sig TEXT NOT NULL,
        source TEXT NOT NULL,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        PRIMARY KEY (query_sig, source)
    )"""
    )

    # Detect legacy schema (PRIMARY KEY only on query_sig) and migrate
    try:
        cols = list(conn.execute("PRAGMA table_info(comps_cache)").fetchall())
        # PRAGMA table_info returns rows: (cid, name, type, notnull, dflt_value, pk)
        pk_cols = [c[1] for c in cols if c[5] == 1]
        has_composite_pk = set(pk_cols) == {"query_sig", "source"}
        if not has_composite_pk:
            # Migrate: create new table, copy data, drop old, rename new
            conn.execute(
                """CREATE TABLE IF NOT EXISTS comps_cache_new (
                query_sig TEXT NOT NULL,
                source TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                PRIMARY KEY (query_sig, source)
            )"""
            )
            # Attempt to copy if columns available; default source to 'unknown' if missing
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO comps_cache_new (query_sig, source, data, timestamp)\n"
                    "SELECT query_sig, COALESCE(source, 'unknown'), data, timestamp FROM comps_cache"
                )
            except Exception:
                # If legacy table lacks 'source' column, duplicate rows into 'unknown'
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO comps_cache_new (query_sig, source, data, timestamp)\n"
                        "SELECT query_sig, 'unknown', data, timestamp FROM comps_cache"
                    )
                except Exception:
                    pass
            conn.execute("DROP TABLE IF EXISTS comps_cache")
            conn.execute("ALTER TABLE comps_cache_new RENAME TO comps_cache")
            conn.commit()
    except Exception:
        # If PRAGMA fails, leave as-is; subsequent ops still function
        pass

    return conn


def _normalize_query_signature(
    title: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
) -> str:
    """Create a normalized query signature for cache key."""
    # Normalize and sort components for consistent hashing
    components = []
    if title:
        components.append(f"title:{title.lower().strip()}")
    if brand:
        components.append(f"brand:{brand.lower().strip()}")
    if model:
        components.append(f"model:{model.lower().strip()}")
    if upc:
        components.append(f"upc:{upc.strip()}")
    if asin:
        components.append(f"asin:{asin.strip()}")
    if condition_hint:
        components.append(f"cond:{condition_hint.lower().strip()}")

    # Sort for consistency and join
    components.sort()
    query_str = "|".join(components)

    # Create hash for shorter key
    return hashlib.md5(query_str.encode()).hexdigest()


def get_cached_comps(
    source: str,
    title: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve cached comps if available and not expired.

    Returns:
        List of comp dictionaries if cache hit and valid, None otherwise
    """
    if not hasattr(settings, "EXTERNAL_COMPS_CACHE_TTL_DAYS"):
        ttl_days = 7  # Default fallback
    else:
        ttl_days = settings.EXTERNAL_COMPS_CACHE_TTL_DAYS

    ttl_sec = ttl_days * 86400
    query_sig = _normalize_query_signature(
        title, brand, model, upc, asin, condition_hint
    )

    try:
        with _lock:
            conn = _db()
            cur = conn.execute(
                "SELECT data, timestamp FROM comps_cache WHERE query_sig = ? AND source = ?",
                (query_sig, source),
            )
            row = cur.fetchone()
            conn.close()

        if not row:
            return None

        data_str, timestamp = row

        # Check TTL
        if int(time.time()) - timestamp > ttl_sec:
            return None

        # Parse and return data
        return json.loads(data_str)
    except Exception:
        # On any error, treat as cache miss
        return None


def set_cached_comps(
    source: str,
    comps_data: List[Dict[str, Any]],
    title: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    upc: Optional[str] = None,
    asin: Optional[str] = None,
    condition_hint: Optional[str] = None,
) -> None:
    """
    Store comps data in cache.

    Args:
        source: Source identifier (e.g., 'ebay', 'google_search')
        comps_data: List of comp dictionaries to cache
        title, brand, model, upc, asin, condition_hint: Query parameters
    """
    query_sig = _normalize_query_signature(
        title, brand, model, upc, asin, condition_hint
    )

    try:
        with _lock:
            conn = _db()
            conn.execute(
                "INSERT OR REPLACE INTO comps_cache (query_sig, data, source, timestamp) VALUES (?, ?, ?, ?)",
                (query_sig, json.dumps(comps_data), source, int(time.time())),
            )
            conn.commit()
            conn.close()
    except Exception:
        # Silently fail on cache write errors
        pass


def clear_expired_cache() -> int:
    """
    Clear expired cache entries.

    Returns:
        Number of entries cleared
    """
    if not hasattr(settings, "EXTERNAL_COMPS_CACHE_TTL_DAYS"):
        ttl_days = 7
    else:
        ttl_days = settings.EXTERNAL_COMPS_CACHE_TTL_DAYS

    ttl_sec = ttl_days * 86400
    cutoff_time = int(time.time()) - ttl_sec

    try:
        with _lock:
            conn = _db()
            cur = conn.execute(
                "DELETE FROM comps_cache WHERE timestamp < ?", (cutoff_time,)
            )
            deleted_count = cur.rowcount
            conn.commit()
            conn.close()
        return deleted_count
    except Exception:
        return 0
