import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

print('\n' + '='*60)
print('AVAILABLE GEMINI MODELS')
print('='*60)

models = genai.list_models()
for m in models:
    if 'generateContent' in m.supported_generation_methods:
        print(f'\n📌 Model: {m.name}')
        print(f'   Display Name: {m.display_name}')
        print(f'   Description: {m.description[:100]}...')
        print(f'   Methods: {", ".join(m.supported_generation_methods)}')

print('\n' + '='*60)
print('RECOMMENDATION FOR HIRING ASSISTANT:')
print('='*60)
print('''
Best Model: gemini-1.5-flash
Reasons:
- Fast response times (critical for chat UX)
- Cost-effective for high-volume screening
- Strong instruction following for prompts
- Good balance of speed and quality
- 1M token context window (handles long conversations)

Alternative: gemini-1.5-pro
- Better for complex reasoning
- Higher quality outputs
- But slower and more expensive
''')
