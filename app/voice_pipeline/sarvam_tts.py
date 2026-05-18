"""
SarvamTTS — Custom LiveKit TTS Plugin for Sarvam AI (bulbul model)
Wraps the Sarvam REST API (https://api.sarvam.ai/text-to-speech)
and makes it compatible with LiveKit's VoicePipelineAgent.

Sarvam returns base64-encoded WAV audio.
This plugin decodes it and streams 20ms PCM audio frames to LiveKit.
"""

from __future__ import annotations

import asyncio
import base64
import io
import struct
import wave
import logging
from dataclasses import dataclass
from typing import AsyncIterator

import aiohttp
from livekit import rtc
from livekit.agents import tts, utils

logger = logging.getLogger(__name__)

# ============================================================
# Sarvam TTS API Constants
# ============================================================

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SAMPLES_PER_FRAME = 480   # 20ms at 24000 Hz — LiveKit standard chunk size
DEFAULT_SAMPLE_RATE = 22050  # Sarvam bulbul:v2 default output


# ============================================================
# SarvamTTS — Main Plugin Class
# ============================================================

class SarvamTTS(tts.TTS):
    """
    LiveKit-compatible TTS plugin using Sarvam AI's bulbul model.

    Usage:
        tts_plugin = SarvamTTS(
            api_key=settings.SARVAM_API_KEY,
            speaker=settings.SARVAM_TTS_SPEAKER,
            model=settings.SARVAM_TTS_MODEL,
            language=settings.SARVAM_TTS_LANGUAGE,
        )
    """

    def __init__(
        self,
        *,
        api_key: str,
        speaker: str = "anushka",
        model: str = "bulbul:v2",
        language: str = "en-IN",
        pace: float = 1.0,
        sample_rate: int = 22050,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._api_key = api_key
        self._speaker = speaker
        self._model = model
        self._language = language
        self._pace = pace
        self._sample_rate = sample_rate

    def synthesize(self, text: str) -> "SarvamSynthesizeStream":
        return SarvamSynthesizeStream(tts=self, text=text)


# ============================================================
# SarvamSynthesizeStream — Async Audio Stream
# ============================================================

class SarvamSynthesizeStream(tts.SynthesizeStream):
    """
    Fetches audio from Sarvam REST API and emits LiveKit AudioFrames.
    """

    def __init__(self, *, tts: SarvamTTS, text: str):
        super().__init__(tts=tts)
        self._tts = tts
        self._text = text

    async def _run(self) -> None:
        """Called internally by LiveKit to begin synthesis."""
        try:
            wav_bytes = await self._fetch_audio(self._text)
            async for frame in self._wav_to_frames(wav_bytes):
                self._event_ch.send_nowait(
                    tts.SynthesizedAudio(
                        frame=frame,
                        request_id=utils.shortuuid(),
                    )
                )
        except aiohttp.ClientResponseError as e:
            logger.error(f"[SarvamTTS] API error {e.status}: {e.message}")
            raise
        except Exception as e:
            logger.error(f"[SarvamTTS] Unexpected error during synthesis: {e}", exc_info=True)
            raise

    async def _fetch_audio(self, text: str) -> bytes:
        """
        POST to Sarvam TTS API and return raw WAV bytes.
        Header uses 'api-subscription-key' (not Bearer token).
        """
        payload = {
            "text": text,
            "target_language_code": self._tts._language,
            "speaker": self._tts._speaker,
            "model": self._tts._model,
            "pace": self._tts._pace,
        }
        headers = {
            "api-subscription-key": self._tts._api_key,
            "Content-Type": "application/json",
        }

        logger.debug(f"[SarvamTTS] Requesting TTS for text: {text[:60]}...")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                SARVAM_TTS_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        # Sarvam returns: {"audios": ["<base64_wav>", ...]}
        audio_b64 = data["audios"][0]
        wav_bytes = base64.b64decode(audio_b64)
        logger.debug(f"[SarvamTTS] Received {len(wav_bytes)} bytes of WAV audio.")
        return wav_bytes

    async def _wav_to_frames(self, wav_bytes: bytes) -> AsyncIterator[rtc.AudioFrame]:
        """
        Parse WAV bytes and yield 20ms PCM AudioFrames for LiveKit.
        Yields control back to event loop between frames to stay non-blocking.
        """
        with io.BytesIO(wav_bytes) as wav_io:
            with wave.open(wav_io, "rb") as wav_file:
                num_channels = wav_file.getnchannels()
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                pcm_data = wav_file.readframes(n_frames)

        # 20ms chunk size at the actual sample rate from the file
        samples_per_frame = sample_rate // 50  # e.g. 22050/50 = 441
        bytes_per_sample = 2  # 16-bit PCM → 2 bytes
        bytes_per_frame = samples_per_frame * num_channels * bytes_per_sample

        for i in range(0, len(pcm_data), bytes_per_frame):
            chunk = pcm_data[i : i + bytes_per_frame]

            # Pad the last incomplete chunk with silence
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))

            audio_frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=sample_rate,
                num_channels=num_channels,
                samples_per_channel=samples_per_frame,
            )
            yield audio_frame
            # Yield control to event loop — keeps the pipeline non-blocking
            await asyncio.sleep(0)
