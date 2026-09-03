# Multi-Bot Telegram System

A Python-based system for running multiple Telegram bots simultaneously, each with their own personality and AI model. Supports multiple AI providers including Ollama, OpenAI, Anthropic, and any OpenAI-compatible API.

## Features

- 🤖 **Multiple Bots**: Run multiple Telegram bots concurrently in separate processes
- 🎭 **Individual Personalities**: Each bot can have its own AI model and system prompt
- 🔄 **Process Isolation**: Each bot runs in its own process for stability and independence
- 💬 **Smart Chat Handling**: Supports both private chats and group chats (with @mentions)
- 🔧 **Easy Configuration**: JSON-based configuration with models and bots separation
- 🌐 **Multiple AI Providers**: Ollama, OpenAI, Anthropic, and OpenAI-compatible APIs
- 🔒 **SSL Flexibility**: Support for self-signed certificates in corporate environments
- 📝 **Markdown Support**: Beautiful formatting for code blocks and rich text responses
- 🏗️ **Modular Architecture**: Clean separation of concerns with dedicated modules

## Supported AI Providers

### Local AI (Ollama)
- 🦙 **Ollama**: Local models (llama3, gemma3, codellama, etc.)
- No API key required
- Full privacy and control

### Cloud AI Services
- 🤖 **OpenAI**: GPT models (gpt-4o, gpt-4o-mini, etc.)
- 🧠 **Anthropic**: Claude models (claude-3-haiku, claude-3-sonnet, etc.)
- 🌐 **Any OpenAI-compatible API**: Custom endpoints and providers

## Requirements

