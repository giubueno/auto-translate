from docx import Document
import re
from utils.tts import speak
from utils.translation import translate_text
import os
import argparse

def get_content(row, language="de"):
    content = ""

    if language != "de":
        cell = row.cells[1]
    else:
        cell = row.cells[2]

    for paragraph in cell.paragraphs:
        content += paragraph.text + "\n"

    if language != "de":
        content = translate_text(content, source_language='en', target_language=language)

    print(content)
    
    return content

def execute(doc_path, language="de"):
    files_path = f"outputs/{language}/files.txt"
    doc = Document(doc_path)

    # Create an empty list of files
    open(files_path, 'w').close()

    # Process each paragraph in the document
    table = doc.tables[0]

    print(f"Document has {len(doc.tables)} tables")
    print(f"Table has {len(table.rows)} rows")

    row_num = -1
    minutes = 0
    seconds = 0

    for row in table.rows:
        row_num += 1
        
        first_cell = row.cells[0]
        paragraph = first_cell.paragraphs[0]
        
        # check if the paragraph is similar to (01:29): or (01:29:00): using regex
        # parse something similar to (00:01): using regex
        match = re.match(r"\((\d{2}):(\d{2})\)", paragraph.text)        
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            minutes_str = str(minutes).zfill(2)
            seconds_str = str(seconds).zfill(2)
            path = f"{minutes_str}:{seconds_str}"
            print(path)
            content = get_content(row, language)
            try:
                speak(minutes, seconds, content, language=language, files_path=files_path)
            except Exception as e:
                print(e)
        else:
            print(f"Row {row_num} is not a time")
            print(paragraph.text)
            print("")

        # second_cell = row.cells[1]
        # 
    # concatenate all the mp3 files
    os.system(f"ffmpeg -f concat -safe 0 -i {files_path} -c copy outputs/{language}/output.mp3")

parser = argparse.ArgumentParser(description="Translate the texts in the docx file informed to the target language and save the files into outputs/{languae}")
parser.add_argument("-l", "--language", help="Language of the text", required=True)
parser.add_argument("-f", "--file", help="Original text file path", required=True)
args = parser.parse_args()
execute(args.file, args.language)