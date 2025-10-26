from docx import Document
import re
from utils.tts import voice_over, VoiceOverResult
from utils.translation import translate_text
import os
import argparse
from audio_builder import AudioBuilder

def execute(doc_path, language="de", source_language="de"):
    os.makedirs(f"outputs/{language}", exist_ok=True)

    files_path = f"outputs/{language}/files.txt"
    doc = Document(doc_path)

    print("language: ", language)

    # Create an empty list of files
    open(files_path, 'w').close()

    path = ""

    voice_over_results: list[VoiceOverResult] = []

    audio_builder = AudioBuilder(language=language)
    
    # read each paragraph in the document
    for paragraph in doc.paragraphs:
        speech_text = paragraph.text
        if speech_text == "":
            continue

        match = re.match(r".*\((\d{2}):(\d{2})\):?", speech_text)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            minutes_str = str(minutes).zfill(2)
            seconds_str = str(seconds).zfill(2)
            path = f"{minutes_str}:{seconds_str}"
            print("time: ", path)
            continue

        if language != source_language:
            content = translate_text(speech_text, source_language=source_language, target_language=language)
        else:
            content = speech_text
        try:
            print("content: ", content)
            voice_over_result = voice_over(minutes, seconds, content, language=language, files_path=files_path)
            voice_over_results.append(voice_over_result)

        except Exception as e:
            print(e)

    # build the audio
    audio_builder.build(voice_over_results)

parser = argparse.ArgumentParser(description="Translate the texts in the docx file informed to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
parser.add_argument("-s", "--source_language", help="Source language of the text", required=False, default="de")
args = parser.parse_args()
execute(args.file, args.language, args.source_language)
