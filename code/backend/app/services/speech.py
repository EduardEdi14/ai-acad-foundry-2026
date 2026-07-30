"""Azure AI Speech — text-to-speech and speech-to-text, over plain REST.

We deliberately call the REST API with httpx instead of installing the Speech SDK.
Two reasons, both pedagogical: it keeps the dependency list honest, and it shows
what an "AI service" actually is once the SDK wrapper is removed — an HTTP
endpoint, a key or token, a content type, and bytes in both directions.

A Speech resource is *separate* from your Foundry resource: its own endpoint, its
own region, its own key. That is the point made in the session — services are not
the model, and one credential does not open all of them.

Config:  AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, AZURE_SPEECH_VOICE
"""
from __future__ import annotations

import httpx

from ..config import settings

# 24 kHz mono PCM in a RIFF container — plays in any browser, no codec needed
TTS_FORMAT = "riff-24khz-16bit-mono-pcm"


class SpeechUnavailable(Exception):
    """Raised with instructions when the Speech resource is not configured."""


def _credentials() -> tuple[str, str]:
    """Key and region for Speech.

    A Foundry resource of kind AIServices is *multi-service*: the same key and
    region already used for chat and embeddings also open Speech. So if the
    dedicated AZURE_SPEECH_* settings are empty we fall back to the Foundry ones —
    one resource, one key, several capabilities.

    A standalone Speech resource is still supported (and is what you would use if
    Speech belonged to a different team or subscription): set AZURE_SPEECH_KEY and
    AZURE_SPEECH_REGION and they win.
    """
    key = settings.azure_speech_key or settings.azure_ai_api_key
    region = settings.azure_speech_region or settings.azure_location
    if not key or not region:
        raise SpeechUnavailable(
            "Speech is not configured. Either set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION "
            "for a dedicated Speech resource, or — since a Foundry AIServices resource "
            "includes Speech — set AZURE_AI_API_KEY and AZURE_LOCATION and it will be used. "
            "See the Session 4 page, 'Speech: giving the assistant a voice'."
        )
    return key, region


def describe() -> dict:
    """What /health reports, without raising when nothing is configured."""
    try:
        key, region = _credentials()
    except SpeechUnavailable:
        return {"configured": False, "region": None, "source": None,
                "voice": settings.azure_speech_voice}
    dedicated = bool(settings.azure_speech_key)
    return {
        "configured": True,
        "region": region,
        "source": "dedicated Speech resource" if dedicated else "Foundry AIServices resource",
        "voice": settings.azure_speech_voice,
    }


def _require_config() -> None:
    _credentials()


def synthesize(text: str, voice: str | None = None) -> bytes:
    """Text -> spoken audio (WAV bytes). The request body is SSML."""
    key, region = _credentials()
    voice = voice or settings.azure_speech_voice
    locale = "-".join(voice.split("-")[:2]) if "-" in voice else "en-US"

    ssml = (
        f'<speak version="1.0" xml:lang="{locale}">'
        f'<voice xml:lang="{locale}" name="{voice}">{_escape(text)}</voice>'
        f"</speak>"
    )
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    response = httpx.post(
        url,
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": TTS_FORMAT,
            "User-Agent": "libra-academy",
        },
        content=ssml.encode("utf-8"),
        timeout=30.0,
    )
    if response.status_code != 200:
        raise SpeechUnavailable(
            f"Speech synthesis failed: HTTP {response.status_code} — {response.text[:300]}"
        )
    return response.content


def transcribe(audio: bytes, content_type: str = "audio/wav", language: str | None = None) -> dict:
    """Spoken audio -> text. Short-audio endpoint: up to about 60 seconds."""
    key, region = _credentials()
    language = language or settings.azure_speech_language

    url = (
        f"https://{region}.stt.speech.microsoft.com"
        f"/speech/recognition/conversation/cognitiveservices/v1"
    )
    response = httpx.post(
        url,
        params={"language": language, "format": "detailed"},
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": f"{content_type}; codecs=audio/pcm; samplerate=16000",
            "Accept": "application/json",
        },
        content=audio,
        timeout=60.0,
    )
    if response.status_code != 200:
        raise SpeechUnavailable(
            f"Speech recognition failed: HTTP {response.status_code} — {response.text[:300]}"
        )

    data = response.json()
    best = (data.get("NBest") or [{}])[0]
    return {
        "status": data.get("RecognitionStatus"),
        "text": data.get("DisplayText") or best.get("Display", ""),
        "confidence": best.get("Confidence"),
        "duration_seconds": round(data.get("Duration", 0) / 10_000_000, 2),
        "language": language,
    }


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
