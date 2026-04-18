# SceneScope Architecture

## High-Level Flow
```
User (React) 
    → API (FastAPI) 
    → Prompt Builder 
    → Amazon Nova APIs 
    → Generated Sketch 
    → Back to User
```

## Components

### Frontend (React)
- Project setup form
- Character bank UI
- Scene editor with side-by-side sketch view
- Clarifying questions modal
- Export options

### Backend (FastAPI)
- REST API endpoints
- Database operations
- Prompt construction
- Nova API integration

### Prompt Builder Service
- Extracts mood from scene text
- Identifies vague elements
- Generates clarifying questions
- Assembles final image prompt with mood modifiers

### Amazon Nova Integration
- Nova 2 Lite: Scene analysis, mood extraction
- Nova Canvas: Sketch generation

### Database (SQLite/PostgreSQL)
- Projects, Characters, Scenes