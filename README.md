# KratorAI Gemini Integration

Rapid prototyping track using Google Gemini API for design breeding, refining, and editing. Now featuring a conversational AI agent for interactive image editing.

## Features

- **AI Agent**: Conversational assistant for image editing and generation
- **Design Breeding**: Multi-image prompts for style fusion
- **Refining**: Image-to-image enhancement with cultural prompts
- **Editing**: Inpainting via Gemini's image capabilities
- **Lineage Tracking**: NetworkX-based royalty graph

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your GEMINI_API_KEY to .env

# Run the API
uvicorn src.api.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent/chat` | POST | Chat with KratorAI agent |
| `/agent/session` | POST | Create new agent session |
| `/breed` | POST | Combine multiple designs into hybrid |
| `/refine` | POST | Generate variations with prompts |
| `/edit` | POST | Targeted inpainting/style transfer |
| `/health` | GET | Health check |

## Tech Stack

- **API**: FastAPI
- **AI**: Google Gemini 2.5 Flash / 2.0 Flash
- **Agent**: Function calling, memory management, structured logging
- **Lineage**: NetworkX for royalty graphs
- **Storage**: Google Cloud Storage

