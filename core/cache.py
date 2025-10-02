"""
Caching layer for API calls and computed data.
Uses Streamlit's built-in caching plus optional on-disk parquet storage.
"""
import os
from pathlib import Path
from typing import Optional, Callable, Any
import pandas as pd
import streamlit as st
import logging
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for data fetching and computations."""

    def __init__(self, cache_dir: Optional[str] = None, ttl_seconds: int = 3600):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for on-disk cache (optional)
            ttl_seconds: Time-to-live for cached data
        """
        self.ttl_seconds = ttl_seconds

        if cache_dir:
            self.cache_dir = Path(os.path.expanduser(cache_dir))
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Default cache location
            self.cache_dir = Path.home() / ".streamlit_fundamentals" / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cache directory: {self.cache_dir}")

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a cache key from prefix and kwargs.

        Args:
            prefix: Cache key prefix (e.g., 'price_history', 'snapshot')
            **kwargs: Key-value pairs to include in hash

        Returns:
            Cache key string
        """
        # Sort kwargs for consistent hashing
        sorted_kwargs = sorted(kwargs.items())
        key_str = f"{prefix}_{json.dumps(sorted_kwargs, sort_keys=True, default=str)}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"{prefix}_{key_hash}"

    def get_parquet_path(self, cache_key: str) -> Path:
        """Get file path for parquet cache."""
        return self.cache_dir / f"{cache_key}.parquet"

    def get_json_path(self, cache_key: str) -> Path:
        """Get file path for JSON cache."""
        return self.cache_dir / f"{cache_key}.json"

    def cache_dataframe(self, cache_key: str, df: pd.DataFrame) -> None:
        """
        Cache a DataFrame to disk.

        Args:
            cache_key: Cache key
            df: DataFrame to cache
        """
        try:
            path = self.get_parquet_path(cache_key)
            df.to_parquet(path)
            logger.debug(f"Cached dataframe to {path}")
        except Exception as e:
            logger.warning(f"Failed to cache dataframe: {e}")

    def load_cached_dataframe(self, cache_key: str) -> Optional[pd.DataFrame]:
        """
        Load cached DataFrame from disk.

        Args:
            cache_key: Cache key

        Returns:
            DataFrame if found and not expired, None otherwise
        """
        try:
            path = self.get_parquet_path(cache_key)
            if not path.exists():
                return None

            # Check if expired
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = datetime.now() - mtime
            if age.total_seconds() > self.ttl_seconds:
                logger.debug(f"Cache expired for {cache_key}")
                return None

            df = pd.read_parquet(path)
            logger.debug(f"Loaded cached dataframe from {path}")
            return df

        except Exception as e:
            logger.warning(f"Failed to load cached dataframe: {e}")
            return None

    def cache_json(self, cache_key: str, data: dict) -> None:
        """
        Cache JSON data to disk.

        Args:
            cache_key: Cache key
            data: Dictionary to cache
        """
        try:
            path = self.get_json_path(cache_key)
            with open(path, 'w') as f:
                json.dump(data, f, default=str)
            logger.debug(f"Cached JSON to {path}")
        except Exception as e:
            logger.warning(f"Failed to cache JSON: {e}")

    def load_cached_json(self, cache_key: str) -> Optional[dict]:
        """
        Load cached JSON from disk.

        Args:
            cache_key: Cache key

        Returns:
            Dictionary if found and not expired, None otherwise
        """
        try:
            path = self.get_json_path(cache_key)
            if not path.exists():
                return None

            # Check if expired
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = datetime.now() - mtime
            if age.total_seconds() > self.ttl_seconds:
                logger.debug(f"Cache expired for {cache_key}")
                return None

            with open(path, 'r') as f:
                data = json.load(f)
            logger.debug(f"Loaded cached JSON from {path}")
            return data

        except Exception as e:
            logger.warning(f"Failed to load cached JSON: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear all cached files."""
        try:
            for file in self.cache_dir.glob("*"):
                if file.is_file():
                    file.unlink()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        cache_dir = os.getenv("CACHE_DIR", "~/.streamlit_fundamentals/cache")
        ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        _cache_manager = CacheManager(cache_dir=cache_dir, ttl_seconds=ttl)
    return _cache_manager


# Streamlit cache decorators with proper TTL

@st.cache_data(ttl=3600, show_spinner=False)
def cached_price_history(adapter_name: str, symbol: str, start_str: str, end_str: str, interval: str) -> pd.DataFrame:
    """
    Cached wrapper for price history fetching.
    Note: Actual fetching is done in repository, this is just a cache placeholder.
    """
    # This function is overridden by the repository
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_snapshot(adapter_name: str, symbol: str) -> dict:
    """
    Cached wrapper for snapshot fetching.
    Note: Actual fetching is done in repository, this is just a cache placeholder.
    """
    # This function is overridden by the repository
    return {}
