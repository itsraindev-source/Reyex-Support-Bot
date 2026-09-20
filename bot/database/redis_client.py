"""
Redis client wrapper for caching and session management.
"""

import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from bot.config import get_settings


class RedisClient:
    """
    Async Redis client wrapper with common operations.
    """
    
    def __init__(self):
        self._client: Optional[Redis] = None
        self._settings = get_settings()
    
    async def get_client(self) -> Redis:
        """Get or create the Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
        return self._client
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis.
        
        Args:
            key: The key to set
            value: The value to set (will be JSON serialized if not a string)
            ttl: Optional time-to-live in seconds
            
        Returns:
            True if successful
        """
        client = await self.get_client()
        
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if ttl:
            return await client.setex(key, ttl, value)
        return await client.set(key, value)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value, or None if not found
        """
        client = await self.get_client()
        value = await client.get(key)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def delete(self, key: str) -> int:
        """
        Delete a key from Redis.
        
        Args:
            key: The key to delete
            
        Returns:
            Number of keys deleted (0 or 1)
        """
        client = await self.get_client()
        return await client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: The key to check
            
        Returns:
            True if the key exists
        """
        client = await self.get_client()
        return await client.exists(key) > 0
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set a time-to-live for a key.
        
        Args:
            key: The key to set TTL for
            ttl: Time-to-live in seconds
            
        Returns:
            True if successful
        """
        client = await self.get_client()
        return await client.expire(key, ttl)
    
    async def ttl(self, key: str) -> int:
        """
        Get the remaining time-to-live for a key.
        
        Args:
            key: The key to check
            
        Returns:
            Remaining TTL in seconds, or -1 if no TTL, -2 if key doesn't exist
        """
        client = await self.get_client()
        return await client.ttl(key)
    
    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a key by a given amount.
        
        Args:
            key: The key to increment
            amount: Amount to increment by (default 1)
            
        Returns:
            The new value
        """
        client = await self.get_client()
        return await client.incrby(key, amount)
    
    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a key by a given amount.
        
        Args:
            key: The key to decrement
            amount: Amount to decrement by (default 1)
            
        Returns:
            The new value
        """
        client = await self.get_client()
        return await client.decrby(key, amount)
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """
        Set a field in a Redis hash.
        
        Args:
            name: The hash name
            key: The field key
            value: The field value
            
        Returns:
            True if successful
        """
        client = await self.get_client()
        
        if not isinstance(value, str):
            value = json.dumps(value)
        
        return await client.hset(name, key, value)
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """
        Get a field from a Redis hash.
        
        Args:
            name: The hash name
            key: The field key
            
        Returns:
            The field value, or None if not found
        """
        client = await self.get_client()
        value = await client.hget(name, key)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def hgetall(self, name: str) -> dict:
        """
        Get all fields from a Redis hash.
        
        Args:
            name: The hash name
            
        Returns:
            Dictionary of all fields and values
        """
        client = await self.get_client()
        values = await client.hgetall(name)
        
        result = {}
        for key, value in values.items():
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        
        return result
    
    async def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a Redis hash.
        
        Args:
            name: The hash name
            *keys: Field keys to delete
            
        Returns:
            Number of fields deleted
        """
        client = await self.get_client()
        return await client.hdel(name, *keys)
    
    async def lpush(self, name: str, *values: Any) -> int:
        """
        Push values to the left side of a Redis list.
        
        Args:
            name: The list name
            *values: Values to push
            
        Returns:
            New length of the list
        """
        client = await self.get_client()
        
        serialized_values = []
        for value in values:
            if not isinstance(value, str):
                value = json.dumps(value)
            serialized_values.append(value)
        
        return await client.lpush(name, *serialized_values)
    
    async def rpop(self, name: str) -> Optional[Any]:
        """
        Pop a value from the right side of a Redis list.
        
        Args:
            name: The list name
            
        Returns:
            The popped value, or None if list is empty
        """
        client = await self.get_client()
        value = await client.rpop(name)
        
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    
    async def llen(self, name: str) -> int:
        """
        Get the length of a Redis list.
        
        Args:
            name: The list name
            
        Returns:
            Length of the list
        """
        client = await self.get_client()
        return await client.llen(name)
    
    async def close(self):
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get the global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


async def close_redis():
    """Close the global Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
