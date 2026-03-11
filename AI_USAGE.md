# AI Tool Usage Documentation

## Overview

SceneScope was developed using AI-assisted coding tools alongside manual development. This document outlines how AI tools were used, what was built manually, and the decision-making process throughout.

## Tools Used

| Tool | Purpose | How It Was Used |
|------|---------|-----------------|
| **Claude Code (Anthropic)** | AI coding assistant | Architecture planning, boilerplate generation, debugging, code review |
| **Google Colab + T4 GPU** | Model training environment | Fine-tuning RoBERTa mood classifier on labeled screenplay data |
| **Groq API (Llama 3.1 8B)** | LLM inference | Scene analysis, director agent, mood classification fallback |
| **HuggingFace** | Model hosting & inference | Hosting fine-tuned mood classifier, generic emotion model fallback |
| **fal.ai (FLUX.1-schnell)** | Image generation | Primary storyboard sketch generation |
| **Google Gemini (Imagen 3)** | Image generation | Fallback image generation |

## What Was AI-Assisted vs. Manual

### AI-Assisted (Claude Code)
- Initial project scaffolding and boilerplate (FastAPI routes, Pydantic models, database schema)
- Director Agent system prompt design and conversational flow
- PDF export endpoint structure
- Visual consistency extraction prompt engineering
- Debugging static file serving, database persistence, and import issues
- 3-tier mood classifier fallback chain architecture

### Built Manually
- Frontend UI/UX design and React components (React Router 7, Tailwind CSS v4)
- Image generator service rewrite (switching from Together AI/OpenAI to fal.ai/Gemini)
- Configuration management and API key integration
- Screenplay parser refinements using `screenplay_tools` library
- Data collection and labeling pipeline (Film Corpus 2.0, 1500 scenes)
- Model training pipeline in Colab (hyperparameter tuning, data balancing decisions)
- End-to-end testing and integration debugging
- Shot suggester knowledge base (film theory mappings)

### Collaborative Decisions
- **2-class vs 4-class mood classifier**: Analyzed data distribution (715 tense, 89 somber, 14 uplifting, 9 action), decided on 2-class (tense/somber) for better accuracy with available data
- **Architecture**: Service-oriented design with independent, swappable services (parser, mood classifier, scene analyzer, image generator, etc.)
- **Fallback chains**: Designed multi-tier fallbacks for both mood classification and image generation to handle API failures gracefully
- **Visual consistency**: Decided on locked-scene propagation approach over global character sheets

## AI in the Product Itself

SceneScope uses AI at multiple levels in its core functionality:

### 1. Mood Classification (Fine-Tuned ML Model)
- **Model**: RoBERTa-base fine-tuned on 1500 labeled screenplay scenes
- **Dataset**: Scenes extracted from Film Corpus 2.0, labeled using Groq LLM with keyword-filtered validation
- **Training**: Google Colab T4 GPU, 3 epochs, batch size 8, learning rate 1e-5
- **Deployment**: Hosted on HuggingFace (`RedMinder56/scenescope-mood-classifier`)
- **Fallback**: Generic emotion model (j-hartmann) and Groq LLM as backup tiers

### 2. Scene Analysis (LLM)
- Groq (Llama 3.1 8B) analyzes each scene for vague elements, generates clarifying questions with directorial suggestions, and produces visual summaries
- Structured JSON output with validation and normalization

### 3. Image Generation (Diffusion Models)
- fal.ai FLUX.1-schnell for fast storyboard frame generation
- Prompts built from visual summaries + mood modifiers + user answers + visual consistency context
- Google Gemini Imagen 3 as fallback provider

### 4. Director Agent (Conversational AI)
- Groq-powered AI film director persona that interprets vague feedback
- Conversational flow: consult, follow-up questions, accept, then refine
- Provides cinematographic reasoning and educational context

### 5. Structure Analysis (LLM)
- Analyzes full screenplay for tonal shifts, pacing patterns, and emotional arcs
- Combines rule-based mood distance calculations with LLM narrative descriptions

## Prompt Engineering

Key prompts were iteratively refined:
- **Scene Analysis Prompt**: Evolved to return structured `{question, suggestion}` objects instead of plain strings
- **Visual Extraction Prompt**: Designed to extract only physical appearance details, marking inferences explicitly
- **Director System Prompt**: Crafted to balance authority with educational warmth, always asking follow-up questions
- **Mood Classification Prompt** (fallback): Constrained to return only valid JSON with mood and confidence

## Lessons Learned

1. **Data quality > quantity**: 1500 well-labeled scenes with balanced classes outperformed larger noisy datasets
2. **Fallback chains are essential**: No single AI service is 100% reliable; multi-tier fallbacks keep the app functional
3. **AI-assisted != AI-generated**: Using Claude Code for architecture discussions and boilerplate freed time for manual work on the parts that matter (UI, training pipeline, integration testing)
4. **Prompt engineering is iterative**: Initial prompts produced inconsistent JSON; adding format examples and strict constraints improved reliability significantly
