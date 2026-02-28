"""
Post-processing audio denoise for Chatterbox TTS generated WAV files.

Fixes the "tail noise" artifact (low-level hiss/breathing) that Chatterbox TTS
appends to every generated clip using a three-stage ffmpeg filter pipeline:

1. RNNoise denoising (arnndn)
2. Conservative silence trim (silenceremove)
3. Smooth fade-out (afade)

Usage::

    from utils.denoise import clean_chatterbox_audio, AudioCleaner

    # Single file
    clean_chatterbox_audio("input.wav", "output.wav")

    # Batch processing
    cleaner = AudioCleaner(rnnoise_model_path="/path/to/model.rnnn")
    results = cleaner.clean_multiple("outputs/de/*.wav")

FastAPI integration::

    from fastapi import FastAPI, UploadFile
    from utils.denoise import clean_chatterbox_audio
    import tempfile, shutil

    app = FastAPI()

    @app.post("/denoise")
    async def denoise_audio(file: UploadFile):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
            shutil.copyfileobj(file.file, tmp_in)
            tmp_in_path = tmp_in.name
        out_path = tmp_in_path.replace(".wav", "_clean.wav")
        success = clean_chatterbox_audio(tmp_in_path, out_path)
        return {"success": success, "output": out_path}

Node.js subprocess wrapper::

    const { execSync } = require('child_process');

    function denoiseAudio(inputPath, outputPath) {
        const cmd = `python -c "from utils.denoise import clean_chatterbox_audio; `
            + `print(clean_chatterbox_audio('${inputPath}', '${outputPath}'))"`;
        const result = execSync(cmd, { encoding: 'utf-8' }).trim();
        return result === 'True';
    }
"""
import glob as glob_module
import json
import logging
import os
import subprocess
import tempfile
from typing import Optional

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


class AudioInputPath(BaseModel):
    """Validated input audio file path."""
    path: str

    @field_validator("path")
    @classmethod
    def must_exist(cls, v: str) -> str:
        if not os.path.isfile(v):
            raise ValueError(f"Input audio file does not exist: {v}")
        return v


class AudioOutputPath(BaseModel):
    """Validated output audio file path."""
    path: str

    @field_validator("path")
    @classmethod
    def parent_must_exist(cls, v: str) -> str:
        parent = os.path.dirname(v)
        if parent and not os.path.isdir(parent):
            raise ValueError(f"Output directory does not exist: {parent}")
        return v


class DenoiseResult(BaseModel):
    """Result of a denoise operation."""
    success: bool
    input_path: str
    output_path: str
    input_duration: Optional[float] = None
    output_duration: Optional[float] = None
    duration_saved: Optional[float] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    return float(info['format']['duration'])


def _build_filter_chain(rnnoise_model_path: Optional[str], duration: float) -> str:
    """Build the ffmpeg audio filter chain string."""
    filters: list[str] = []

    if rnnoise_model_path and os.path.isfile(rnnoise_model_path):
        filters.append(f"arnndn=m={rnnoise_model_path}")
    elif rnnoise_model_path:
        logger.warning("RNNoise model not found at %s, skipping denoise", rnnoise_model_path)

    # Conservative silence trim from the end
    filters.append(
        "silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.2:stop_threshold=-35dB"
    )

    # Fade-out applied at the very end
    fade_start = max(0, duration - 0.03)
    filters.append(f"afade=t=out:st={fade_start:.4f}:d=0.03")

    return ",".join(filters)


def _cleanup_temp(path: str) -> None:
    """Remove a temp file if it exists."""
    try:
        os.unlink(path)
    except OSError:
        pass


def _convert_to_wav(input_path: str) -> Optional[str]:
    """
    Convert a non-WAV audio file to WAV format.

    :param input_path: Path to the input audio file
    :return: Path to the temporary WAV file, or None on failure
    """
    tmp_fd, tmp_wav = tempfile.mkstemp(suffix='.wav')
    os.close(tmp_fd)

    try:
        subprocess.run(
            ['ffmpeg', '-i', input_path, '-acodec', 'pcm_s16le', '-ar', '44100', '-y', tmp_wav],
            check=True, capture_output=True
        )
        return tmp_wav
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Failed to convert %s to WAV: %s", input_path, e)
        _cleanup_temp(tmp_wav)
        return None


