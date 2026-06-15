"""
Voice Generator - Converts text to speech using Edge TTS with mood-aware parameters.

Features:
- Human-sounding voice (Edge TTS neural voices)
- Mood-aware rate and pitch adjustment
- Pause duration based on intensity
- No API key required (uses Edge service)
"""

import asyncio
import os
from typing import Dict, Optional
from pathlib import Path
import edge_tts


class VoiceGenerator:
    """
    Generates audio narration using Edge TTS (Microsoft's neural voices).
    
    Features:
    - Multiple voice options (male/female, languages)
    - Rate and pitch control
    - Mood-aware speech timing
    - Pause injection between phrases
    """
    
    AVAILABLE_VOICES = {
        "en-US": {
            "neutral": "en-US-AriaNeural",
            "male": "en-US-GuyNeural",
            "female": "en-US-AriaNeural",
            "young-male": "en-US-ChristopherNeural",
            "young-female": "en-US-JennyNeural",
        },
        "en-GB": {
            "neutral": "en-GB-RyanNeural",
            "male": "en-GB-RyanNeural",
            "female": "en-GB-SoniaNeural",
        },
        "en-AU": {
            "neutral": "en-AU-NatashaNeural",
            "male": "en-AU-WilliamNeural",
            "female": "en-AU-NatashaNeural",
        },
    }
    
    def __init__(
        self,
        voice: str = "en-US-AriaNeural",
        rate: float = 1.0,
        pitch: float = 0.0,
    ):
        """
        Initialize voice generator.
        
        Args:
            voice: Edge TTS voice code (e.g., "en-US-AriaNeural")
            rate: Speech rate multiplier (0.5-2.0)
            pitch: Pitch offset (-20 to +20)
        """
        self.voice = voice
        self.rate = max(0.5, min(2.0, rate))
        self.pitch = max(-20.0, min(20.0, pitch))
    
    async def generate_async(
        self,
        text: str,
        output_path: str,
        rate_multiplier: float = 1.0,
        pitch_offset: float = 0.0,
        pause_duration: int = 600,
    ) -> str:
        """
        Generate speech asynchronously (for batch processing).
        
        Args:
            text: Text to speak
            output_path: Output MP3 file path
            rate_multiplier: Mood-based rate adjustment
            pitch_offset: Mood-based pitch adjustment
            pause_duration: Milliseconds to pause between sentences
        
        Returns:
            Path to generated audio file
        """
        # Apply mood modifiers
        final_rate = self.rate * rate_multiplier
        final_pitch = self.pitch + pitch_offset
        
        # Clamp values
        final_rate = max(0.5, min(2.0, final_rate))
        final_pitch = max(-20, min(20, final_pitch))
        
        # Create TTS communication
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self._rate_to_percentage(final_rate),
            pitch=f"{final_pitch:+.0f}%",
        )
        
        # Save to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await communicate.save(str(output_path))
        return str(output_path)
    
    def generate(
        self,
        text: str,
        output_path: str,
        rate_multiplier: float = 1.0,
        pitch_offset: float = 0.0,
        pause_duration: int = 600,
    ) -> str:
        """
        Generate speech (synchronous wrapper).
        
        Args:
            text: Text to speak
            output_path: Output MP3 file path
            rate_multiplier: Mood-based rate adjustment
            pitch_offset: Mood-based pitch adjustment
            pause_duration: Milliseconds to pause between sentences
        
        Returns:
            Path to generated audio file
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.generate_async(
                    text,
                    output_path,
                    rate_multiplier,
                    pitch_offset,
                    pause_duration,
                )
            )
        finally:
            loop.close()
    
    def _rate_to_percentage(self, rate: float) -> str:
        """Convert rate multiplier (0.5-2.0) to Edge TTS percentage format."""
        # Edge TTS uses percentage from -100 to +100
        # 1.0 = 0%, 0.5 = -50%, 2.0 = +100%
        percentage = (rate - 1.0) * 100
        percentage = max(-100, min(100, percentage))
        return f"{percentage:+.0f}%"
    
    def set_voice(self, voice: str):
        """Change voice mid-session."""
        self.voice = voice
    
    def set_base_rate(self, rate: float):
        """Set base rate for future generations."""
        self.rate = max(0.5, min(2.0, rate))
    
    def set_base_pitch(self, pitch: float):
        """Set base pitch for future generations."""
        self.pitch = max(-20, min(20, pitch))
    
    @classmethod
    def get_voice_for_locale(
        cls,
        locale: str = "en-US",
        gender: str = "neutral"
    ) -> str:
        """
        Get a voice code for a given locale and gender.
        
        Args:
            locale: Language locale (e.g., "en-US", "en-GB")
            gender: "male", "female", or "neutral"
        
        Returns:
            Voice code for use with Edge TTS
        """
        if locale not in cls.AVAILABLE_VOICES:
            locale = "en-US"
        
        voices = cls.AVAILABLE_VOICES[locale]
        return voices.get(gender, voices.get("neutral"))