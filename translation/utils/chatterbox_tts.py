import threading

import torch
import torchaudio as ta
from pathlib import Path


class VoiceOverResult:
    def __init__(self, minutes, seconds, text, language="de", audio_prompt_path=None, files_path="outputs/de/output.mp3"):
        self.minutes = minutes
        self.seconds = seconds
        self.text = text
        self.language = language
        self.audio_prompt_path = audio_prompt_path
        self.files_path = files_path


def _patch_chatterbox_for_device(device):
    """
    Patch Chatterbox library to properly load checkpoints on non-CUDA devices.
    """
    import chatterbox.mtl_tts as mtl_tts
    from safetensors.torch import load_file as load_safetensors
    from chatterbox.models.t3 import T3
    from chatterbox.models.t3.modules.t3_config import T3Config
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.models.tokenizers import MTLTokenizer
    from chatterbox.models.voice_encoder import VoiceEncoder

    original_from_local = mtl_tts.ChatterboxMultilingualTTS.from_local

    @classmethod
    def patched_from_local(cls, ckpt_dir, device):
        ckpt_dir = Path(ckpt_dir)

        ve = VoiceEncoder()
        ve.load_state_dict(
            torch.load(ckpt_dir / "ve.pt", weights_only=True, map_location=device)
        )
        ve.to(device).eval()

        t3 = T3(T3Config.multilingual())
        t3_state = load_safetensors(ckpt_dir / "t3_mtl23ls_v2.safetensors", device=str(device))
        if "model" in t3_state.keys():
            t3_state = t3_state["model"][0]
        t3.load_state_dict(t3_state)
        t3.to(device).eval()

        s3gen = S3Gen()
        s3gen.load_state_dict(
            torch.load(ckpt_dir / "s3gen.pt", weights_only=True, map_location=device)
        )
        s3gen.to(device).eval()

        tokenizer = MTLTokenizer(
            str(ckpt_dir / "grapheme_mtl_merged_expanded_v1.json")
        )

        conds = None
        if (builtin_voice := ckpt_dir / "conds.pt").exists():
            conds = mtl_tts.Conditionals.load(builtin_voice, map_location=device).to(device)

        return cls(t3, s3gen, ve, tokenizer, device, conds=conds)

    mtl_tts.ChatterboxMultilingualTTS.from_local = patched_from_local


class ChatterboxVoiceCloner:
    def __init__(self, device=None):
        """
        Initialize Chatterbox voice cloner.

        :param device: Device to use (cuda, mps, or cpu). Auto-detected if None.
        """
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "cpu"  # Use CPU for MPS compatibility issues
            else:
                device = "cpu"

        self.device = device
        self._model = None
        self._multilingual_model = None
        self._patched = False
        self._lock = threading.Lock()
        print(f"Chatterbox will use device: {self.device}")

    def _ensure_patched(self):
        if not self._patched:
            _patch_chatterbox_for_device(self.device)
            self._patched = True

    @property
    def model(self):
        """Lazy load the English model."""
        if self._model is None:
            from chatterbox.tts import ChatterboxTTS
            print("Loading Chatterbox TTS model...")
            self._model = ChatterboxTTS.from_pretrained(device=self.device)
        return self._model

    @property
    def multilingual_model(self):
        """Lazy load the multilingual model."""
        if self._multilingual_model is None:
            self._ensure_patched()
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            print("Loading Chatterbox Multilingual TTS model...")
            self._multilingual_model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
        return self._multilingual_model

    def generate_speech(self, text, audio_prompt_path, output_path, language="en") -> str:
        """
        Generate speech using voice cloning from an audio sample.

        :param text: Text to convert to speech
        :param audio_prompt_path: Path to the audio file to clone voice from
        :param output_path: Path to save the generated audio
        :param language: Language code (en, de, fr, etc.)
        :return: Path to the generated audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Lock around model inference to ensure thread safety on GPU
        with self._lock:
            if language != "en":
                wav = self.multilingual_model.generate(
                    text,
                    audio_prompt_path=str(audio_prompt_path),
                    language_id=language
                )
                sample_rate = self.multilingual_model.sr
            else:
                wav = self.model.generate(
                    text,
                    audio_prompt_path=str(audio_prompt_path)
                )
                sample_rate = self.model.sr

            # Save WAV while still holding the lock (uses GPU tensors)
            wav_output = output_path.with_suffix('.wav')
            ta.save(str(wav_output), wav, sample_rate)

        # ffmpeg conversion runs outside the lock so it can overlap with the next inference
        if output_path.suffix.lower() == '.mp3':
            import subprocess
            subprocess.run([
                'ffmpeg', '-i', str(wav_output),
                '-codec:a', 'libmp3lame', '-qscale:a', '2',
                '-y', str(output_path)
            ], check=True, capture_output=True)
            wav_output.unlink()  # Remove temp WAV file
            print(f"Speech generated and saved to: {output_path}")
            return str(output_path)
        else:
            print(f"Speech generated and saved to: {wav_output}")
            return str(wav_output)


def voice_over_chatterbox(minutes, seconds, text, audio_prompt_path, language="de",
                          files_path="outputs/de/files.txt", cloner=None) -> VoiceOverResult:
    """
    Generate voice over using Chatterbox with timestamp tracking.

    :param minutes: Timestamp minutes
    :param seconds: Timestamp seconds
    :param text: Text to convert to speech
    :param audio_prompt_path: Path to the audio sample for voice cloning
    :param language: Target language code
    :param files_path: Path to the files manifest
    :param cloner: Optional ChatterboxVoiceCloner instance
    :return: VoiceOverResult object
    """
    if cloner is None:
        cloner = ChatterboxVoiceCloner()

    output_path = Path(f"outputs/{language}")
    output_path.mkdir(parents=True, exist_ok=True)

    # Format minutes and seconds as two-digit numbers
    minutes_str = str(minutes).zfill(2)
    seconds_str = str(seconds).zfill(2)
    speech_file_path = Path(__file__).parent.parent / f"{output_path}/{minutes_str}{seconds_str}.mp3"

    if speech_file_path.exists():
        print(f"File {speech_file_path} already exists")
    else:
        cloner.generate_speech(text, audio_prompt_path, str(speech_file_path), language)

    # Append the file path to the files.txt
    with open(files_path, 'a') as file:
        file.write(f"file '{speech_file_path}'\n")

    result = VoiceOverResult(minutes, seconds, text, language, audio_prompt_path, speech_file_path)

    return result