def _is_wav(file_path: str) -> bool:
    """Check if a file is a WAV file by extension."""
    return os.path.splitext(file_path)[1].lower() == '.wav'


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def clean_chatterbox_audio(input_path: str, output_path: str,
                           rnnoise_model_path: Optional[str] = None) -> bool:
    """
    Apply denoise, silence trim, and fade-out to a Chatterbox TTS audio file.

    Pipeline (in order):
      1. RNNoise denoising: ``arnndn=m=model_rnnoise=0.8``
      2. Conservative silence trim: ``silenceremove=...stop_threshold=-35dB``
      3. Smooth fade-out: ``afade=t=out:st=<calculated>:d=0.03``

    Handles non-WAV inputs by converting to WAV first.

    :param input_path: Path to input audio file (WAV, MP3, FLAC, OGG, etc.)
    :param output_path: Path to write cleaned WAV file (can be same as input)
    :param rnnoise_model_path: Path to RNNoise model file. Falls back to
        ``RNNOISE_MODEL_PATH`` env var if None.
    :return: True on success, False on failure

    Node.js subprocess wrapper example::

        const { execSync } = require('child_process');
        function denoiseAudio(inputPath, outputPath) {
            const cmd = `python -c "from utils.denoise import clean_chatterbox_audio; `
                + `print(clean_chatterbox_audio('${inputPath}', '${outputPath}'))"`;
            return execSync(cmd, { encoding: 'utf-8' }).trim() === 'True';
        }
    """
    if rnnoise_model_path is None:
        rnnoise_model_path = os.environ.get('RNNOISE_MODEL_PATH')

    # Handle non-WAV inputs by converting to WAV first
    converted_wav: Optional[str] = None
    working_input = input_path

    if not _is_wav(input_path):
        logger.info("Non-WAV input detected (%s), converting to WAV first", input_path)
        converted_wav = _convert_to_wav(input_path)
        if converted_wav is None:
            return False
        working_input = converted_wav

    try:
        return _process_audio(working_input, output_path, rnnoise_model_path)
    finally:
        if converted_wav:
            _cleanup_temp(converted_wav)


