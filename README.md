# KratorAI

**Empowering Africa's Graphic Designers in the AI Era**

KratorAI is an AI-powered platform that transforms static artwork into dynamic, monetizable digital assets through an advanced generative engine.

## Project Structure

This repository contains two parallel development tracks:

| Track | Purpose | Stack |
|-------|---------|-------|
| [`gemini-integration/`](./gemini-integration/) | Rapid prototyping with Gemini API | FastAPI, Gemini 2.5/3 Pro |
| [`custom-model/`](./custom-model/) | Production fine-tuned model with agentic tools | SDXL, ControlNet, LangGraph |
| [`shared/`](./shared/) | Common utilities (DB, storage, schemas) | PostgreSQL, GCS |

## Core AI Features

- **Design Breeding**: Combine "DNA" from multiple templates to generate novel, licensed assets
- **Refining & Variations**: Enhance templates via prompts while maintaining cultural integrity
- **Targeted Editing**: Inpainting, style transfer, and element manipulation
- **Cultural Localization**: Fine-tuned on African aesthetics (Adinkra, Kente, etc.)

## Quick Start

```bash
# Clone and setup
cd KratorAI

# For Gemini API prototyping
cd gemini-integration
pip install -r requirements.txt
cp .env.example .env  # Add your GEMINI_API_KEY
uvicorn src.api.main:app --reload

# For custom model development
cd ../custom-model
pip install -r requirements.txt
# See custom-model/README.md for setup
```

## Documentation

- [Product Description](./product_descript.md) - Full product requirements
- [Gemini Integration Guide](./gemini-integration/README.md)
- [Custom Model Development](./custom-model/README.md)

## License

Proprietary - KratorAI © 2025
