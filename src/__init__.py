"""Comic Reader - AI-powered comic scene narration with progressive mood detection."""

__version__ = "0.1.0"
__author__ = "Amogh Tapan Sharma"

from .scene_extractor import SceneExtractor
from .mood_state import MoodState
from .mood_detector import MoodDetector
from .character_voice_mapper import CharacterVoiceMapper
from .voice_generator import VoiceGenerator
from .audio_processor import AudioProcessor

__all__ = [
    "SceneExtractor",
    "MoodState",
    "MoodDetector",
    "CharacterVoiceMapper",
    "VoiceGenerator",
    "AudioProcessor",
]