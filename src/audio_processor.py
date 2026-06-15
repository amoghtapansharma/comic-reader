"""
Audio Processor - Combines and processes audio files using ffmpeg.

Features:
- Merge multiple audio segments
- Add silence/pauses between segments
- Adjust audio levels
- Convert between formats
"""

import subprocess
from pathlib import Path
from typing import List, Optional
import os


class AudioProcessor:
    """
    Handles audio processing using ffmpeg.
    
    Can combine speech segments with pauses and adjust audio properties.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize audio processor.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable (uses system PATH if not found)
        """
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Verify ffmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"ffmpeg not found at {self.ffmpeg_path}. "
                "Please install ffmpeg: choco install ffmpeg"
            )
    
    def concatenate_with_pauses(
        self,
        audio_files: List[str],
        output_path: str,
        pause_durations: Optional[List[int]] = None,
        bitrate: str = "192k",
    ) -> str:
        """
        Concatenate multiple audio files with pauses between them.
        
        Args:
            audio_files: List of input MP3 file paths
            output_path: Output MP3 file path
            pause_durations: List of pause durations (ms) between files
            bitrate: Output bitrate (e.g., "192k")
        
        Returns:
            Path to output file
        """
        if not audio_files:
            raise ValueError("No audio files provided")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Default: 500ms pause between segments
        if pause_durations is None:
            pause_durations = [500] * (len(audio_files) - 1)
        
        # Create concat file
        concat_file = output_path.parent / "concat_list.txt"
        with open(concat_file, "w") as f:
            for i, audio_file in enumerate(audio_files):
                f.write(f"file '{Path(audio_file).resolve()}'\n")
                
                # Add silence after each file except the last
                if i < len(audio_files) - 1:
                    pause_ms = pause_durations[i] if i < len(pause_durations) else 500
                    f.write(f"file 'anullsrc=r=44100:cl=mono' (filter_complex '[0:a] atrim=0:{pause_ms/1000}')\n")
        
        # Use ffmpeg concat demuxer
        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame",
            "-b:a", bitrate,
            "-y",  # Overwrite output
            str(output_path),
        ]
        
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        finally:
            # Clean up concat file
            if concat_file.exists():
                concat_file.unlink()
        
        return str(output_path)
    
    def merge_audio_streams(
        self,
        primary_audio: str,
        secondary_audio: Optional[str] = None,
        output_path: str = "merged.mp3",
        primary_volume: float = 1.0,
        secondary_volume: float = 0.5,
        bitrate: str = "192k",
    ) -> str:
        """
        Merge two audio streams (e.g., narration + background music).
        
        Args:
            primary_audio: Main audio file (narration)
            secondary_audio: Background audio file (optional)
            output_path: Output MP3 file
            primary_volume: Volume level for primary (0.0-1.0)
            secondary_volume: Volume level for secondary (0.0-1.0)
            bitrate: Output bitrate
        
        Returns:
            Path to output file
        """
        if secondary_audio is None:
            # No secondary, just convert primary
            return self._convert_audio(primary_audio, output_path, bitrate)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use ffmpeg to mix audio
        cmd = [
            self.ffmpeg_path,
            "-i", primary_audio,
            "-i", secondary_audio,
            "-filter_complex",
            f"[0:a]volume={primary_volume}[a0];[1:a]volume={secondary_volume}[a1];[a0][a1]amix=inputs=2",
            "-c:a", "libmp3lame",
            "-b:a", bitrate,
            "-y",
            str(output_path),
        ]
        
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        
        return str(output_path)
    
    def _convert_audio(
        self,
        input_path: str,
        output_path: str,
        bitrate: str = "192k",
    ) -> str:
        """Convert audio to MP3 with specified bitrate."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-c:a", "libmp3lame",
            "-b:a", bitrate,
            "-y",
            str(output_path),
        ]
        
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        
        return str(output_path)
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get duration of audio file in seconds.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            Duration in seconds
        """
        cmd = [
            self.ffmpeg_path,
            "-i", audio_path,
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # Parse ffmpeg output
        for line in result.stderr.split("\n"):
            if "Duration:" in line:
                # Format: Duration: HH:MM:SS.ms
                time_str = line.split("Duration: ")[1].split(",")[0]
                parts = time_str.split(":")
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        
        return 0.0