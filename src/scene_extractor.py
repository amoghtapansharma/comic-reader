"""
Scene Extractor - Uses LLaVA vision model to analyze comic panels.

Extracts:
- Text/dialogue from panels
- Character actions and descriptions
- Visual effects and sound effects
"""

import ollama
from pathlib import Path
from typing import Dict, List
import base64


class SceneExtractor:
    """
    Analyzes comic panel images using LLaVA (vision model).
    
    LLaVA is a multimodal model that can:
    - Read handwritten text
    - Describe scenes and actions
    - Identify emotional cues from visual style
    """
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llava",
        timeout: int = 60
    ):
        """
        Initialize scene extractor.
        
        Args:
            ollama_host: Ollama server URL
            model: Model name (e.g., "llava")
            timeout: Request timeout in seconds
        """
        self.client = ollama.Client(host=ollama_host)
        self.model = model
        self.timeout = timeout
    
    def extract_from_file(self, image_path: str) -> Dict[str, str]:
        """
        Extract scene content from an image file.
        
        Args:
            image_path: Path to WEBP or image file
        
        Returns:
            Dict with keys:
            - dialogue: Extracted text/speech
            - action: Character actions and scene description
            - effects: Sound effects and visual emphasis
            - raw_response: Full model response
        """
        # Read and encode image
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Build prompt
        prompt = """Analyze this comic panel. Extract and return:

1. DIALOGUE: All visible text/dialogue (exactly as written, preserve punctuation)
2. ACTION: What's happening - character positions, gestures, scene description
3. EFFECTS: Sound effects, visual emphasis (speed lines, effects, etc.)

Be precise and concise. Format as:
DIALOGUE: [text here]
ACTION: [description here]
EFFECTS: [effects here]

If a section is not present, write "None"."""
        
        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                images=[image_data],
                stream=False,
                timeout=self.timeout,
            )
            
            full_response = response.get("response", "")
            
            # Parse response
            parsed = self._parse_response(full_response)
            parsed["raw_response"] = full_response
            
            return parsed
        
        except Exception as e:
            raise RuntimeError(f"LLaVA inference failed: {str(e)}")
    
    def extract_from_batch(self, image_paths: List[str]) -> List[Dict[str, str]]:
        """
        Extract scenes from multiple images.
        
        Args:
            image_paths: List of image file paths
        
        Returns:
            List of extraction results
        """
        results = []
        for i, path in enumerate(image_paths):
            print(f"Extracting scene {i+1}/{len(image_paths)}...", end=" ", flush=True)
            result = self.extract_from_file(path)
            results.append(result)
            print("done")
        return results
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """Parse LLaVA response into structured format."""
        parsed = {
            "dialogue": "",
            "action": "",
            "effects": "",
        }
        
        lines = response.split("\n")
        current_key = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("DIALOGUE:"):
                current_key = "dialogue"
                parsed["dialogue"] = line.replace("DIALOGUE:", "").strip()
            elif line.startswith("ACTION:"):
                current_key = "action"
                parsed["action"] = line.replace("ACTION:", "").strip()
            elif line.startswith("EFFECTS:"):
                current_key = "effects"
                parsed["effects"] = line.replace("EFFECTS:", "").strip()
            elif current_key and line and not line.startswith(("DIALOGUE:", "ACTION:", "EFFECTS:")):
                # Continuation of previous field
                parsed[current_key] += " " + line
        
        # Clean up "None" values
        for key in parsed:
            if parsed[key].lower() in ("none", ""):
                parsed[key] = ""
        
        return parsed