import boto3
import random
import argparse
from botocore.exceptions import NoCredentialsError
import urllib.request
import json

def upload_file_to_s3(file_name, bucket_name):
    """
    Upload a file to an S3 bucket
    :param file_name: File to upload
    :param bucket_name: Bucket to upload to
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_name, bucket_name, file_name)
        print(f"File {file_name} uploaded to S3 bucket {bucket_name}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")

def transcribe_file(file_name, bucket_name, job_name, language_code="en-US"):
    """
    Transcribe an audio file using AWS Transcribe
    :param file_name: Name of the file in the S3 bucket
    :param bucket_name: Name of the S3 bucket
    :param job_name: Name of the transcription job
    :param language_code: Language code of the transcript
    """
    transcribe_client = boto3.client('transcribe')
    file_uri = f"s3://{bucket_name}/{file_name}"
    
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': file_uri},
        MediaFormat='mp3',
        LanguageCode=language_code
    )

    print(f"Started transcription job {job_name}")

def check_transcription_status(job_name):
    """
    Check the status of a transcription job
    :param job_name: Name of the transcription job
    """
    transcribe_client = boto3.client('transcribe')
    result = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
    return result['TranscriptionJob']['TranscriptionJobStatus']

def download_transcription_result(job_name):
    """
    Download the transcription result for a specified job.
    :param job_name: Name of the transcription job
    """
    # Create a client for the Transcribe service
    transcribe_client = boto3.client('transcribe')
    
    try:
        # Get transcription job information
        response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        
        if status == 'COMPLETED':
            # Get the URL of the transcription file
            transcription_file_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
            # Download the transcription result
            with urllib.request.urlopen(transcription_file_uri) as response:
                # Read the transcription result
                data = json.load(response)
                
                # Save to a local file (optional)
                with open('transcription_result.json', 'w') as outfile:
                    json.dump(data, outfile)
                
                print("Transcription downloaded and saved as 'transcription_result.json'")
                return data
        else:
            print(f"Transcription job is not complete yet. Current status: {status}")
    except Exception as e:
        print(f"Error retrieving transcription job: {e}")

def main(file_name):
    bucket_name = "saddleback-translations"
    job_name = f"saddleback-transcription-job-{random.randint(1, 1000)}"
    
    # Upload the file to S3
    upload_file_to_s3(file_name, bucket_name)
    
    # Start the transcription job
    transcribe_file(file_name, bucket_name, job_name)
    
    # Optionally, wait for the job to complete and check the status
    import time
    while True:
        status = check_transcription_status(job_name)
        print(f"Job Status: {status}")
        if status in ['COMPLETED', 'FAILED']:
            break
        time.sleep(30)

    download_transcription_result(job_name)

parser = argparse.ArgumentParser(description="Transcribe the audio file to text")
parser.add_argument("-f", "--file", help="Original text file path", required=True)
args = parser.parse_args()

main(args.file)
