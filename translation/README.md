# Translation

Code used to translate audios using Whisper to transcribe text, OpenAI to translate the text and convert the translated text into speech.

## Running

You can run this code using Python 3.

### Dependencies

If you don't have one already, create a virtual environment using:

```sh
python3 -m venv venv
```

Activate the Virtual Environment: Before installing dependencies, activate the virtual environment. On macOS and Linux, run:

```sh
python3 -m venv venv
source venv/bin/activate
```

On Windows, run:

```sh
.\venv\Scripts\activate
```

To install all dependencies listed in requirements.txt, use the following command:

```sh
pip install -r requirements.txt
```

***Attention***
We are using Open Whisper (Open source), which depends on NumPy < 2.x. You need to make sure that you have a 1.x version.

For example:

```sh
pip install numpy==1.26.4
```

### Testing

You can run the test by executing:

```sh
python -m unittest discover -s tests
```

## Audio translation

### Text to audio

```sh
python speak.py -f inputs/texts/de/0039.txt -l de -v alloy
```

```sh
python speak.py -f inputs/texts/de/0125.txt -l de -v fable
```

### Building an MP3 file

0125 = 85000

```sh
python build.py -f outputs/de/german.mp3 -i outputs/de/0125.mp3 -o outputs/de/german.mp3 -t 85000
```

### Translate

```sh
python translate.py -l de -f inputs/texts/en/0125.txt
```