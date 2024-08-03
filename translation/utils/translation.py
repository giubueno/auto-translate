import boto3

def translate_text(text, source_language='en', target_language='es'):
    translate = boto3.client(service_name='translate', region_name='us-east-1', use_ssl=True)
    result = translate.translate_text(Text=text, SourceLanguageCode=source_language, TargetLanguageCode=target_language)
    return result.get('TranslatedText')