from pathlib import Path
import subprocess
import os
from openai import OpenAI

def split_text_to_chunks(file_path, chunk_size=4096):
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    chunks = []
    while len(text) > chunk_size:
        # Find the last period (.) within the chunk size
        break_point = text.rfind('.', 0, chunk_size)
        if break_point == -1:
            # If no period is found, break at the chunk size limit
            break_point = chunk_size
        
        # Append the chunk and update the remaining text
        chunks.append(text[:break_point+1])
        text = text[break_point:].lstrip('. ')  # Remove leading spaces from the remaining text
    
    # Append any remaining text as the last chunk
    if text:
        chunks.append(text)
    
    return chunks

def merge_mp3_files(file_list, output_file):
    # Create a temporary file to hold the list of files
    with open("filelist.txt", "w") as filelist:
        for filename in file_list:
            filelist.write(f"file '{filename}'\n")
    
    # Call ffmpeg to merge the files
    command = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", "filelist.txt", "-c", "copy", output_file]
    subprocess.run(command, check=True)
    
    # Remove the temporary file
    os.remove("filelist.txt")

def process_text(input_file_path):
  client = OpenAI()

  # Example usage
  chunks = split_text_to_chunks(input_file_path)

  file_list = []

  # Print the chunks
  for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:\n{chunk}\n{'-'*40}")

    # Text to be converted to speech
    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice="nova",
        input=chunk
    ) as response:
        speech_file_path = Path(__file__).parent / f"outputs/es/openai_{i}.mp3"
        response.stream_to_file(speech_file_path)
        file_list.append(speech_file_path)

    output_file = Path(__file__).parent / "outputs/es/es.mp3"
    merge_mp3_files(file_list, output_file)

# process_text(Path(__file__).parent / "../output/es.en.txt")
process_text(Path(__file__).parent.parent / "awscli/input/translations/es.20240616_en.txt")