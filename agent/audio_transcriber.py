import os
import logging
import soundfile as sf
import librosa
from transformers import pipeline

logger = logging.getLogger(__name__)

class LocalTranscriber:
    def __init__(self):
        self.transcriber = None
        self.model_name = "openai/whisper-base" # Small, fast, open-source model (~300MB download once)
        self.is_loaded = False

    def load_model(self):
        if not self.is_loaded:
            logger.info(f"Loading local open-source Whisper model: {self.model_name}...")
            # We use device='cpu' to ensure it runs everywhere, or specify device=0 if you have a configured GPU
            self.transcriber = pipeline("automatic-speech-recognition", model=self.model_name)
            self.is_loaded = True
            logger.info("Local Whisper model loaded successfully.")

    def transcribe(self, audio_file_path: str) -> str:
        """
        Reads an OGG/WAV file locally and transcribes it using open-source Whisper.
        """
        try:
            self.load_model()
            
            # 1. Read the audio file
            audio_data, sample_rate = sf.read(audio_file_path)
            
            # 2. Whisper expects exactly 16000 Hz sample rate and mono channel
            if len(audio_data.shape) > 1:
                # Convert stereo to mono by averaging channels
                audio_data = audio_data.mean(axis=1)
                
            if sample_rate != 16000:
                # Resample to 16000 Hz using librosa
                audio_data = librosa.resample(y=audio_data, orig_sr=sample_rate, target_sr=16000)

            # 3. Transcribe using the local model
            logger.info(f"Transcribing {audio_file_path} locally (transcribe mode)...")
            
            # Explicitly set task to 'transcribe' and enable timestamps for long audio
            result = self.transcriber(
                {"sampling_rate": 16000, "raw": audio_data},
                generate_kwargs={"task": "transcribe"},
                return_timestamps=True # Critical for >30 second audio
            )
            
            return result.get("text", "").strip()
            
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            return f"Error during local transcription: {str(e)}"

# Global instance
local_transcriber = LocalTranscriber()
