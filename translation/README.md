# Translation

Code used to translate audios using Whisper to transcribe the text, AWS Translate and Open AI to transform the translated text into speech.

## Running

You can run this code using Python 3.

### Dependencies

Activate the Virtual Environment: Before installing dependencies, activate the virtual environment. On macOS and Linux, run:

```sh
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

### Testing

You can run the test by executing:

```sh
python -m unittest discover -s tests
```