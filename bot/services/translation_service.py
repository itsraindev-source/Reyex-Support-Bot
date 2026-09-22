"""
Translation service using LibreTranslate API.
"""

import hashlib
import httpx
from typing import Optional, Dict

from bot.config import get_settings
from bot.database.connection import get_session
from bot.database.redis_client import get_redis_client
from bot.database.repositories.user_repository import UserRepository
from bot.utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()


class TranslationService:
    """Service for automatic translation using LibreTranslate."""
    
    def __init__(self):
        self.libretranslate_url = settings.libretranslate_url
        self.api_key = settings.libretranslate_api_key
        self.supported_languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese",
        }
        self._http_client: Optional[httpx.AsyncClient] = None
        self._cache_ttl = 3600  # Cache translations for 1 hour
    
    def get_http_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            timeout = httpx.Timeout(30.0)
            self._http_client = httpx.AsyncClient(timeout=timeout)
        return self._http_client
    
    async def detect_language(self, text: str) -> Optional[str]:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Detected language code (e.g., 'en', 'es'), or None if detection fails
        """
        if not text or len(text.strip()) < 3:
            return None
        
        try:
            client = self.get_http_client()
            
            response = await client.post(
                f"{self.libretranslate_url}/detect",
                json={"q": text},
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    detected = result[0].get("language")
                    logger.debug(f"Detected language: {detected} for text: {text[:50]}...")
                    return detected
            
            logger.warning(f"Language detection failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return None
    
    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> Optional[str]:
        """
        Translate text to the target language.
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'en', 'es')
            source_language: Source language code (auto-detect if None)
            
        Returns:
            Translated text, or None if translation fails
        """
        if not text or not text.strip():
            return None
        
        if target_language not in self.supported_languages:
            logger.warning(f"Unsupported target language: {target_language}")
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(text, target_language, source_language)
        cached = await self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for translation: {text[:50]}...")
            return cached
        
        try:
            client = self.get_http_client()
            
            payload = {
                "q": text,
                "source": source_language or "auto",
                "target": target_language,
                "format": "text",
            }
            
            response = await client.post(
                f"{self.libretranslate_url}/translate",
                json=payload,
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                translated = result.get("translatedText")
                
                if translated:
                    logger.debug(
                        f"Translated text from {source_language or 'auto'} to {target_language}: "
                        f"{text[:50]}... -> {translated[:50]}..."
                    )
                    # Cache the result
                    await self._set_cache(cache_key, translated)
                    return translated
            
            logger.warning(f"Translation failed: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return None
    
    def _get_cache_key(self, text: str, target_language: str, source_language: Optional[str] = None) -> str:
        """Generate a cache key for translation."""
        content = f"{text}:{target_language}:{source_language or 'auto'}"
        return f"translation:{hashlib.md5(content.encode()).hexdigest()}"
    
    async def _get_from_cache(self, key: str) -> Optional[str]:
        """Get translation from Redis cache."""
        try:
            redis_client = get_redis_client()
            cached = await redis_client.get(key)
            if cached:
                return cached.decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to get from cache: {e}")
        return None
    
    async def _set_cache(self, key: str, value: str):
        """Set translation in Redis cache."""
        try:
            redis_client = get_redis_client()
            await redis_client.setex(key, self._cache_ttl, value)
        except Exception as e:
            logger.warning(f"Failed to set cache: {e}")
    
    async def translate_for_user(
        self,
        text: str,
        user_id: int,
        author_id: int,
    ) -> Optional[Dict[str, str]]:
        """
        Translate text for a specific user based on their language preferences.
        
        Args:
            text: Text to translate
            user_id: ID of the user to translate for
            author_id: ID of the message author (to avoid translating their own messages)
            
        Returns:
            Dictionary with translation info, or None if translation not needed/possible
        """
        # Don't translate user's own messages
        if user_id == author_id:
            return None
        
        # Get user's language preference
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_user(user_id)
            
            if not user or not user.auto_translate:
                return None
            
            target_language = user.language
        
        # Detect source language
        source_language = await self.detect_language(text)
        
        # Don't translate if already in target language
        if source_language == target_language:
            return None
        
        # Translate
        translated = await self.translate_text(text, target_language, source_language)
        
        if translated:
            return {
                "original": text,
                "translated": translated,
                "source_language": source_language,
                "target_language": target_language,
                "source_language_name": self.supported_languages.get(source_language, source_language),
                "target_language_name": self.supported_languages.get(target_language, target_language),
            }
        
        return None
    
    async def get_supported_languages(self) -> Dict[str, str]:
        """
        Get the list of supported languages.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return self.supported_languages.copy()
    
    async def check_service_health(self) -> bool:
        """
        Check if the LibreTranslate service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            client = self.get_http_client()
            
            response = await client.get(f"{self.libretranslate_url}/languages")
            
            if response.status_code == 200:
                languages = response.json()
                logger.info(f"LibreTranslate service healthy, supports {len(languages)} languages")
                return True
            
            logger.warning(f"LibreTranslate service unhealthy: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking LibreTranslate health: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Global translation service instance
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """Get the global translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


async def close_translation_service():
    """Close the global translation service."""
    global _translation_service
    if _translation_service:
        await _translation_service.close()
        _translation_service = None
