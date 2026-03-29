You are an expert audio engineer and a Senior Python developer. I need a robust Python utility to fix the "tail noise" artifact in Chatterbox TTS generated WAV files.

PROBLEM: Chatterbox TTS adds low-level hiss/breathing noise at the end of every generated clip. Simple trimming amplifies it.

REQUIRED SOLUTION: Single function that processes input WAV → denoised, silence-trimmed, fade-out WAV.

EXACT PIPELINE (don't change the order or parameters):
1. RNNoise denoising: arnndn=m=model_rnnoise=0.8  
2. Conservative silence trim: silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.2:stop_threshold=-35dB  
3. Smooth fade-out: afade=t=out:st=0.08:d=0.03

FFMPEG COMMAND REFERENCE (implement exactly):
ffmpeg -i input.wav -af "arnndn=m=model_rnnoise=0.8,silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.2:stop_threshold=-35dB,afade=t=out:st=0.08:d=0.03" -y output.wav

REQUIREMENTS:
1. Python function `clean_chatterbox_audio(input_path: str, output_path: str) -> bool`
2. Uses subprocess.run(ffmpeg) with proper error handling
3. Validates input file exists, output succeeds
4. Logs duration savings (input vs output length)
5. Bonus: Class wrapper with batch processing: `clean_multiple(glob_pattern: str)`
6. Type hints + pydantic models for paths
7. Handles missing ffmpeg gracefully (install instructions)

INTEGRATION: 
- Make it importable for FastAPI endpoint
- Node.js subprocess wrapper example included in docstring

TEST CASE:
Input: 5s WAV with 800ms hiss tail → Output: 4.2s clean speech

Edge cases to handle:
- Very short clips (<500ms)
- Already clean files  
- Non-WAV inputs (convert to WAV first)

Write the complete, production-ready code with tests.
