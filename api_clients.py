import requests
import os

OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')


def call_ollama(prompt: str, model_config: dict, system_prompt: str, logger) -> str:
    """Call Ollama API using model configuration"""
    base_url = model_config.get('base_url', OLLAMA_API_URL)
    model_id = model_config['model_id']

    payload = {
        "model": model_id,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False
    }
    try:
        verify_ssl = model_config.get('ssl_verify', True)
        response = requests.post(f"{base_url}/api/generate", json=payload, verify=verify_ssl)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "No response received from Ollama.")
    except Exception as e:
        logger.error(f"Error calling Ollama: {e}")
        return f"Error calling Ollama: {e}"


def call_openai_compatible(prompt: str, model_config: dict, system_prompt: str, logger) -> str:
    """Call OpenAI compatible API using model configuration"""
    base_url = model_config['base_url']
    model_id = model_config['model_id']
    api_key = model_config.get('api_key', '')

    if not api_key:
        logger.error("No API key provided for OpenAI compatible API")
        return "Error: No API key configured for OpenAI compatible API"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        verify_ssl = model_config.get('ssl_verify', True)
        response = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, verify=verify_ssl)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error calling OpenAI compatible API: {e}")
        return f"Error calling OpenAI compatible API: {e}"


def call_ai_model(prompt: str, bot_config: dict, models_dict: dict, logger) -> str:
    """Call the appropriate AI API based on model configuration"""
    model_name = bot_config['model']
    model_config = models_dict[model_name]
    system_prompt = bot_config.get('system_prompt', 'You are a helpful assistant.')

    api_type = model_config['type'].lower()

    if api_type == 'ollama':
        return call_ollama(prompt, model_config, system_prompt, logger)
    elif api_type == 'openai':
        return call_openai_compatible(prompt, model_config, system_prompt, logger)
    else:
        logger.error(f"Unsupported API type: {api_type}")
        return f"Error: Unsupported API type: {api_type}"