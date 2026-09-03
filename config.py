import os
import sys
import json

CONFIG_JSON = os.getenv('CONFIG_JSON', 'config.json')


def load_bot_configs():
    """Load bot and model configurations from JSON file"""
    try:
        with open(CONFIG_JSON, 'r') as f:
            config = json.load(f)

        models_config = config.get('models', [])
        if not models_config:
            sys.exit("❌ No 'models' configuration found in JSON file.")

        models_dict = {model['name']: model for model in models_config}

        bot_configs = config.get('bots', [])
        if not bot_configs:
            sys.exit("❌ No 'bots' configuration found in JSON file.")

        for bot_config in bot_configs:
            model_name = bot_config.get('model')
            if model_name not in models_dict:
                sys.exit(f"❌ Bot '{bot_config.get('name')}' references unknown model '{model_name}'")

        for model in models_dict.values():
            if model.get('type') == 'openai' and not model.get('api_key'):
                env_key = f"{model.get('name', 'model').upper()}_API_KEY"
                model['api_key'] = os.getenv(env_key, '')

        return bot_configs, models_dict

    except FileNotFoundError:
        sys.exit(f"❌ Bot configuration file not found: {CONFIG_JSON}")
    except json.JSONDecodeError as e:
        sys.exit(f"❌ Invalid JSON in bot configuration file: {e}")
    except Exception as e:
        sys.exit(f"❌ Error loading bot configuration: {e}")
