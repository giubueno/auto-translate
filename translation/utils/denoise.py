"""Post-processing audio denoise using ffmpeg filters."""
import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def _get_duration(file_path):
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    return float(info['format']['duration'])


def _build_filter_chain(rnnoise_model_path, duration):
    """Build the ffmpeg audio filter chain string."""
    filters = []

    if rnnoise_model_path and os.path.isfile(rnnoise_model_path):
        filters.append(f"arnndn=m={rnnoise_model_path}")
    elif rnnoise_model_path:
        logger.warning("RNNoise model not found at %s, skipping denoise", rnnoise_model_path)

    # Conservative silence trim from the end
    filters.append(
        "silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.2:stop_threshold=-35dB"
    )

    # Fade-out applied at the very end (duration will be recalculated after trim)
    # Use a placeholder; actual fade is applied in a second pass or estimated
    fade_start = max(0, duration - 0.03)
    filters.append(f"afade=t=out:st={fade_start:.4f}:d=0.03")

    return ",".join(filters)


def clean_audio(input_path, output_path, rnnoise_model_path=None):
    """
    Apply denoise, silence trim, and fade-out to an audio file.

    :param input_path: Path to input WAV file
    :param output_path: Path to write cleaned WAV file (can be same as input)
    :param rnnoise_model_path: Path to RNNoise model file. Falls back to
        RNNOISE_MODEL_PATH env var if None.
    :return: True on success, False on failure
    """
    if rnnoise_model_path is None:
        rnnoise_model_path = os.environ.get('RNNOISE_MODEL_PATH')

    try:
        input_duration = _get_duration(input_path)
    except FileNotFoundError:
        logger.error("ffmpeg/ffprobe not found. Skipping denoise.")
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
        logger.error("ffmpeg not found. Skipping denoise.")
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
        logger.info("Denoise complete: %.2fs -> %.2fs (saved %.2fs)", input_duration, output_duration, savings)
    except Exception:
        logger.info("Denoise complete (could not measure output duration)")

    return True


def _cleanup_temp(path):
    """Remove a temp file if it exists."""
    try:
        os.unlink(path)
    except OSError:
        pass
