"""
Redis service for managing call session state.
Provides fast read/write of CallSession objects during active calls.
"""

import json
import redis.asyncio as redis
from typing import Optional
from app.models.call_state import CallSession
from app.config import settings
from app.utils.logger import CallLogger

logger = CallLogger(call_id="redis")

SESSION_TTL = 3600  # 1 hour


class RedisService:
    """Manages call session state using real Redis (via Docker) with in-memory fallback."""

    def __init__(self):
        self._prefix = "voice_agent:session:"
        self._fallback_storage = {}  # In-memory fallback for demos
        self.use_fallback = False

    async def connect(self):
        """Check if Redis is available, otherwise set fallback mode."""
        client = self._get_client()
        try:
            await client.ping()
            self.use_fallback = False
            logger.info("Redis connected")
        except Exception:
            self.use_fallback = True
            logger.warning("Redis not reachable. Using in-memory fallback for session state.")
        finally:
            await client.aclose()

    async def disconnect(self):
        """No-op."""
        pass

    def _get_client(self):
        return redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,  # Fast fail for demos
        )

    def _key(self, call_id: str) -> str:
        return f"{self._prefix}{call_id}"

    async def save_session(self, session: CallSession) -> None:
        """Save session to Redis (or fallback dictionary)."""
        key = self._key(session.call_id)
        
        if self.use_fallback:
            self._fallback_storage[key] = session.model_dump_json()
            return

        client = self._get_client()
        try:
            await client.set(key, session.model_dump_json(), ex=SESSION_TTL)
        except Exception:
            self.use_fallback = True
            self._fallback_storage[key] = session.model_dump_json()
            logger.warning("Redis failed during save. Switched to in-memory fallback.")
        finally:
            await client.aclose()

    async def get_session(self, call_id: str) -> Optional[CallSession]:
        """Retrieve session from Redis (or fallback dictionary)."""
        key = self._key(call_id)
        
        if self.use_fallback:
            data = self._fallback_storage.get(key)
            return CallSession.model_validate_json(data) if data else None

        client = self._get_client()
        try:
            data = await client.get(key)
            if data:
                return CallSession.model_validate_json(data)
            return None
        except Exception:
            self.use_fallback = True
            data = self._fallback_storage.get(key)
            return CallSession.model_validate_json(data) if data else None
        finally:
            await client.aclose()

    async def delete_session(self, call_id: str) -> None:
        """Delete session."""
        key = self._key(call_id)
        if self.use_fallback:
            self._fallback_storage.pop(key, None)
            return

        client = self._get_client()
        try:
            await client.delete(key)
        except Exception:
            self.use_fallback = True
        finally:
            await client.aclose()

    async def session_exists(self, call_id: str) -> bool:
        """Check if a session exists."""
        key = self._key(call_id)
        if self.use_fallback:
            return key in self._fallback_storage

        client = self._get_client()
        try:
            return bool(await client.exists(key))
        except Exception:
            self.use_fallback = True
            return key in self._fallback_storage
        finally:
            await client.aclose()

    async def get_active_call_count(self) -> int:
        """Get count of active sessions."""
        if not self._client:
            await self.connect()
        keys = await self._client.keys(f"{self._prefix}*")
        return len(keys)


# Singleton instance
redis_service = RedisService()
