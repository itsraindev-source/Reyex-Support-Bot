"""
Tests for translation service.
"""

import pytest

from bot.services.translation_service import TranslationService, get_translation_service


def test_service_singleton():
    """Test that the translation service singleton works correctly."""
    service1 = get_translation_service()
    service2 = get_translation_service()
    
    assert service1 is service2  # Should be the same instance


def test_supported_languages():
    """Test that supported languages are properly configured."""
    service = TranslationService()
    
    languages = service.supported_languages
    
    # Check that common languages are supported
    assert "en" in languages  # English
    assert "es" in languages  # Spanish
    assert "fr" in languages  # French
    assert "de" in languages  # German
    
    # Check that language codes map to language names
    assert languages["en"] == "English"
    assert languages["es"] == "Spanish"


def test_service_initialization():
    """Test that the service initializes with correct configuration."""
    service = TranslationService()
    
    assert service.libretranslate_url is not None
    assert len(service.supported_languages) > 0


def test_get_supported_languages():
    """Test getting supported languages."""
    service = TranslationService()
    
    languages = service.get_supported_languages()
    
    assert isinstance(languages, dict)
    assert len(languages) > 0
    assert "en" in languages
