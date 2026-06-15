"""
Mood State Machine - Tracks emotional trajectory across sequential comic panels.

Handles:
- Mood accumulation and escalation
- Transitions between emotional states
- Intensity tracking
- Mood history for narrative analysis
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime
import json


@dataclass
class MoodSnapshot:
    """Single mood state at a point in time."""
    timestamp: str
    panel_index: int
    mood_type: str  # e.g., "comedic", "dramatic", "emotional"
    intensity: float  # 0.0 to 1.0
    reasoning: str
    accumulated_intensity: float  # Running total across sequence


class MoodState:
    """
    Tracks mood evolution across a sequence of comic panels.
    
    Supports:
    - Building tension/comedy as sequence continues
    - Detecting mood shifts (escalation, de-escalation, transitions)
    - Maintaining history for analysis
    - Predicting next mood (for lookahead rendering)
    """
    
    MOOD_RELATIONSHIPS = {
        # Comedic can escalate into comedic_peak or shift to comedic_resolved
        "comedic": ["comedic_escalating", "comedic_peak", "comedic_resolved"],
        "comedic_escalating": ["comedic_peak"],
        "comedic_peak": ["comedic_resolved", "comedic"],
        
        # Dramatic can build to climax or shift to resolution
        "dramatic": ["dramatic_building", "dramatic_climax", "dramatic_resolved"],
        "dramatic_building": ["dramatic_climax"],
        "dramatic_climax": ["dramatic_resolved"],
        
        # Emotional progression
        "emotional": ["emotional_intensifying", "emotional_peak", "emotional_release"],
        "emotional_intensifying": ["emotional_peak"],
        "emotional_peak": ["emotional_release"],
        
        # Tension arc
        "tense": ["tense_escalating", "tense_peak", "tense_released"],
        "tense_escalating": ["tense_peak"],
        "tense_peak": ["tense_released"],
        
        # Action pacing
        "action": ["action_accelerating", "action_climax"],
        "action_accelerating": ["action_climax"],
        
        # Neutral/peaceful states
        "contemplative": ["contemplative"],
        "peaceful": ["peaceful"],
    }
    
    def __init__(self, escalation_sensitivity: float = 0.7):
        """
        Initialize mood state machine.
        
        Args:
            escalation_sensitivity: How quickly mood intensifies (0.1-1.0)
        """
        self.escalation_sensitivity = escalation_sensitivity
        self.history: List[MoodSnapshot] = []
        self.current_mood_type: str = "neutral"
        self.current_intensity: float = 0.0
        self.accumulated_intensity: float = 0.0
        self.panel_index: int = 0
    
    def update(
        self,
        mood_type: str,
        new_intensity: float,
        reasoning: str
    ) -> MoodSnapshot:
        """
        Update mood state with new panel information.
        
        Args:
            mood_type: Primary emotion (e.g., "comedic", "dramatic")
            new_intensity: Raw intensity from scene (0.0-1.0)
            reasoning: Why this mood was detected
        
        Returns:
            MoodSnapshot with accumulated intensity
        """
        self.panel_index += 1
        
        # Calculate accumulated intensity
        # If same mood family, add to accumulation; if transition, partially reset
        if self._is_mood_related(self.current_mood_type, mood_type):
            # Same mood family - accumulate
            escalation_factor = self.escalation_sensitivity
            self.accumulated_intensity = min(
                1.0,
                self.accumulated_intensity + (new_intensity * escalation_factor * 0.1)
            )
        else:
            # Mood shift - weighted blend of new and old
            self.accumulated_intensity = (
                self.accumulated_intensity * 0.3 + new_intensity * 0.7
            )
        
        self.current_mood_type = mood_type
        self.current_intensity = new_intensity
        
        # Create snapshot
        snapshot = MoodSnapshot(
            timestamp=datetime.now().isoformat(),
            panel_index=self.panel_index,
            mood_type=mood_type,
            intensity=new_intensity,
            reasoning=reasoning,
            accumulated_intensity=self.accumulated_intensity,
        )
        
        self.history.append(snapshot)
        return snapshot
    
    def _is_mood_related(self, mood1: str, mood2: str) -> bool:
        """Check if two moods are in the same emotional family."""
        if mood1 == mood2:
            return True
        
        # Extract base mood (e.g., "comedic" from "comedic_escalating")
        base1 = mood1.split("_")[0]
        base2 = mood2.split("_")[0]
        
        return base1 == base2
    
    def get_voice_parameters(self) -> Dict[str, float]:
        """
        Get voice rendering parameters based on current mood state.
        
        Returns dict with:
            - rate_multiplier: speech speed (0.5-2.0)
            - pitch_offset: pitch adjustment (-20 to +20)
            - pause_duration: milliseconds between phrases
        """
        # Base parameters by mood
        mood_base = {
            "comedic": {"rate": 1.1, "pitch": 3, "pause": 600},
            "comedic_escalating": {"rate": 1.15, "pitch": 5, "pause": 500},
            "comedic_peak": {"rate": 1.2, "pitch": 8, "pause": 400},
            "comedic_resolved": {"rate": 0.95, "pitch": 0, "pause": 700},
            
            "dramatic": {"rate": 0.75, "pitch": -8, "pause": 1000},
            "dramatic_building": {"rate": 0.7, "pitch": -10, "pause": 1200},
            "dramatic_climax": {"rate": 0.65, "pitch": -12, "pause": 1500},
            "dramatic_resolved": {"rate": 0.8, "pitch": -5, "pause": 900},
            
            "emotional": {"rate": 0.8, "pitch": -3, "pause": 1000},
            "emotional_intensifying": {"rate": 0.75, "pitch": -5, "pause": 1200},
            "emotional_peak": {"rate": 0.7, "pitch": -8, "pause": 1400},
            "emotional_release": {"rate": 0.85, "pitch": 0, "pause": 800},
            
            "tense": {"rate": 0.9, "pitch": 0, "pause": 900},
            "tense_escalating": {"rate": 0.85, "pitch": 2, "pause": 800},
            "tense_peak": {"rate": 0.8, "pitch": 5, "pause": 700},
            "tense_released": {"rate": 1.0, "pitch": -3, "pause": 600},
            
            "action": {"rate": 1.2, "pitch": 5, "pause": 400},
            "action_accelerating": {"rate": 1.3, "pitch": 8, "pause": 300},
            "action_climax": {"rate": 1.4, "pitch": 10, "pause": 200},
            
            "contemplative": {"rate": 0.85, "pitch": -5, "pause": 1000},
            "peaceful": {"rate": 0.9, "pitch": -3, "pause": 800},
        }
        
        # Default if mood not found
        base_params = mood_base.get(
            self.current_mood_type,
            {"rate": 1.0, "pitch": 0, "pause": 600}
        )
        
        # Modulate by accumulated intensity (louder/more energetic if building)
        intensity_boost = (self.accumulated_intensity - 0.5) * 0.3  # -0.15 to +0.15
        
        return {
            "rate_multiplier": max(0.5, min(2.0, base_params["rate"] + intensity_boost)),
            "pitch_offset": base_params["pitch"],
            "pause_duration": int(base_params["pause"] * (1 - intensity_boost * 0.5)),
        }
    
    def get_mood_arc(self) -> List[Dict]:
        """Get full mood history as serializable list."""
        return [asdict(snapshot) for snapshot in self.history]
    
    def reset(self):
        """Reset mood state for new sequence."""
        self.history.clear()
        self.current_mood_type = "neutral"
        self.current_intensity = 0.0
        self.accumulated_intensity = 0.0
        self.panel_index = 0
    
    def to_json(self) -> str:
        """Serialize mood history to JSON."""
        return json.dumps(
            {
                "mood_arc": self.get_mood_arc(),
                "final_mood": self.current_mood_type,
                "final_intensity": self.current_intensity,
                "total_panels": self.panel_index,
            },
            indent=2
        )