import argparse
from pathlib import Path
import os
from utils.translation import translate_text

def split_text_to_chunks(file_path, chunk_size=4096):
    chunks = []

    with open(file_path, 'r', encoding='utf-8') as file:
        chunks = file.readlines()

    return chunks

def execute(language, original_file_path):
    output_path = Path(f"inputs/texts/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_text_to_chunks(original_file_path)

    filename = os.path.basename(original_file_path)

    # Save the translated texts
    with open(f"{output_path}/{filename}", "w") as file:
        for chunk in chunks:
            translated_texts = translate_text(chunk, source_language='en', target_language=language)
            file.write(translated_texts)

parser = argparse.ArgumentParser(description="Translate the texts in inputs/en to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
args = parser.parse_args()

execute(args.language, args.file)