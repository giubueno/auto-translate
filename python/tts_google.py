from gtts import gTTS
import os

# read the content of the file ../output/de.en.txt
with open('../output/de.en.txt', 'r') as file:
    # Text to be converted to speech
    text = file.read().replace('\n', '')

# Language in which you want to convert
language = 'de'

# Passing the text and language to the engine
speech = gTTS(text=text, lang=language, slow=True)

# Saving the converted audio in a mp3 file named
speech.save("output.mp3")

# Playing the converted file (optional)
os.system("start output.mp3")  # For Windows
# os.system("mpg321 output.mp3")  # For Linux
