# KratorAI Custom Model

Production-grade fine-tuned model with agentic design workflow for African graphic designers.

## Architecture

This track uses:
- **SDXL** as base diffusion model
- **ControlNet** for structure preservation during breeding
- **IP-Adapter** for style transfer and blending
- **LangGraph** for agentic tool orchestration
- **SAM (Segment Anything)** for precise masking

## Features

| Feature | Implementation |
|---------|----------------|
| Design Breeding | ControlNet + IP-Adapter multi-style blending |
| Refining | SDXL img2img with cultural LoRA |
| Editing | SAM masks + SDXL inpainting |
| Agent | LangGraph workflow with tool routing |

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Download base models (requires HuggingFace auth)
python -m src.models.download_models

# Configure environment
cp .env.example .env

# Run the API
uvicorn src.api.main:app --reload --port 8001
```

## Project Structure

```
custom-model/
├── data/                    # Training data
│   ├── raw/                 # Original uploads
│   ├── processed/           # Annotated datasets
│   └── pipelines/           # Data processing
├── models/                  # Model artifacts
│   ├── base/                # Base model configs
│   ├── finetuned/           # Trained checkpoints
│   └── configs/             # Training configs
├── src/
│   ├── agent/               # LangGraph design agent
│   │   ├── design_agent.py  # Main orchestrator
│   │   └── tools/           # Agent tools
│   ├── models/              # Model wrappers
│   └── training/            # Fine-tuning scripts
└── tests/
```

## Training

```bash
# Prepare dataset
python -m data.pipelines.prepare_dataset

# Fine-tune cultural LoRA
python -m src.training.train_lora --config models/configs/cultural_lora.yaml

# Evaluate on holdout set
python -m src.training.evaluate --checkpoint models/finetuned/cultural_v1
```

## API Endpoints

Same interface as `gemini-integration/` for drop-in replacement:

| Endpoint | Description |
|----------|-------------|
| `POST /breed` | Multi-design breeding |
| `POST /refine` | Variation generation |
| `POST /edit` | Inpainting/style transfer |
| `POST /agent/chat` | Conversational design agent |
