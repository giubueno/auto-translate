import translators
import argparse

parser = argparse.ArgumentParser(description="Translates an MP3 file to a different language")
parser.add_argument("-f", "--file", help="MP3 file path", required=True)
parser.add_argument("-l", "--language", help="Target language", required=True)
parser.add_argument("-d", "--destination", help="Destination folder", required=False, default="outputs")
args = parser.parse_args()

translator = translators.AudioTranslator(args.file, args.language, args.destination)
translator.run()