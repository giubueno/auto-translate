from openai import OpenAI

def translate_text(text, source_language='en', target_language='es'):
    if text == "":
        return ""
    
    client = OpenAI()
    
    # Prepare the prompt for translation
    prompt = f"Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else: {text}"
    
    # Make request to OpenAI API
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a professional translator. Translate the given text accurately while preserving the original meaning and tone."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3  # Lower temperature for more consistent translations
    )
    
    return response.choices[0].message.content.strip()
