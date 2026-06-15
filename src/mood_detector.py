"""
Mood Detector - Classifies emotional tone and intensity of comic panels.

Uses LLaVA to analyze:
- Dialogue content and tone
- Visual style (shading, effects, panel composition)
- Action and pacing
- Narrative context

Integrates with MoodState for progressive mood buildup.
"""

import ollama
import base64
import re
from typing import Dict, Tuple
from pathlib import Path
from .mood_state import MoodState, MoodSnapshot


class MoodDetector:
    """
    Detects emotional mood/tone from comic panels using LLaVA.
    
    Classifies into categories:
    - comedic, dramatic, emotional, action, tense, contemplative, peaceful
    
    Also supports mood buildup via MoodState machine.
    """
    
    VALID_MOODS = {
        "comedic", "comedic_escalating", "comedic_peak", "comedic_resolved",
        "dramatic", "dramatic_building", "dramatic_climax", "dramatic_resolved",
        "emotional", "emotional_intensifying", "emotional_peak", "emotional_release",
        "tense", "tense_escalating", "tense_peak", "tense_released",
        "action", "action_accelerating", "action_climax",
        "contemplative", "peaceful", "neutral",
    }
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llava",
        timeout: int = 60,
        escalation_sensitivity: float = 0.7,
    ):
        """
        Initialize mood detector.
        
        Args:
            ollama_host: Ollama server URL
            model: Vision model name
            timeout: Request timeout
            escalation_sensitivity: How quickly mood escalates (0.1-1.0)
        """
        self.client = ollama.Client(host=ollama_host)
        self.model = model
        self.timeout = timeout
        self.mood_state = MoodState(escalation_sensitivity=escalation_sensitivity)
    
    def detect_from_file(
        self,
        image_path: str,
        scene_context: str = ""
    ) -> Tuple[str, float, str, MoodSnapshot]:
        """
        Detect mood from a comic panel image.
        
        Args:
            image_path: Path to image file
            scene_context: Optional context about the scene/sequence
        
        Returns:
            Tuple of:
            - mood_type (str): Primary emotional tone
            - intensity (float): 0.0-1.0
            - reasoning (str): Why this mood was detected
            - mood_snapshot: Full snapshot with accumulation
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Build prompt
        prompt = self._build_prompt(scene_context)
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                images=[image_data],
                stream=False,
                timeout=self.timeout,
            )
            
            full_response = response.get("response", "")
            mood_type, intensity, reasoning = self._parse_mood_response(full_response)
            
            # Update mood state with accumulation
            snapshot = self.mood_state.update(mood_type, intensity, reasoning)
            
            return mood_type, intensity, reasoning, snapshot
        
        except Exception as e:
            raise RuntimeError(f"Mood detection failed: {str(e)}")
    
    def detect_batch(self, image_paths: list) -> list:
        """
        Detect mood progression across multiple panels.
        
        Args:
            image_paths: List of panel image paths in sequence order
        
        Returns:
            List of tuples: (mood_type, intensity, reasoning, snapshot)
        """
        results = []
        context = ""
        
        for i, path in enumerate(image_paths):
            print(
                f"Analyzing mood {i+1}/{len(image_paths)}...",
                end=" ",
                flush=True
            )
            
            # Detect mood with context of previous panels
            mood_type, intensity, reasoning, snapshot = self.detect_from_file(
                path,
                scene_context=context
            )
            
            results.append((mood_type, intensity, reasoning, snapshot))
            
            # Update context for next iteration
            context = (
                f"Previous mood: {mood_type} (intensity: {intensity:.2f}). "
                f"Accumulated intensity: {snapshot.accumulated_intensity:.2f}. "
                f"Narrative arc: {reasoning}."
            )
            
            print(f"→ {mood_type} ({intensity:.2f})")
        
        return results
    
    def _build_prompt(self, scene_context: str = "") -> str:
        """Build LLaVA prompt for mood detection."""
        context_line = (
            f"Previous context: {scene_context}\n"
            if scene_context
            else ""
        )
        
        prompt = f"""{context_line}Analyze the emotional mood/tone of this comic panel.

Consider:
1. Dialogue - What tone are characters using? (sarcastic, excited, sad, confused?)
2. Visual style - Shading, effects, line weight? (dramatic vs. comedic)
3. Action - What's happening? (tension building, comedy punchline, emotional moment?)
4. Pacing - Panel composition suggests tempo?

Classify the PRIMARY mood as ONE of:
comedic, dramatic, emotional, action, tense, contemplative, peaceful

Return format (EXACTLY):
MOOD: [single mood word]
INTENSITY: [0.0 to 1.0]
REASONING: [1-2 sentences explaining the mood]

Examples:
MOOD: comedic
INTENSITY: 0.8
REASONING: Car sound effect "VROOOOM" and surprised character reaction suggests comedic climax.

MOOD: dramatic
INTENSITY: 0.6
REASONING: Serious character expression and inner monologue indicates contemplative mood.
"""
        return prompt
    
    def _parse_mood_response(self, response: str) -> Tuple[str, float, str]:
        """Parse LLaVA mood response into structured data."""
        mood_type = "neutral"
        intensity = 0.5
        reasoning = ""
        
        lines = response.split("\n")
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("MOOD:"):
                mood_str = line.replace("MOOD:", "").strip().lower()
                # Validate mood
                if mood_str in self.VALID_MOODS:
                    mood_type = mood_str
                else:
                    # Try to find closest match
                    for valid_mood in self.VALID_MOODS:
                        if valid_mood.startswith(mood_str.split("_")[0]):
                            mood_type = valid_mood
                            break
            
            elif line.startswith("INTENSITY:"):
                try:
                    intensity_str = line.replace("INTENSITY:", "").strip()
                    # Extract number (handle formats like "0.8" or "80%")
                    intensity_val = float(
                        intensity_str.replace("%", "").strip()
                    )
                    # Normalize to 0-1 range
                    if intensity_val > 1.0:
                        intensity_val /= 100.0
                    intensity = max(0.0, min(1.0, intensity_val))
                except ValueError:
                    intensity = 0.5
            
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
        
        return mood_type, intensity, reasoning
    
    def get_voice_params(self) -> Dict:
        """Get voice parameters for current mood state."""
        return self.mood_state.get_voice_parameters()
    
    def get_mood_arc(self) -> str:
        """Get mood history as JSON string."""
        return self.mood_state.to_json()
    
    def reset(self):
        """Reset mood detector for new sequence."""
        self.mood_state.reset()