# Translation

Code used to translate audios using Whisper to transcribe the text, AWS Translate and Open AI to transform the translated text into speech.

## Running

You can run this code using Python 3.

### Dependencies

If you don't have one already, create a virtual environment using:

```sh
python3 -m venv venv
```

Activate the Virtual Environment: Before installing dependencies, activate the virtual environment. On macOS and Linux, run:

```sh
python3 -m venv myenv
source myenv/bin/activate
```

On Windows, run:

```sh
.\myenv\Scripts\activate
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