- Python 3.8+
- Telegram Bot API tokens (one for each bot)
- At least one AI provider:
  - [Ollama](https://ollama.ai/) for local models, OR
  - API keys for cloud providers (OpenAI, Anthropic, etc.)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd multi-bot-telegram-system
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install python-telegram-bot requests
   ```

4. **Set up AI Provider(s)**

   **Option A: Ollama (Local)**
   ```bash
   # Install Ollama from https://ollama.ai/
   ollama pull llama3
   ollama pull gemma3:4b
   ```

   **Option B: Cloud Providers**
   - Get API keys from your preferred provider(s)
   - Configure in `config.json` or environment variables

## Configuration

### Models Configuration

The `config.json` file now separates models from bots for better reusability:

```json
{
  "models": [
    {
      "name": "local_llama",
      "type": "ollama",
      "model_id": "llama3",
      "base_url": "http://localhost:11434"
    },
    {
      "name": "openai_gpt4",
      "type": "openai",
      "model_id": "gpt-4o-mini",
      "base_url": "https://api.openai.com/v1",
      "api_key": "your-openai-api-key",
      "ssl_verify": true
    },
    {
      "name": "anthropic_claude",
      "type": "openai",
      "model_id": "claude-3-haiku-20240307",
      "base_url": "https://api.anthropic.com/v1",
      "api_key": "your-anthropic-api-key",
      "ssl_verify": true
    },
    {
      "name": "corporate_model",
      "type": "openai",
      "model_id": "custom-model",
      "base_url": "https://internal-api.company.com/v1",
      "api_key": "your-internal-key",
      "ssl_verify": false
    }
  ],
  "bots": [
    {
      "name": "assistant_bot",
      "token": "YOUR_BOT_TOKEN_HERE",
      "model": "local_llama",
      "system_prompt": "You are a helpful assistant."
    },
    {
      "name": "coding_bot",
      "token": "YOUR_SECOND_BOT_TOKEN",
      "model": "openai_gpt4",
      "system_prompt": "You are a coding expert who helps with programming tasks."
    }
  ]
}
```

### Model Configuration Options

| Field | Description | Required | Default |
|-------|-------------|----------|---------|
| `name` | Unique model identifier | ✅ | - |
| `type` | Provider type (`ollama` or `openai`) | ✅ | - |
| `model_id` | Actual model name/ID | ✅ | - |
| `base_url` | API endpoint URL | ✅ | - |
| `api_key` | API authentication key | For `openai` type | - |
| `ssl_verify` | Verify SSL certificates | ❌ | `true` |

### Bot Configuration Options

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Friendly bot name (for logs) | ✅ |
| `token` | Telegram Bot API token | ✅ |
| `model` | Reference to model name | ✅ |
| `system_prompt` | Bot personality/instructions | ✅ |

### Environment Variables

The following environment variables are **optional** and have default values:

```env
# Configuration file path (default: config.json)
CONFIG_JSON=config.json

# Ollama API URL (default: http://localhost:11434)
OLLAMA_API_URL=http://localhost:11434
```

API keys can also be set via environment variables for security (model name in uppercase + `_API_KEY`):

```env
# Example API key environment variables
OPENAI_GPT4_API_KEY=sk-your-openai-key
ANTHROPIC_CLAUDE_API_KEY=your-anthropic-key
CORPORATE_MODEL_API_KEY=your-internal-key
```

## Usage

### Running the Bots

```bash
python bot.py
```

Output example:
```
✅ Starting 2 bot(s) in separate processes...
✅ assistant_bot is running...
✅ coding_bot is running...
```

### Stopping the Bots

Press `Ctrl+C` to gracefully shut down:
```
🛑 Shutting down all bots...
```

### Chat Interaction

**Private Chats**: Send any message directly

**Group Chats**: Mention the bot `@botusername message`

### Formatted Responses

The bots now support rich formatting including:

- **Code blocks** with syntax highlighting:
  ```python
  def hello():
      print("Hello, World!")
  ```

- **Inline code**: `variable`
- **Bold text**: **important**
- **Italic text**: *emphasis*
- Lists and other markdown formatting

## Project Structure

```
multi-bot-telegram-system/
├── bot.py              # Main bot application and Telegram handling
├── api_clients.py      # AI provider API clients
├── config.py          # Configuration loading and validation
├── config.json        # Models and bots configuration
├── prompts.txt        # Example system prompts
├── README.md          # This documentation
├── .venv/             # Virtual environment (gitignored)
├── .vscode/           # VS Code configuration
├── .git/              # Git repository
└── __pycache__/       # Python cache (gitignored)
```

## Adding New Models

1. **Add model configuration** to `config.json`:
   ```json
   {
     "name": "new_model",
     "type": "openai",
     "model_id": "gpt-4o",
     "base_url": "https://api.openai.com/v1",
     "api_key": "your-key-here",
     "ssl_verify": true
   }
   ```

2. **Reference in bot configuration**:
   ```json
   {
     "name": "new_bot",
     "token": "BOT_TOKEN",
     "model": "new_model",
     "system_prompt": "Your personality here."
   }
   ```

## Adding New Bots

1. **Create Telegram bot** via [@BotFather](https://t.me/botfather)
2. **Add bot configuration** to `config.json`
3. **Restart the application**

## SSL Certificate Handling

For corporate/internal APIs with self-signed certificates:

```json
{
  "name": "internal_model",
  "type": "openai",
  "model_id": "internal-llm",
  "base_url": "https://internal-ai.company.com/v1",
  "api_key": "internal-key",
  "ssl_verify": false
}
```

⚠️ **Security Note**: Only disable SSL verification for trusted internal networks.

## Development

### VS Code/Cursor Setup

- Press `F5` to run with debugger
- Breakpoints and debugging work seamlessly

### Code Structure

- **`bot.py`**: Telegram bot logic and message handling
- **`api_clients.py`**: AI provider communication
- **`config.py`**: Configuration management and validation

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| "No 'models' configuration found" | Add `models` section to `config.json` |
| "Bot references unknown model" | Ensure model `name` matches in both sections |
| "No API key provided" | Set `api_key` in config or environment variable |
| "SSL certificate verify failed" | Set `ssl_verify: false` for self-signed certificates |
| "Error calling Ollama" | Verify Ollama is running: `ollama serve` |

### Logs

Each bot has its own log prefix:
```
2024-01-01 12:00:00 - assistant_bot - INFO - ✅ Starting bot
2024-01-01 12:00:01 - coding_bot - INFO - Message processed
```

## Security Best Practices

- 🔐 **Never commit API keys** to version control
- 🔒 **Use environment variables** for sensitive data
- 🛡️ **Enable SSL verification** for public APIs
- 📁 **Keep `config.json` gitignored** if it contains secrets

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
