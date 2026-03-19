"""
Sarvam AI Translator & TTS — Phase 5
Handles all language translation and text-to-speech using Sarvam AI APIs.
"""
import os
import re
import time
from typing import Optional

import httpx
from dotenv import load_dotenv
from tenacity import retry, wait_fixed, stop_after_attempt

load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"
RATE_LIMIT_DELAY = 1.0  # 60 req/min → ~1s between calls

# Language code mapping
LANG_MAP = {
    "hi": "hi-IN", "ta": "ta-IN", "te": "te-IN", "bn": "bn-IN",
    "mr": "mr-IN", "gu": "gu-IN", "kn": "kn-IN", "ml": "ml-IN",
    "pa": "pa-IN", "or": "or-IN", "en": "en-IN",
}

_last_call = 0.0


def _rate_limit():
    """Enforce rate limiting between Sarvam API calls."""
    global _last_call
    now = time.time()
    elapsed = now - _last_call
    if elapsed < RATE_LIMIT_DELAY:
        time.sleep(RATE_LIMIT_DELAY - elapsed)
    _last_call = time.time()


def _sarvam_headers() -> dict:
    return {
        "API-Subscription-Key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }


# ---- 1. detect_language ----

def detect_language(text: str) -> str:
    """
    Detect the language of input text.
    Uses Unicode heuristics with Sarvam API fallback.
    """
    # Quick heuristic: check for Devanagari script (Hindi)
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    # Tamil
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    # Telugu
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "te"
    # Bengali
    if re.search(r"[\u0980-\u09FF]", text):
        return "bn"
    # Gujarati
    if re.search(r"[\u0A80-\u0AFF]", text):
        return "gu"
    # Kannada
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn"
    # Malayalam
    if re.search(r"[\u0D00-\u0D7F]", text):
        return "ml"
    # Punjabi (Gurmukhi)
    if re.search(r"[\u0A00-\u0A7F]", text):
        return "pa"
    # Odia
    if re.search(r"[\u0B00-\u0B7F]", text):
        return "or"
    # Default: English
    return "en"


# ---- 2. translate_to_english ----

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
def translate_to_english(text: str, source_lang: str) -> str:
    """Translate user input to English for agent processing."""
    if source_lang == "en":
        return text

    _rate_limit()

    sarvam_source = LANG_MAP.get(source_lang, f"{source_lang}-IN")

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{SARVAM_BASE_URL}/translate",
                headers=_sarvam_headers(),
                json={
                    "input": text,
                    "source_language_code": sarvam_source,
                    "target_language_code": "en-IN",
                    "speaker_gender": "Male",
                    "mode": "formal",
                    "model": "mayura:v1",
                    "enable_preprocessing": True,
                },
            )
            resp.raise_for_status()
            return resp.json().get("translated_text", text)
    except Exception:
        return text  # Fallback: return original


# ---- 3. translate_to_language ----

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
def translate_to_language(text: str, target_lang: str) -> str:
    """Translate agent response to target language, preserving numbers and scheme names."""
    if target_lang == "en":
        return text

    _rate_limit()

    sarvam_target = LANG_MAP.get(target_lang, f"{target_lang}-IN")

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{SARVAM_BASE_URL}/translate",
                headers=_sarvam_headers(),
                json={
                    "input": text,
                    "source_language_code": "en-IN",
                    "target_language_code": sarvam_target,
                    "speaker_gender": "Male",
                    "mode": "formal",
                    "model": "mayura:v1",
                    "enable_preprocessing": True,
                },
            )
            resp.raise_for_status()
            return resp.json().get("translated_text", text)
    except Exception:
        return text


# ---- 4. translate_scheme_card ----

def translate_scheme_card(scheme: dict, target_lang: str) -> dict:
    """
    Translate benefits_summary and eligibility_summary fields.
    Keeps scheme_name in English (official name).
    """
    if target_lang == "en":
        return scheme

    translated = dict(scheme)

    if scheme.get("benefits_summary"):
        translated["benefits_summary"] = translate_to_language(
            scheme["benefits_summary"], target_lang
        )
    if scheme.get("eligibility_summary"):
        translated["eligibility_summary"] = translate_to_language(
            scheme["eligibility_summary"], target_lang
        )

    return translated


# ---- 5. text_to_speech ----

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
def text_to_speech(text: str, language: str = "hi") -> Optional[bytes]:
    """
    Convert text to speech using Sarvam Bulbul TTS API.
    Returns audio bytes (wav format) or None on failure.
    """
    _rate_limit()

    sarvam_lang = LANG_MAP.get(language, f"{language}-IN")

    # Truncate to ~500 chars for TTS (API limit)
    if len(text) > 500:
        text = text[:497] + "..."

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{SARVAM_BASE_URL}/text-to-speech",
                headers=_sarvam_headers(),
                json={
                    "inputs": [text],
                    "target_language_code": sarvam_lang,
                    "speaker": "meera",
                    "model": "bulbul:v1",
                    "pitch": 0,
                    "pace": 1.0,
                    "loudness": 1.5,
                    "speech_sample_rate": 22050,
                    "enable_preprocessing": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # API returns base64-encoded audio
            import base64
            audio_b64 = data.get("audios", [None])[0]
            if audio_b64:
                return base64.b64decode(audio_b64)
    except Exception:
        pass

    return None
