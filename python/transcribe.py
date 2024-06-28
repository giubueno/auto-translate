import whisper
import json

def transcribe_audio_to_json(audio_file_path):
    ''' 
    Transcribe an audio file using the base model and return the transcription with timestamps.
    Returns the transcription in JSON format.
    {
        "text": "Hello, this is a test.",
        "segments": [
            {
                "id": 0,
                "seek": 0,
                "start": 0.0,
                "end": 2.5,
                "text": "Hello, this is a test.",
                "tokens": [50364, 2159, 11, 341, 307, 257, 1332, 13],
                "temperature": 0.0,
                "avg_logprob": -0.450,
                "compression_ratio": 1.2,
                "no_speech_prob": 0.1,
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "this", "start": 0.5, "end": 0.8},
                    {"word": "is", "start": 0.8, "end": 1.0},
                    {"word": "a", "start": 1.0, "end": 1.1},
                    {"word": "test", "start": 1.1, "end": 1.5}
                ]
            }
        ],
        "language": "en"
    }
    '''    
    # Load the Whisper model
    model = whisper.load_model("base")

    # Transcribe the audio file
    result = model.transcribe(audio_file_path, word_timestamps=True)

    # Convert the result to JSON format
    result_json = json.dumps(result, indent=4)

    return result_json

# Example usage
# audio_file_path = "./inputs/output.mp3"
# transcription_json = transcribe_audio_to_json(audio_file_path)
# print(transcription_json)




# Load processor
processor = AutoProcessor.from_pretrained("tensorspeech/tts-tacotron2-baker-ch")

# Load Tacotron2 model
tacotron2 = TFAutoModel.from_pretrained("tensorspeech/tts-tacotron2-baker-ch")

# Load MelGAN model
melgan = TFAutoModel.from_pretrained("tensorspeech/tts-mb_melgan-baker-ch")

# Prepare input text
input_text = "Hello, welcome to TensorFlow TTS."

# Convert text to sequence
input_ids = processor.text_to_sequence(input_text)

# Run Tacotron2 model to get mel spectrogram
_, mel_outputs, _, _ = tacotron2.inference(
    input_ids=tf.expand_dims(tf.convert_to_tensor(input_ids, dtype=tf.int32), 0),
    input_lengths=tf.convert_to_tensor([len(input_ids)], tf.int32),
    speaker_ids=tf.convert_to_tensor([0], dtype=tf.int32)
)

# Run MelGAN model to get waveform
audio = melgan.inference(mel_outputs)[0, :, 0]

# Save the audio to a WAV file first
wav_path = "output.wav"
sf.write(wav_path, audio.numpy(), 22050, "PCM_16")

# Convert WAV to MP3
mp3_path = "output.mp3"
audio_segment = AudioSegment.from_wav(wav_path)
audio_segment.export(mp3_path, format="mp3")

print(f"MP3 file saved at {mp3_path}")

