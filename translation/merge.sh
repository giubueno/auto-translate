#!/bin/bash
# Merge all mp3 files in the current directory into a single file
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp3