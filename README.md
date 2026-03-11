# SceneScope: A writing tool that shows you what your words actually say

**AI-powered screenplay pre-visualization tool that transforms written scenes into visual storyboards.**

Writers and directors paste screenplay text and instantly see how their words translate to the screen, with mood-conditioned sketches, clarifying questions, and iterative refinement guided by an AI director.

## Problem

Screenplay text is inherently ambiguous. "A dark room" could mean a hundred different things visually. Directors, cinematographers, and writers spend hours in pre-production trying to align on visual interpretation. This costs time, money, and creative energy, especially for independent filmmakers and students who cannot afford dedicated storyboard artists.

## Solution

SceneScope creates a **write -> see -> refine -> repeat** feedback loop:

1. Paste a screenplay scene (Fountain format)
2. AI classifies the mood, identifies vague elements, and generates a visual storyboard frame
3. Answer clarifying questions (with AI-suggested defaults) to refine the visualization
4. Consult the AI Director for cinematographic guidance
5. Lock finalized scenes to maintain visual consistency across the screenplay
6. Export a PDF storyboard

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 19, React Router 7, Vite 7, Tailwind CSS v4 | SPA with SSR capability |
| Backend | FastAPI, Python 3.11+ | Async API server |
| Database | SQLite + aiosqlite | Async persistence with iteration tracking |
| ML - Mood | RoBERTa (fine-tuned), HuggingFace Inference API | Scene mood classification |
| ML - Analysis | Groq API (Llama 3.1 8B Instant) | Scene analysis, director agent, structure analysis |
| ML - Images | fal.ai (FLUX.1-schnell), Google Gemini (Imagen 3) | Storyboard frame generation |
| Parsing | screenplay-tools (Fountain parser) | Screenplay format parsing |
| Export | fpdf2 | PDF storyboard generation |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- API keys for: Groq, fal.ai, HuggingFace (optional: Gemini)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Fill in your API keys

# Initialize database
python -c "import asyncio; from app.db import init_db; asyncio.run(init_db())"

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Contributors

- Suryateja Duvvuri ([@SuryatejaDuvvuri](https://github.com/SuryatejaDuvvuri))
