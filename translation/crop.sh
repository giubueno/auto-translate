#!/bin/bash

rm outputs/de/de_20250622-2_cropped.mp3
rm outputs/es/es_20250622-2_cropped.mp3
rm outputs/pt-br/pt-br_20250622-2_cropped.mp3

# crop the first 27:24 of outputs/de/de_20250622-2.mp3 and save it as outputs/de/de_20250622-2_cropped.mp3
ffmpeg -i outputs/de/de_20250622-2.mp3 -ss 00:27:24 -c copy outputs/de/de_20250622-2_cropped.mp3

# crop the first 27:24 of outputs/es/es_20250622-2.mp3 and save it as outputs/es/es_20250622-2_cropped.mp3
ffmpeg -i outputs/es/es_20250622-2.mp3 -ss 00:27:24 -c copy outputs/es/es_20250622-2_cropped.mp3

# crop the first 27:24 of outputs/pt-br/pt-br_20250622-2.mp3 and save it as outputs/pt-br/pt-br_20250622-2_cropped.mp3
ffmpeg -i outputs/pt-br/pt-br_20250622-2.mp3 -ss 00:27:24 -c copy outputs/pt-br/pt-br_20250622-2_cropped.mp3
