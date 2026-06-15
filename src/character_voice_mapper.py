"""
Character Voice Mapper - Maps identified characters to distinct voice profiles.

Features:
- Auto-detect character names from dialogue
- Assign voice profiles (gender, voice type, accent)
- Store character voice preferences
- Support for voice variation per character state (calm, angry, sad, etc.)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import json
from pathlib import Path


@dataclass
class VoiceProfile:
    """Voice configuration for a character."""
    character_name: str
    base_voice: str  # e.g., "en-US-AriaNeural"
    gender: str  # "male", "female", "neutral"
    age_group: str  # "child", "young-adult", "adult", "elderly"
    personality_traits: List[str] = field(default_factory=list)  # e.g., ["sarcastic", "energetic"]
    base_rate: float = 1.0  # Speech rate modifier
    base_pitch: float = 0.0  # Pitch offset
    voice_variants: Dict[str, Dict] = field(default_factory=dict)
    # Variants by emotional state: {"angry": {"rate": 1.2, "pitch": 5}, ...}


class CharacterVoiceMapper:
    """
    Maps characters to voice profiles.
    
    Automatically detects characters from dialogue and assigns
    contextually appropriate voices.
    """
    
    # Predefined character archetypes with voice suggestions
    DEFAULT_ARCHETYPES = {
        "protagonist": {
            "gender": "male",
            "age_group": "young-adult",
            "personality_traits": ["determined", "thoughtful"],
            "base_voice": "en-US-GuyNeural",
            "base_rate": 1.0,
        },
        "female-lead": {
            "gender": "female",
            "age_group": "young-adult",
            "personality_traits": ["intelligent", "confident"],
            "base_voice": "en-US-AriaNeural",
            "base_rate": 1.05,
        },
        "comic-relief": {
            "gender": "male",
            "age_group": "young-adult",
            "personality_traits": ["energetic", "playful"],
            "base_voice": "en-US-ChristopherNeural",
            "base_rate": 1.15,
            "base_pitch": 2,
        },
        "villain": {
            "gender": "male",
            "age_group": "adult",
            "personality_traits": ["sinister", "authoritative"],
            "base_voice": "en-US-GuyNeural",
            "base_rate": 0.9,
            "base_pitch": -5,
        },
        "mentor": {
            "gender": "male",
            "age_group": "elderly",
            "personality_traits": ["wise", "calm"],
            "base_voice": "en-US-GuyNeural",
            "base_rate": 0.85,
            "base_pitch": -8,
        },
    }
    
    # Available Edge TTS voices organized by gender and age
    VOICE_OPTIONS = {
        "female": {
            "young-adult": ["en-US-AriaNeural", "en-US-JennyNeural", "en-GB-SoniaNeural"],
            "adult": ["en-US-AriaNeural", "en-AU-NatashaNeural"],
            "child": ["en-US-JennyNeural"],
        },
        "male": {
            "young-adult": ["en-US-GuyNeural", "en-US-ChristopherNeural", "en-AU-WilliamNeural"],
            "adult": ["en-US-GuyNeural", "en-GB-RyanNeural"],
            "child": ["en-US-ChristopherNeural"],
            "elderly": ["en-GB-RyanNeural"],
        },
        "neutral": {
            "any": ["en-US-AriaNeural", "en-US-GuyNeural"],
        },
    }
    
    def __init__(self):
        """Initialize character voice mapper."""
        self.character_profiles: Dict[str, VoiceProfile] = {}
        self.detected_characters: List[str] = []
    
    def add_character(
        self,
        character_name: str,
        gender: str = "neutral",
        age_group: str = "young-adult",
        personality_traits: Optional[List[str]] = None,
        base_voice: Optional[str] = None,
        base_rate: float = 1.0,
        base_pitch: float = 0.0,
    ) -> VoiceProfile:
        """
        Register a character with voice profile.
        
        Args:
            character_name: Name of character
            gender: "male", "female", or "neutral"
            age_group: "child", "young-adult", "adult", "elderly"
            personality_traits: List of traits (e.g., ["sarcastic", "energetic"])
            base_voice: Specific Edge TTS voice to use
            base_rate: Speech rate multiplier (0.5-2.0)
            base_pitch: Pitch offset (-20 to +20)
        
        Returns:
            VoiceProfile instance
        """
        # Auto-select voice if not specified
        if base_voice is None:
            base_voice = self._select_voice(gender, age_group)
        
        profile = VoiceProfile(
            character_name=character_name,
            base_voice=base_voice,
            gender=gender,
            age_group=age_group,
            personality_traits=personality_traits or [],
            base_rate=base_rate,
            base_pitch=base_pitch,
            voice_variants=self._create_voice_variants(gender, age_group),
        )
        
        self.character_profiles[character_name] = profile
        if character_name not in self.detected_characters:
            self.detected_characters.append(character_name)
        
        return profile
    
    def detect_characters_from_dialogue(
        self,
        dialogue_text: str,
        scene_description: str = ""
    ) -> List[str]:
        """
        Detect character names from dialogue text.
        
        Looks for patterns like:
        - "Character: dialogue"
        - Character names in italics or quotes
        
        Args:
            dialogue_text: Raw dialogue from scene
            scene_description: Scene context (optional)
        
        Returns:
            List of detected character names
        """
        detected = []
        
        # Pattern 1: "Name: dialogue"
        lines = dialogue_text.split("\n")
        for line in lines:
            if ":" in line:
                potential_name = line.split(":")[0].strip()
                # Filter out common non-names
                if (
                    len(potential_name) > 2
                    and len(potential_name) < 30
                    and potential_name[0].isupper()
                    and potential_name not in ["DIALOGUE", "ACTION", "EFFECTS"]
                ):
                    if potential_name not in detected:
                        detected.append(potential_name)
        
        # Auto-assign voices to new characters
        for char_name in detected:
            if char_name not in self.character_profiles:
                # Try to infer from context
                archetype = self._infer_archetype(char_name, scene_description)
                archetype_config = self.DEFAULT_ARCHETYPES.get(
                    archetype,
                    self.DEFAULT_ARCHETYPES["protagonist"]
                )
                self.add_character(
                    char_name,
                    gender=archetype_config["gender"],
                    age_group=archetype_config["age_group"],
                    personality_traits=archetype_config.get("personality_traits", []),
                    base_voice=archetype_config.get("base_voice"),
                    base_rate=archetype_config.get("base_rate", 1.0),
                    base_pitch=archetype_config.get("base_pitch", 0.0),
                )
        
        return detected
    
    def get_voice_for_character(
        self,
        character_name: str,
        emotional_state: str = "neutral"
    ) -> Dict:
        """
        Get voice parameters for a character in a specific emotional state.
        
        Args:
            character_name: Character to get voice for
            emotional_state: "happy", "angry", "sad", "surprised", "neutral", etc.
        
        Returns:
            Dict with voice and parameters:
            {
                "voice": "en-US-AriaNeural",
                "rate": 1.0,
                "pitch": 0.0,
                "description": "Female protagonist, determined"
            }
        """
        if character_name not in self.character_profiles:
            # Return default if character not found
            return self._get_default_voice()
        
        profile = self.character_profiles[character_name]
        
        # Base parameters
        rate = profile.base_rate
        pitch = profile.base_pitch
        
        # Apply emotional state modifiers
        emotional_mods = self._get_emotional_modifiers(emotional_state)
        rate *= emotional_mods["rate_multiplier"]
        pitch += emotional_mods["pitch_offset"]
        
        # Check for character-specific variant
        if emotional_state in profile.voice_variants:
            variant = profile.voice_variants[emotional_state]
            rate = variant.get("rate", rate)
            pitch = variant.get("pitch", pitch)
        
        return {
            "voice": profile.base_voice,
            "rate": max(0.5, min(2.0, rate)),
            "pitch": max(-20, min(20, pitch)),
            "character": character_name,
            "personality": ", ".join(profile.personality_traits),
            "description": f"{profile.gender.title()} {profile.age_group}",
        }
    
    def set_character_voice_variant(
        self,
        character_name: str,
        emotional_state: str,
        rate: float = 1.0,
        pitch: float = 0.0
    ):
        """
        Override voice parameters for a character in a specific emotional state.
        
        Args:
            character_name: Character name
            emotional_state: Emotional state key
            rate: Speech rate for this state
            pitch: Pitch for this state
        """
        if character_name in self.character_profiles:
            self.character_profiles[character_name].voice_variants[emotional_state] = {
                "rate": rate,
                "pitch": pitch,
            }
    
    def _select_voice(self, gender: str, age_group: str) -> str:
        """Select appropriate Edge TTS voice for gender/age."""
        gender = gender.lower()
        age_group = age_group.lower()
        
        if gender not in self.VOICE_OPTIONS:
            gender = "neutral"
        
        voices = self.VOICE_OPTIONS[gender]
        
        if age_group not in voices:
            # Fall back to first available
            age_group = list(voices.keys())[0]
        
        # Return first voice for this gender/age
        return voices[age_group][0]
    
    def _create_voice_variants(self, gender: str, age_group: str) -> Dict:
        """Create emotional voice variants for a character."""
        base_rate = 1.0
        base_pitch = 0.0
        
        return {
            "happy": {"rate": base_rate * 1.1, "pitch": base_pitch + 3},
            "angry": {"rate": base_rate * 1.2, "pitch": base_pitch + 5},
            "sad": {"rate": base_rate * 0.85, "pitch": base_pitch - 3},
            "surprised": {"rate": base_rate * 1.3, "pitch": base_pitch + 8},
            "calm": {"rate": base_rate * 0.9, "pitch": base_pitch - 2},
            "excited": {"rate": base_rate * 1.25, "pitch": base_pitch + 5},
            "confused": {"rate": base_rate * 0.95, "pitch": base_pitch + 1},
        }
    
    def _infer_archetype(self, character_name: str, context: str = "") -> str:
        """Infer character archetype from name and context."""
        name_lower = character_name.lower()
        context_lower = context.lower()
        
        # Simple heuristics
        if any(word in name_lower for word in ["hero", "main", "protagonist"]):
            return "protagonist"
        
        if any(word in name_lower for word in ["evil", "villain", "dark", "lord"]):
            return "villain"
        
        if any(word in name_lower for word in ["master", "sage", "elder", "prof"]):
            return "mentor"
        
        if any(word in name_lower for word in ["comic", "funny", "silly", "joke"]):
            return "comic-relief"
        
        if any(word in context_lower for word in ["female", "woman", "girl", "she"]):
            return "female-lead"
        
        return "protagonist"  # Default
    
    def _get_emotional_modifiers(self, emotional_state: str) -> Dict:
        """Get rate/pitch modifiers for emotional states."""
        modifiers = {
            "happy": {"rate_multiplier": 1.1, "pitch_offset": 3},
            "angry": {"rate_multiplier": 1.2, "pitch_offset": 5},
            "sad": {"rate_multiplier": 0.85, "pitch_offset": -3},
            "surprised": {"rate_multiplier": 1.3, "pitch_offset": 8},
            "calm": {"rate_multiplier": 0.9, "pitch_offset": -2},
            "excited": {"rate_multiplier": 1.25, "pitch_offset": 5},
            "confused": {"rate_multiplier": 0.95, "pitch_offset": 1},
            "neutral": {"rate_multiplier": 1.0, "pitch_offset": 0},
        }
        
        return modifiers.get(emotional_state, modifiers["neutral"])
    
    def _get_default_voice(self) -> Dict:
        """Get default voice when character not found."""
        return {
            "voice": "en-US-AriaNeural",
            "rate": 1.0,
            "pitch": 0.0,
            "character": "unknown",
            "personality": "neutral",
            "description": "Default voice",
        }
    
    def save_profiles(self, output_path: str):
        """Save character voice profiles to JSON."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        profiles_dict = {}
        for name, profile in self.character_profiles.items():
            profiles_dict[name] = asdict(profile)
        
        with open(output_path, "w") as f:
            json.dump(profiles_dict, f, indent=2)
    
    def load_profiles(self, input_path: str):
        """Load character voice profiles from JSON."""
        input_path = Path(input_path)
        
        if not input_path.exists():
            return
        
        with open(input_path, "r") as f:
            profiles_dict = json.load(f)
        
        for name, profile_data in profiles_dict.items():
            # Reconstruct VoiceProfile
            voice_variants = profile_data.pop("voice_variants", {})
            profile = VoiceProfile(**profile_data)
            profile.voice_variants = voice_variants
            self.character_profiles[name] = profile
    
    def to_json(self) -> str:
        """Serialize all character profiles to JSON string."""
        profiles_dict = {}
        for name, profile in self.character_profiles.items():
            profiles_dict[name] = asdict(profile)
        
        return json.dumps(profiles_dict, indent=2)


if __name__ == "__main__":
    # Test character voice mapper
    mapper = CharacterVoiceMapper()
    
    # Add a character manually
    mapper.add_character(
        "Alice",
        gender="female",
        age_group="young-adult",
        personality_traits=["intelligent", "sarcastic"],
    )
    
    # Detect characters from dialogue
    dialogue = """
    Alice: This is ridiculous!
    Bob: Calm down, it's not that bad.
    Alice: Are you kidding me?
    """
    
    detected = mapper.detect_characters_from_dialogue(dialogue)
    print(f"Detected characters: {detected}")
    
    # Get voice for character
    alice_voice = mapper.get_voice_for_character("Alice", emotional_state="angry")
    print(f"Alice's angry voice: {alice_voice}")
    
    # Get voice for auto-detected character
    bob_voice = mapper.get_voice_for_character("Bob", emotional_state="calm")
    print(f"Bob's calm voice: {bob_voice}")
