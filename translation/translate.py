import argparse
from pathlib import Path
import os
import boto3

def translate_text(text, source_language='en', target_language='es'):
    """
    Translate text from source language to target language using AWS Translate.

    :param text: Text to translate
    :param source_language: Source language code (e.g., 'en' for English)
    :param target_language: Target language code (e.g., 'es' for Spanish)
    :return: Translated text
    """
    translate = boto3.client(service_name='translate', region_name='us-east-1', use_ssl=True)
    result = translate.translate_text(Text=text, SourceLanguageCode=source_language, TargetLanguageCode=target_language)
    return result.get('TranslatedText')

def execute(language):
    output_path = Path(f"inputs/texts/{language}")
    # Create the output directory
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # list files in the inputs/texts/en directory
    files = os.listdir("inputs/texts/en")
    # sort the files
    files.sort()

    for file in files:
        # Read the text
        with open(f"inputs/texts/en/{file}", "r") as file:
            texts = file.readlines()

        # Merger list of strings into a single string
        texts = "".join(texts)
        translated_texts = translate_text(texts, source_language='en', target_language=language)

        # Save the translated texts
        with open(f"{output_path}/{os.path.basename(file.name)}", "w") as file:
            file.write(translated_texts)

parser = argparse.ArgumentParser(description="Translate the texts in inputs/en to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
args = parser.parse_args()

execute(args.language)