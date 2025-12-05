# Hugging Face Space Setup Instructions

## ⚠️ IMPORTANT: API Key Configuration

Your Gemini API key was compromised and disabled. Follow these steps:

### 1. Get a New API Key
1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the new key (starts with `AIza...`)

### 2. Configure Hugging Face Space
1. Go to https://huggingface.co/spaces/SajivJess/ConstructureAI/settings
2. Scroll to **Repository Secrets**
3. Click **New Secret**
4. Name: `GEMINI_API_KEY`
5. Value: Paste your new API key
6. Click **Add Secret**

### 3. Restart the Space
1. Go to https://huggingface.co/spaces/SajivJess/ConstructureAI
2. Click the ⋮ menu (three dots)
3. Click **Factory Reboot**

### 4. Delete Old Key
1. Go back to https://aistudio.google.com/apikey
2. Find the old compromised key
3. Click **Delete** to prevent misuse

## 🔒 Security Best Practices

- ✅ **DO** use environment variables for API keys
- ✅ **DO** add `.env` to `.gitignore`
- ✅ **DO** use HF Space Secrets for production
- ❌ **DON'T** hardcode API keys in source code
- ❌ **DON'T** commit API keys to git repos
- ❌ **DON'T** share API keys in screenshots/logs

## Testing Locally

Create a `.env` file in the backend directory:

```bash
GEMINI_API_KEY=your_new_api_key_here
```

This file is already in `.gitignore` and won't be committed.
