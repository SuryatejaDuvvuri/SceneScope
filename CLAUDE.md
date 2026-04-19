# SceneScope — AI Screenplay Pre-Visualization

## Project Overview
SceneScope is an AI-powered pre-visualization tool that converts raw screenplay text into illustrated storyboards. Built as a CS205 final project at UC Riverside, it replaces the need for a storyboard artist in early pre-production by automating scene parsing, mood classification, visual ambiguity detection, and image generation in a single pipeline.

## Architecture

**Frontend:** React + React Router, deployed on Cloudflare Pages
**Backend:** Python FastAPI, served via cloudflared tunnel
**AI Services:** Groq (LLM), HuggingFace (mood classifier), Stability AI + Replicate (image generation)
**Auth:** Google OAuth2 with JWT tokens

### Pipeline (per scene)
1. User pastes screenplay text
2. Backend parses text into individual scenes
3. Each scene gets mood classified (3-tier fallback: fine-tuned RoBERTa → generic emotion model → LLM)
4. Visual ambiguity detector identifies vague descriptions
5. Clarifying questions generated with suggested answers
6. User answers refine the scene context
7. Image generation produces storyboard illustration
8. AI Director agent provides film-theory-grounded creative feedback

## Key Technical Decisions

### Fine-tuned RoBERTa Mood Classifier
- Generic emotion models only hit ~55% accuracy on screenplay dialogue — creative writing doesn't map cleanly to standard emotion labels
- Trained custom classifier on 1,500 scenes from Film Corpus 2.0 using Google Colab T4 GPU
- Deployed on HuggingFace Inference API (model: RedMinder56/scenescope-mood-classifier)
- 3-tier fallback ensures classification stays available when any single provider goes down

### Visual Consistency System
- When a user "locks" a scene, the system extracts character appearances, locations, and props
- These details are propagated into image generation prompts for subsequent scenes
- Solves the problem of AI image generators producing inconsistent characters across scenes

### Image Generation Style
- Early versions produced photorealistic images — wrong for storyboarding
- Solution: bookend style anchoring — short style directive at start of prompt, scene content in middle, style reinforcement at end
- Target: hand-drawn colored storyboard illustration style (like a painted sketch)
- Prompt structure prevents scene content from drowning out style instructions

### AI Director Agent
- Conversational agent grounded in film theory
- Interprets vague creative feedback ("make it moodier") into actionable visual direction
- Generates follow-up questions to refine the user's creative intent

## Problems Solved During Development

### Deployment (Cloudflare Pages + cloudflared)
- **404 on /api/auth/google:** Frontend was hitting itself instead of backend. Fix: `VITE_API_BASE_URL` must be baked at build time — rebuild with `VITE_API_BASE_URL=https://tunnel-url npm run build`, deploy `build/client/` (not `dist/`)
- **CORS 400 Bad Request:** Backend `CORS_ORIGINS` didn't include the Cloudflare Pages URL. Fix: add `https://scenescope.pages.dev` to env
- **Double slash in OAuth redirect (`//auth/callback`):** `FRONTEND_URL` had trailing slash. Fix: remove trailing slash
- **OAuth redirecting to localhost:** Backend `FRONTEND_URL` still set to `localhost:5173`. Fix: update to production URL
- **cloudflared tunnel drops:** QUIC connection errors on WiFi. Diagnosis: temporary drops, cloudflared auto-reconnects. Recommendation: wired ethernet for demos

### Image Generation Quality
- **Wrong content:** Bar scene produced office/study images. Root cause: scene content was being drowned by style prefix in the prompt. Fix: restructured prompt to put scene content front and center
- **Photorealistic output:** Generated actual photographs instead of storyboard sketches. Fix: bookend style anchoring — style at start AND end of prompt, scene in middle

### GitHub Branch Issue
- Repository had both `master` and `main` branches with unrelated commit histories (different root commits)
- Diagnosis: two separate initial commits. Fix: delete `master` on remote with `git push origin --delete master`

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Deploy frontend to Cloudflare Pages
cd frontend
VITE_API_BASE_URL=https://YOUR-TUNNEL-URL npm run build
npx wrangler pages deploy build/client --project-name=scenescope

# Expose backend via cloudflared
cloudflared tunnel --url http://localhost:8000

# Train mood classifier (Google Colab with T4 GPU)
# See training notebook in project docs
```

## Environment Variables

### Backend (.env)
```
GROQ_API_KEY=
HUGGINGFACE_API_KEY=
STABILITY_API_KEY=
REPLICATE_API_TOKEN=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FRONTEND_URL=https://scenescope.pages.dev  # NO trailing slash
BACKEND_PUBLIC_URL=https://your-tunnel.trycloudflare.com
CORS_ORIGINS=http://localhost:5173,https://scenescope.pages.dev
JWT_SECRET_KEY=
```

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000  # or tunnel URL for production build
VITE_GOOGLE_CLIENT_ID=
```

## File Structure Notes
- Frontend build outputs to `build/client/` (not `dist/`) — React Router with Vite
- Backend entry point: `app.main` (FastAPI)
- Mood classifier model hosted on HuggingFace, not bundled locally

## AI Usage Documentation
- Full AI tool usage documented in `AI_USAGE.md` (required for CS205 rubric, worth 10% of grade)
- Covers what was AI-assisted vs manual, ML pipeline details, prompt engineering lessons learned
