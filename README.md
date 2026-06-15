# Comic Reader with AI Scene Detection & Progressive Voice Narration

A Windows desktop application that reads handwritten comic scenes using vision AI, detects mood/tone that **builds progressively** as scenes continue, and generates human voice narration with character-specific voices.

## Features

- 🎨 **Scene Detection**: LLaVA vision model analyzes comic panels and extracts dialogue/text
- 🎭 **Progressive Mood Detection**: Emotional tone builds and evolves across sequential panels
- 🔊 **Character-Specific Voices**: Different characters get distinct voices, auto-detected from dialogue
- 📁 **Batch Processing**: Process multiple WEBP comics in sequence
- 💻 **Fully Offline**: Uses local Ollama LLM (no API calls except TTS which needs internet)
- 📊 **Mood State Machine**: Tracks emotion arc with accumulation
- 🎬 **Output**: Generates MP3 with narration + JSON metadata

## Features in Detail

### Progressive Mood Buildup
Mood doesn't reset per panel—it accumulates:
```
Panel 1: "comedic" (intensity 0.5)
Panel 2: "comedic_escalating" (intensity 0.7) — buildup
Panel 3: "comedic_peak" (intensity 0.9) — climax
Panel 4: "comedic_resolved" (intensity 0.3) — release
```

### Character-Specific Voices
Each character has their own voice profile that adapts to emotional context:
```
Alice (female, intelligent, sarcastic):
  - Calm: "en-US-AriaNeural", rate 0.9, pitch -2
  - Angry: "en-US-AriaNeural", rate 1.2, pitch +5
  - Surprised: "en-US-AriaNeural", rate 1.3, pitch +8

Bob (male, comic relief):
  - Base: "en-US-ChristopherNeural", rate 1.15, pitch +2
  - Happy: rate 1.2, pitch +4
```

## Requirements

- **Windows 10/11**
- **Python 3.10+**
- **Ollama** with LLaVA model (`ollama pull llava`)
- **ffmpeg** (for audio processing)
- **Internet connection** (for Edge TTS only)

## Installation

```bash
# 1. Install Ollama from https://ollama.ai
# 2. Pull LLaVA model
ollama pull llava

# 3. Clone repo and install Python dependencies
git clone https://github.com/amoghtapansharma/comic-reader.git
cd comic-reader
pip install -r requirements.txt

# 4. Install ffmpeg (via chocolatey)
choco install ffmpeg
```

## Usage

```bash
# Basic usage - single comic
python comic_reader.py --input comic.webp --output comic_narrated.mp3

# Batch process with mood accumulation across files
python comic_reader.py --input ./comics --output ./output --batch

# Custom voice preferences
python comic_reader.py --input comic.webp --output comic.mp3 --voice female --language en-GB

# Show mood history and character voices
python comic_reader.py --input comic.webp --output comic.mp3 --show-analysis
```

## Architecture

1. **Scene Extractor** (LLaVA): Analyzes image, extracts text/dialogue, describes action
2. **Character Voice Mapper**: Detects characters, assigns/loads voice profiles
3. **Progressive Mood Detector** (LLaVA + state machine): 
   - Tracks emotional trajectory across panels
   - Accumulates mood intensity and type
   - Adjusts voice parameters based on mood state
4. **Voice Generator** (Edge TTS): Converts text with character-specific + mood-aware parameters
5. **Audio Processor** (ffmpeg): Merges narration segments with mood-aware pauses

## Config

Edit `config.yaml` to customize:
- Ollama model and host
- Default voice preferences
- Mood progression sensitivity
- Mood-to-speed/pitch mapping
- Character archetype definitions
- Output quality

## File Structure

```
comic-reader/
├── README.md
├── requirements.txt
├── config.yaml
├── comic_reader.py                    # Main CLI
├── src/
│   ├── __init__.py
│   ├── scene_extractor.py             # LLaVA vision integration
│   ├── mood_detector.py               # Progressive tone classification
│   ├── mood_state.py                  # Mood state machine with accumulation
│   ├── character_voice_mapper.py      # Character voice profiles & auto-detection
│   ├── voice_generator.py             # Edge TTS wrapper
│   └── audio_processor.py             # ffmpeg integration
├── character_profiles.json            # Saved character voices (auto-generated)
└── examples/
    └── sample_comic_sequence/
        ├── panel_1.webp
        ├── panel_2.webp
        └── panel_3.webp
```

## Performance Notes

- First LLaVA inference: ~30-60s (model loading)
- Subsequent inferences: ~5-15s per panel (depends on GPU)
- TTS generation: ~2-3s per 100 words
- Edge TTS requires internet but no API key needed
- Mood state maintained across batch processing
- Character profiles cached in memory

## Example Workflow

```
Input: comic_panels/ (3 WEBP files)
│
├─ Panel 1: "She seems spaced out. I want breakfast."
│  ├─ Characters detected: ["She", "I"] → Auto-assign voices
│  ├─ Mood: CONTEMPLATIVE (0.5 intensity)
│  ├─ Voice: Calm female voice, normal pace
│  └─ Output: panel_1_narration.mp3
│
├─ Panel 2: "Her body is here, but her mind seems to always be in outer space."
│  ├─ Previous mood: CONTEMPLATIVE (accumulate)
│  ├─ Mood: CONTEMPLATIVE_INTENSIFYING (0.7 intensity)
│  ├─ Voice: Same female, slightly slower, more concerned
│  └─ Output: panel_2_narration.mp3
│
└─ Panel 3: "VROOOOOOM!!" (car sound effect)
   ├─ Previous mood: CONTEMPLATIVE_INTENSIFYING → SHIFT
   ├─ Mood: COMEDIC_PEAK (0.9 intensity)
   ├─ Voice: Excited, comedic timing, faster delivery
   └─ Output: panel_3_narration.mp3

Final Output: comic_combined.mp3
  (All segments merged with mood-aware pauses)
```

## Troubleshooting

**Ollama not connecting**: Ensure `ollama serve` is running (default: localhost:11434)

**LLaVA too slow**: Check GPU drivers. CPU mode slower but works.

**TTS not working**: Verify internet connection; Edge TTS requires connectivity.

**WEBP not reading**: Install `Pillow[webp]` or ensure libwebp is available.

**Character voices not detected**: Check dialogue format: "Name: dialogue"

**Mood not progressing**: Ensure `--batch` flag is used for multiple files; mood state resets per single file by default.

## License

MIT