def _process_audio(input_path: str, output_path: str,
                   rnnoise_model_path: Optional[str]) -> bool:
    """Internal processing pipeline on a WAV file."""
    try:
        input_duration = _get_duration(input_path)
    except FileNotFoundError:
        logger.error("ffmpeg/ffprobe not found. Install ffmpeg: https://ffmpeg.org/download.html")
        return False
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError) as e:
        logger.error("Failed to probe audio duration: %s", e)
        return False

    use_rnnoise = rnnoise_model_path and os.path.isfile(rnnoise_model_path)
    filter_chain = _build_filter_chain(rnnoise_model_path, input_duration)

    # Write to a temp file first, then replace output
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.wav')
    os.close(tmp_fd)

    try:
        cmd = [
            'ffmpeg', '-i', input_path,
            '-af', filter_chain,
            '-y', tmp_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        logger.error("ffmpeg not found. Install ffmpeg: https://ffmpeg.org/download.html")
        _cleanup_temp(tmp_path)
        return False
    except subprocess.CalledProcessError:
        if use_rnnoise:
            # Retry without arnndn (filter may not be supported)
            logger.warning("arnndn filter failed, retrying without RNNoise denoise")
            fallback_chain = _build_filter_chain(None, input_duration)
            try:
                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-af', fallback_chain,
                    '-y', tmp_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.error("ffmpeg fallback also failed: %s", e)
                _cleanup_temp(tmp_path)
                return False
        else:
            logger.error("ffmpeg filter chain failed")
            _cleanup_temp(tmp_path)
            return False

    # Now apply precise fade-out based on actual trimmed duration
    try:
        trimmed_duration = _get_duration(tmp_path)
    except (subprocess.CalledProcessError, KeyError, json.JSONDecodeError):
        # If we can't probe, just use the file as-is
        os.replace(tmp_path, output_path)
        logger.info("Denoise complete (fade skipped): %.2fs -> unknown", input_duration)
        return True

    fade_start = max(0, trimmed_duration - 0.03)
    tmp_fd2, tmp_path2 = tempfile.mkstemp(suffix='.wav')
    os.close(tmp_fd2)

    try:
        cmd = [
            'ffmpeg', '-i', tmp_path,
            '-af', f"afade=t=out:st={fade_start:.4f}:d=0.03",
            '-y', tmp_path2
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        os.replace(tmp_path2, output_path)
        _cleanup_temp(tmp_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fade failed, use the trimmed version without precise fade
        os.replace(tmp_path, output_path)
        _cleanup_temp(tmp_path2)

    try:
        output_duration = _get_duration(output_path)
        savings = input_duration - output_duration
        logger.info("Denoise complete: %.2fs -> %.2fs (saved %.2fs)",
                     input_duration, output_duration, savings)
    except Exception:
        logger.info("Denoise complete (could not measure output duration)")

    return True


# Backward-compatible alias
clean_audio = clean_chatterbox_audio


# ---------------------------------------------------------------------------
# Class wrapper with batch processing
# ---------------------------------------------------------------------------

class AudioCleaner:
    """
    Class wrapper for Chatterbox TTS audio cleaning with batch support.

    :param rnnoise_model_path: Path to RNNoise model file. Falls back to
        ``RNNOISE_MODEL_PATH`` env var if None.

    Usage::

        cleaner = AudioCleaner(rnnoise_model_path="/path/to/model.rnnn")

        # Single file
        result = cleaner.clean("input.wav", "output.wav")
        print(result.success, result.duration_saved)

        # Batch processing
        results = cleaner.clean_multiple("outputs/de/*.wav")
        for r in results:
            print(f"{r.input_path}: saved {r.duration_saved:.2f}s")
    """

    def __init__(self, rnnoise_model_path: Optional[str] = None):
        self.rnnoise_model_path = rnnoise_model_path or os.environ.get('RNNOISE_MODEL_PATH')

    def clean(self, input_path: str, output_path: str) -> DenoiseResult:
        """
        Clean a single audio file and return a structured result.

        :param input_path: Path to input audio file
        :param output_path: Path to write cleaned audio file
        :return: DenoiseResult with success status and duration info
        """
        try:
            validated_input = AudioInputPath(path=input_path)
            validated_output = AudioOutputPath(path=output_path)
        except Exception as e:
            return DenoiseResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                error=str(e)
            )

        input_duration: Optional[float] = None
        try:
            input_duration = _get_duration(validated_input.path)
        except Exception:
            pass

        success = clean_chatterbox_audio(
            validated_input.path,
            validated_output.path,
            rnnoise_model_path=self.rnnoise_model_path
        )

        output_duration: Optional[float] = None
        duration_saved: Optional[float] = None
        if success:
            try:
                output_duration = _get_duration(validated_output.path)
                if input_duration is not None:
                    duration_saved = input_duration - output_duration
            except Exception:
                pass

        return DenoiseResult(
            success=success,
            input_path=validated_input.path,
            output_path=validated_output.path,
            input_duration=input_duration,
            output_duration=output_duration,
            duration_saved=duration_saved
        )

    def clean_multiple(self, glob_pattern: str) -> list[DenoiseResult]:
        """
        Batch process multiple audio files matching a glob pattern.

        Each file is cleaned in-place (output overwrites input).

        :param glob_pattern: Glob pattern to match audio files
            (e.g. ``"outputs/de/*.wav"``, ``"**/*.mp3"``)
        :return: List of DenoiseResult for each processed file
        """
        files = sorted(glob_module.glob(glob_pattern, recursive=True))
        if not files:
            logger.warning("No files matched pattern: %s", glob_pattern)
            return []

        logger.info("Batch processing %d files matching '%s'", len(files), glob_pattern)
        results: list[DenoiseResult] = []

        for file_path in files:
            logger.info("Processing: %s", file_path)
            result = self.clean(file_path, file_path)
            results.append(result)

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded
        total_saved = sum(r.duration_saved or 0 for r in results)
        logger.info("Batch complete: %d/%d succeeded, %.2fs total saved",
                     succeeded, len(results), total_saved)
        if failed:
            logger.warning("%d files failed processing", failed)

        return results
