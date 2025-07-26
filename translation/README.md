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

### Required Credentials and Environment Variables

This project uses several external services that require API keys and credentials. Create a `.env` file in the root directory with the following variables:

```sh
# OpenAI API Key (required for text-to-speech and translation)
OPENAI_API_KEY=your_openai_api_key_here

# AWS Credentials (required for AWS Translate and Transcribe services)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# Google Cloud Credentials (optional, for Google Cloud services)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json

# Google Gemini API Key (optional, for video translation features)
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
```

#### How to obtain credentials:

1. **OpenAI API Key:**
   - Sign up at [OpenAI Platform](https://platform.openai.com/)
   - Navigate to API Keys section
   - Create a new API key
   - Add billing information (required for API usage)

2. **AWS Credentials:**
   - Create an AWS account at [AWS Console](https://aws.amazon.com/)
   - Create an IAM user with permissions for:
     - Amazon Translate
     - Amazon Transcribe
     - Amazon S3 (if using transcription features)
   - Generate Access Key ID and Secret Access Key
   - Ensure the user has appropriate permissions for the services

3. **Google Cloud Credentials (optional):**
   - Set up a Google Cloud project
   - Enable the required APIs (Text-to-Speech, Translate)
   - Create a service account and download the JSON credentials file

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

## Running voice.sh

The `voice.sh` script is a comprehensive automation tool that processes DOCX files and generates translated audio files for multiple languages.

### Prerequisites

Before running `voice.sh`, ensure you have:

1. **All required credentials** (see section above)
2. **A DOCX file** in the `inputs/` directory with the correct naming format
3. **Virtual environment activated**

### Usage

```sh
# Make the script executable (first time only)
chmod +x voice.sh

# Run the script
./voice.sh
```

### What voice.sh does

The script performs the following operations:

1. **Activates the virtual environment**
2. **Installs/updates dependencies** from `requirements.txt`
3. **Sets environment variables:**
   - `DATE_FILE`: The date identifier for the DOCX file (default: "20250727")
   - `DOC_LANGUAGE`: Source language of the document (default: "de")
4. **Processes multiple languages:** Portuguese (pt-br), German (de), and Spanish (es)
5. **For each language:**
   - Runs `tts_from_docx.py` to translate and convert text to speech
   - Renames output files with date suffix
6. **Prepares files for Google Drive upload** (commented out in the script)

### Customizing voice.sh

You can modify the script to:

- **Change the date file:** Edit the `DATE_FILE` variable
- **Change source language:** Edit the `DOC_LANGUAGE` variable  
- **Add/remove target languages:** Modify the `LANGUAGES` array
- **Change input file path:** Update the path in the `tts_from_docx.py` call

### Example customization:

```bash
# Change the date and source language
export DATE_FILE="20250115"
export DOC_LANGUAGE=en

# Add more languages
LANGUAGES=("pt-br" "de" "es" "fr" "it")
```

### Input file format

The DOCX file should contain:
- **Timestamps** in format `(MM:SS):` at the beginning of paragraphs
- **Text content** to be translated and converted to speech
- **Proper paragraph structure** for processing

Example:
```
(00:01): Welcome to our presentation.
(00:05): Today we will discuss important topics.
```

### Output structure

The script generates:
```
outputs/
├── pt-br/
│   ├── pt-br_20250727.mp3
│   └── files.txt
├── de/
│   ├── de_20250727.mp3
│   └── files.txt
└── es/
    ├── es_20250727.mp3
    └── files.txt
```

### Troubleshooting

1. **Permission denied:** Run `chmod +x voice.sh`
2. **Missing credentials:** Ensure all environment variables are set
3. **File not found:** Check that the DOCX file exists in `inputs/` directory
4. **API rate limits:** The script includes delays to avoid rate limiting
5. **Virtual environment issues:** Ensure `venv/bin/activate` exists and is accessible