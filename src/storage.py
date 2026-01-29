import json
import redis
from datetime import timedelta
from .config import REDIS_URL, logger

class StorageManager:
    def __init__(self):
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            logger.info("Connected to Redis")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def save_session(self, chat_id: int, session_data: dict, ttl_days: int = 30):
        """Save user session with expiration."""
        key = f"session:{chat_id}"
        self.redis.set(key, json.dumps(session_data))
        self.redis.expire(key, timedelta(days=ttl_days))

    def get_session(self, chat_id: int) -> dict:
        """Retrieve user session."""
        key = f"session:{chat_id}"
        data = self.redis.get(key)
        if data:
            # Refresh expiration on activity
            self.redis.expire(key, timedelta(days=30))
            return json.loads(data)
        return None

    def clear_session(self, chat_id: int):
        """Remove user session."""
        self.redis.delete(f"session:{chat_id}")

    def cache_search_results(self, query_hash: str, results: list, ttl_seconds: int = 60):
        """Cache search results for pagination."""
        key = f"search:{query_hash}"
        self.redis.set(key, json.dumps(results))
        self.redis.expire(key, ttl_seconds)

    def get_cached_search(self, query_hash: str) -> list:
        """Retrieve cached search results."""
        key = f"search:{query_hash}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

storage_manager = StorageManager()
