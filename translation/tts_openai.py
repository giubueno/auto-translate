from pathlib import Path
import subprocess
import os
from openai import OpenAI
import argparse
import time

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

    # remove the individual files
    for filename in file_list:
        os.system(f"rm {filename}")

def process_text(input_file_path, language="es", voice="echo"):
    ''' Process the text in the input file and convert it to speech using OpenAI's API '''
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
            voice=voice,
            input=chunk
        ) as response:
            speech_file_path = Path(__file__).parent / f"outputs/{language}/openai_{i}.mp3"
            response.stream_to_file(speech_file_path)
            file_list.append(speech_file_path)
        
        # wait 10 seconds to avoid rate limiting
        time.sleep(5)

    output_file = Path(__file__).parent / f"outputs/{language}/{language}.mp3"
    merge_mp3_files(file_list, output_file)

# Parse the command line arguments
parser = argparse.ArgumentParser(description="Convert text to speech using OpenAI's API")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Text file path", required=True)
parser.add_argument("-v", "--voice", help="OpenAI voice to be used", required=False, default="echo")
args = parser.parse_args()

process_text(args.file, args.language, args.voice)