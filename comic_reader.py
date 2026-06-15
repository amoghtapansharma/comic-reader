"""
Main CLI entry point for Comic Reader.

Usage:
    python comic_reader.py --input comic.webp --output comic.mp3
    python comic_reader.py --input ./comics --output ./output --batch
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict
import sys

from src.scene_extractor import SceneExtractor
from src.mood_detector import MoodDetector
from src.character_voice_mapper import CharacterVoiceMapper
from src.voice_generator import VoiceGenerator
from src.audio_processor import AudioProcessor


class ComicReader:
    """Main orchestrator for comic reading pipeline."""
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        ollama_model: str = "llava",
        default_voice: str = "en-US-AriaNeural",
        escalation_sensitivity: float = 0.7,
        verbose: bool = False,
    ):
        """Initialize Comic Reader."""
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self.verbose = verbose
        
        # Initialize components
        self.scene_extractor = SceneExtractor(
            ollama_host=ollama_host,
            model=ollama_model,
        )
        self.mood_detector = MoodDetector(
            ollama_host=ollama_host,
            model=ollama_model,
            escalation_sensitivity=escalation_sensitivity,
        )
        self.character_mapper = CharacterVoiceMapper()
        self.voice_generator = VoiceGenerator(voice=default_voice)
        self.audio_processor = AudioProcessor()
        
        self.temp_audio_files: List[str] = []
    
    def process_single(
        self,
        input_path: str,
        output_path: str,
        show_analysis: bool = False,
    ) -> Dict:
        """
        Process a single comic panel.
        
        Args:
            input_path: Path to WEBP file
            output_path: Output MP3 path
            show_analysis: Print mood/character analysis
        
        Returns:
            Processing results dict
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.verbose:
            print(f"Processing: {input_path}")
        
        # Extract scene
        print("[1/3] Extracting scene...", end=" ", flush=True)
        scene = self.scene_extractor.extract_from_file(str(input_path))
        print("done")
        
        # Detect characters and assign voices
        print("[2/3] Detecting characters and mood...", end=" ", flush=True)
        self.character_mapper.detect_characters_from_dialogue(
            scene["dialogue"],
            scene["action"]
        )
        mood_type, intensity, reasoning, snapshot = self.mood_detector.detect_from_file(
            str(input_path),
            scene_context=scene["action"]
        )
        print("done")
        
        # Generate narration
        print("[3/3] Generating audio...", end=" ", flush=True)
        
        # Build full narration text
        narration_text = self._build_narration(scene)
        
        # Detect primary character from dialogue
        characters = self.character_mapper.detected_characters
        primary_character = characters[0] if characters else "narrator"
        
        # Get voice parameters
        voice_params = self.character_mapper.get_voice_for_character(
            primary_character,
            emotional_state=self._map_mood_to_emotion(mood_type)
        )
        
        mood_voice_params = self.mood_detector.get_voice_params()
        
        # Generate audio
        self.voice_generator.set_voice(voice_params["voice"])
        audio_file = self.voice_generator.generate(
            text=narration_text,
            output_path=str(output_path),
            rate_multiplier=mood_voice_params["rate_multiplier"],
            pitch_offset=mood_voice_params["pitch_offset"],
        )
        print("done")
        
        # Print analysis if requested
        if show_analysis:
            self._print_analysis(scene, mood_type, intensity, reasoning, voice_params)
        
        return {
            "input": str(input_path),
            "output": audio_file,
            "scene": scene,
            "mood": mood_type,
            "intensity": intensity,
            "characters": characters,
            "voice": voice_params["voice"],
        }
    
    def process_batch(\n        self,\n        input_dir: str,\n        output_dir: str,\n        show_analysis: bool = False,\n    ) -> List[Dict]:\n        \"\"\"\n        Process multiple comic panels in sequence (with mood accumulation).\n        \n        Args:\n            input_dir: Directory with WEBP files\n            output_dir: Output directory for MP3s\n            show_analysis: Print analysis for each panel\n        \n        Returns:\n            List of processing results\n        \"\"\"\n        input_dir = Path(input_dir)\n        output_dir = Path(output_dir)\n        output_dir.mkdir(parents=True, exist_ok=True)\n        \n        # Get all WEBP files\n        webp_files = sorted(input_dir.glob(\"*.webp\"))\n        if not webp_files:\n            print(f\"No WEBP files found in {input_dir}\")\n            return []\n        \n        print(f\"Found {len(webp_files)} panels to process\\n\")\n        \n        results = []\n        audio_files = []\n        pause_durations = []\n        \n        # Process each panel\n        for i, input_file in enumerate(webp_files):\n            print(f\"\\n=== Panel {i+1}/{len(webp_files)} ===\")\n            \n            # Process panel\n            result = self.process_single(\n                str(input_file),\n                str(output_dir / f\"panel_{i+1:03d}.mp3\"),\n                show_analysis=show_analysis,\n            )\n            \n            results.append(result)\n            audio_files.append(result[\"output\"])\n            \n            # Get mood-based pause duration\n            mood_params = self.mood_detector.get_voice_params()\n            pause_durations.append(mood_params[\"pause_duration\"])\n        \n        # Combine all audio files with pauses\n        print(\"\\n[Final] Combining audio segments...\", end=\" \", flush=True)\n        combined_output = str(output_dir / \"comic_combined.mp3\")\n        self.audio_processor.concatenate_with_pauses(\n            audio_files,\n            combined_output,\n            pause_durations=pause_durations,\n        )\n        print(\"done\")\n        \n        # Save metadata\n        metadata = {\n            \"total_panels\": len(webp_files),\n            \"combined_output\": combined_output,\n            \"panels\": results,\n            \"mood_arc\": json.loads(self.mood_detector.get_mood_arc()),\n            \"character_profiles\": json.loads(self.character_mapper.to_json()),\n        }\n        \n        metadata_file = output_dir / \"metadata.json\"\n        with open(metadata_file, \"w\") as f:\n            json.dump(metadata, f, indent=2)\n        \n        print(f\"\\n✓ Combined audio: {combined_output}\")\n        print(f\"✓ Metadata: {metadata_file}\")\n        \n        return results\n    \n    def _build_narration(self, scene: Dict[str, str]) -> str:\n        \"\"\"Build narration text from extracted scene.\"\"\"\n        parts = []\n        \n        if scene.get(\"dialogue\"):\n            parts.append(scene[\"dialogue\"])\n        \n        if scene.get(\"action\"):\n            parts.append(scene[\"action\"])\n        \n        if scene.get(\"effects\"):\n            # Describe effects\n            parts.append(f\"Sound: {scene['effects']}\")\n        \n        return \" \".join(filter(None, parts))\n    \n    def _map_mood_to_emotion(self, mood_type: str) -> str:\n        \"\"\"Map mood type to character emotional state.\"\"\"\n        mood_to_emotion = {\n            \"comedic\": \"excited\",\n            \"comedic_escalating\": \"excited\",\n            \"comedic_peak\": \"excited\",\n            \"comedic_resolved\": \"happy\",\n            \"dramatic\": \"calm\",\n            \"dramatic_building\": \"tense\",\n            \"dramatic_climax\": \"angry\",\n            \"dramatic_resolved\": \"calm\",\n            \"emotional\": \"sad\",\n            \"emotional_intensifying\": \"sad\",\n            \"emotional_peak\": \"sad\",\n            \"emotional_release\": \"calm\",\n            \"action\": \"excited\",\n            \"action_accelerating\": \"excited\",\n            \"action_climax\": \"excited\",\n            \"tense\": \"confused\",\n            \"tense_escalating\": \"angry\",\n            \"tense_peak\": \"angry\",\n            \"tense_released\": \"calm\",\n            \"contemplative\": \"calm\",\n            \"peaceful\": \"calm\",\n        }\n        return mood_to_emotion.get(mood_type, \"neutral\")\n    \n    def _print_analysis(self, scene: Dict, mood: str, intensity: float, reasoning: str, voice: Dict):\n        \"\"\"Print analysis for current panel.\"\"\"\n        print(\"\\n--- Scene Analysis ---\")\n        if scene.get(\"dialogue\"):\n            print(f\"Dialogue: {scene['dialogue'][:100]}...\")\n        print(f\"Action: {scene.get('action', 'N/A')[:100]}...\")\n        print(f\"\\n--- Mood Analysis ---\")\n        print(f\"Mood: {mood} (intensity: {intensity:.2f})\")\n        print(f\"Reasoning: {reasoning}\")\n        print(f\"\\n--- Voice ---\")\n        print(f\"Character: {voice['character']}\")\n        print(f\"Voice: {voice['voice']}\")\n        print(f\"Rate: {voice['rate']:.2f}x\")\n        print(f\"Pitch: {voice['pitch']:+.1f}\")\n\n\ndef main():\n    \"\"\"Main entry point.\"\"\"\n    parser = argparse.ArgumentParser(\n        description=\"Comic Reader - AI-powered comic narration\"\n    )\n    parser.add_argument(\n        \"--input\", \"-i\",\n        required=True,\n        help=\"Input WEBP file or directory of WEBP files\"\n    )\n    parser.add_argument(\n        \"--output\", \"-o\",\n        required=True,\n        help=\"Output MP3 file or directory\"\n    )\n    parser.add_argument(\n        \"--batch\", \"-b\",\n        action=\"store_true\",\n        help=\"Process directory with mood accumulation\"\n    )\n    parser.add_argument(\n        \"--ollama-host\",\n        default=\"http://localhost:11434\",\n        help=\"Ollama server host\"\n    )\n    parser.add_argument(\n        \"--ollama-model\",\n        default=\"llava\",\n        help=\"Ollama model to use\"\n    )\n    parser.add_argument(\n        \"--voice\",\n        default=\"en-US-AriaNeural\",\n        help=\"Default voice to use\"\n    )\n    parser.add_argument(\n        \"--show-analysis\", \"-a\",\n        action=\"store_true\",\n        help=\"Print detailed analysis for each panel\"\n    )\n    parser.add_argument(\n        \"--verbose\", \"-v\",\n        action=\"store_true\",\n        help=\"Verbose output\"\n    )\n    \n    args = parser.parse_args()\n    \n    # Initialize reader\n    reader = ComicReader(\n        ollama_host=args.ollama_host,\n        ollama_model=args.ollama_model,\n        default_voice=args.voice,\n        verbose=args.verbose,\n    )\n    \n    try:\n        # Check if input is directory or file\n        input_path = Path(args.input)\n        \n        if input_path.is_dir() or args.batch:\n            # Batch mode\n            results = reader.process_batch(\n                args.input,\n                args.output,\n                show_analysis=args.show_analysis,\n            )\n        else:\n            # Single file mode\n            result = reader.process_single(\n                args.input,\n                args.output,\n                show_analysis=args.show_analysis,\n            )\n            print(f\"\\n✓ Output saved to: {result['output']}\")\n    \n    except KeyboardInterrupt:\n        print(\"\\n\\nInterrupted by user\")\n        sys.exit(1)\n    except Exception as e:\n        print(f\"\\n\\n✗ Error: {str(e)}\")\n        if args.verbose:\n            import traceback\n            traceback.print_exc()\n        sys.exit(1)\n\n\nif __name__ == \"__main__\":\n    main()\n