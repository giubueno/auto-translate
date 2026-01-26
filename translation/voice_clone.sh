#!/bin/bash
#
# Voice Clone Translation Script (using Chatterbox locally)
#
# Usage: ./voice_clone.sh <video_path> [options]
#
# Example: ./voice_clone.sh /path/to/video.mp4 -l de -s en --sequential -g 1000
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
VIDEO_PATH=""
TARGET_LANG="de"
SOURCE_LANG="en"
DEVICE=""
SEQUENTIAL=""
GAP="1000"
WORKERS="4"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--language)
            TARGET_LANG="$2"
            shift 2
            ;;
        -s|--source)
            SOURCE_LANG="$2"
            shift 2
            ;;
        -d|--device)
            DEVICE="$2"
            shift 2
            ;;
        --sequential)
            SEQUENTIAL="--sequential"
            shift
            ;;
        -g|--gap)
            GAP="$2"
            shift 2
            ;;
        -w|--workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 <video_path> [options]"
            echo ""
            echo "Arguments:"
            echo "  video_path              Path to the source video file (required, first positional arg)"
            echo ""
            echo "Options:"
            echo "  -l, --language LANG     Target language code (default: de for German)"
            echo "  -s, --source LANG       Source language code (default: en for English)"
            echo "  -d, --device DEVICE     Device for Chatterbox: cuda, mps, cpu (default: auto-detect)"
            echo "  --sequential            Concatenate audio with gaps instead of time-synced overlay"
            echo "  -g, --gap MS            Gap in milliseconds between chunks in sequential mode (default: 1000)"
            echo "  -w, --workers N         Number of parallel workers for translation (default: 4)"
            echo "  -h, --help              Show this help message"
            echo ""
            echo "Supported languages: ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt, ru, sv, sw, tr, zh"
            echo ""
            echo "Examples:"
            echo "  $0 /path/to/video.mp4 -l de -s en"
            echo "  $0 /path/to/video.mp4 -l fr --sequential -g 1000"
            echo "  $0 /path/to/video.mp4 -l es -d cuda -w 8"
            exit 0
            ;;
        *)
            # First positional argument is video path
            if [ -z "$VIDEO_PATH" ]; then
                VIDEO_PATH="$1"
            fi
            shift
            ;;
    esac
done

if [ -z "$VIDEO_PATH" ]; then
    echo "Error: Video path is required"
    echo "Usage: $0 <video_path> [options]"
    echo "Use -h or --help for more information"
    exit 1
fi

if [ ! -f "$VIDEO_PATH" ]; then
    echo "Error: Video file not found: $VIDEO_PATH"
    exit 1
fi

echo "Starting voice clone translation pipeline (Chatterbox)..."
echo "Video: $VIDEO_PATH"
echo "Translating from $SOURCE_LANG to $TARGET_LANG"
if [ -n "$SEQUENTIAL" ]; then
    echo "Mode: Sequential (with ${GAP}ms gaps)"
else
    echo "Mode: Time-synchronized"
fi
echo "Parallel workers: $WORKERS"
echo ""

# Build command
CMD="python3 voice_clone_pipeline.py -v \"$VIDEO_PATH\" -l \"$TARGET_LANG\" -s \"$SOURCE_LANG\" -o outputs -w $WORKERS -g $GAP"

if [ -n "$DEVICE" ]; then
    CMD="$CMD -d $DEVICE"
fi

if [ -n "$SEQUENTIAL" ]; then
    CMD="$CMD --sequential"
fi

eval $CMD
