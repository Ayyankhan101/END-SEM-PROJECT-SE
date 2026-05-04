"""
Internationalization (i18n) support for DockWatch
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

# Default language
DEFAULT_LANGUAGE = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "zh", "ja", "pt", "ru"]

# Cache for loaded translations
_translations: Dict[str, Dict] = {}


def load_translations(language: str) -> Dict:
    """Load translations for a language"""
    if language in _translations:
        return _translations[language]
    
    # Try to load from file
    i18n_dir = Path(__file__).parent
    translation_file = i18n_dir / f"{language}.json"
    
    if translation_file.exists():
        with open(translation_file, 'r', encoding='utf-8') as f:
            _translations[language] = json.load(f)
            return _translations[language]
    
    # Fall back to default language
    if language != DEFAULT_LANGUAGE:
        return load_translations(DEFAULT_LANGUAGE)
    
    # Return empty dict if even default is missing
    return {}


def get_translation(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Get a translation string"""
    translations = load_translations(language)
    
    # Support nested keys like "container.status.running"
    keys = key.split(".")
    value = translations
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k, key)
        else:
            value = key
            break
    
    # Format with kwargs if provided
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            pass
    
    return value if isinstance(value, str) else key


# Alias for convenience
_ = get_translation


def get_supported_languages() -> List[Dict]:
    """Get list of supported languages with their names"""
    language_names = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "zh": "中文",
        "ja": "日本語",
        "pt": "Português",
        "ru": "Русский"
    }
    
    return [
        {"code": code, "name": language_names.get(code, code)}
        for code in SUPPORTED_LANGUAGES
    ]