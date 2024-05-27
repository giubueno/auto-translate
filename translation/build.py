from pydub import AudioSegment
import argparse

def add_mp3_at_time(main_mp3_path, insert_mp3_path, output_path, insert_time_ms):
    # Load the main MP3 file
    main_audio = AudioSegment.from_mp3(main_mp3_path)
    
    # Load the MP3 file to be inserted
    insert_audio = AudioSegment.from_mp3(insert_mp3_path)
    
    # Split the main audio at the insertion point
    first_part = main_audio[:insert_time_ms]
    second_part = main_audio[insert_time_ms:]
    
    # Concatenate the parts
    combined_audio = first_part + insert_audio + second_part
    
    # Export the combined audio to the output file
    combined_audio.export(output_path, format="mp3")
    print(f"MP3 files have been combined and saved to {output_path}")

# Example usage
output_path = "combined_audio.mp3"
insert_time_ms = 30000  # Insert at 30 seconds

# Parse the command line arguments
parser = argparse.ArgumentParser(description="Convert text to speech using OpenAI's API")
parser.add_argument("-f", "--file", help="Main MP3", required=True)
parser.add_argument("-i", "--insert", help="MP3 to be inserted", required=True)
parser.add_argument("-o", "--output", help="Output MP3", required=True)
parser.add_argument("-t", "--time", help="Time to insert", required=True)

parser = parser.parse_args()
add_mp3_at_time(parser.file, parser.insert, parser.output, int(parser.time))