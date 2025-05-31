from docx import Document
import re
from utils.tts import voice_over
from utils.translation import translate_text
import os
import argparse

def execute(doc_path, language="de", source_language="de"):
    files_path = f"outputs/{language}/files.txt"
    doc = Document(doc_path)

    print("language: ", language)

    # Create an empty list of files
    open(files_path, 'w').close()

    path = ""
    
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

        if language != "de":           
            content = translate_text(speech_text, source_language=source_language, target_language=language)
        else:
            content = speech_text
        try:
            voice_over(minutes, seconds, content, language=language, files_path=files_path)
            print("content: ", content)
            print("\n")
        except Exception as e:
            print(e)

    # concatenate all the mp3 files
    os.system(f"ffmpeg -f concat -safe 0 -i {files_path} -c copy outputs/{language}/output.mp3")

parser = argparse.ArgumentParser(description="Translate the texts in the docx file informed to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
parser.add_argument("-s", "--source_language", help="Source language of the text", required=False, default="de")
args = parser.parse_args()
execute(args.file, args.language, args.source_language)
