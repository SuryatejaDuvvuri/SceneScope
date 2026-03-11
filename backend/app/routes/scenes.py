"""
Scenes API Routes
─────────────────
Handles the refinement loop, locking, and structure analysis.

The initial scene creation pipeline is in routes/projects.py (POST /projects/{id}/scenes).
This file handles everything AFTER initial creation.
"""

import uuid
from fastapi import APIRouter, HTTPException
from app.db import get_db, to_json, from_json
from app.models.scene import (
    RefineRequest, SceneResponse, SceneIterationResponse, DirectorNotes,
    ConsultRequest, ConsultFollowUpRequest, ConsultResponse,
)
from app.models.common import StructureAnalysis
from app.services.promptBuilder import buildPrompt
from app.services.imageGenerator import generateImage
from app.services.shotSuggester import suggest_shots
from app.services.visualConsistency import extractVisualDetails, getProjectContext, buildConsistencyPrompt
from app.services.structureAnalyzer import analyze_structure
from app.services.directorAgent import consult_director, continue_consultation
from app.services.sceneAnalyzer import generateRefinementQuestions

router = APIRouter(tags=["scenes"])

MAX_REFINEMENTS = 3


# ── Refinement Loop ──

@router.post("/scenes/{scene_id}/refine", response_model=SceneResponse)
async def refine_scene(scene_id: str, body: RefineRequest):
    """Refine a scene: rebuild prompt with user answers + visual context, regenerate sketch."""
    db = await get_db()
    try:
        # Fetch scene
        row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is locked and cannot be refined")

        # Check iteration limit
        count_row = await db.execute(
            "SELECT COUNT(*) as c FROM scene_iterations WHERE scene_id = ?", (scene_id,)
        )
        count = await count_row.fetchone()
        next_iteration = count["c"] + 1

        if next_iteration > MAX_REFINEMENTS:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_REFINEMENTS} refinements reached. Lock the scene to finalize.")

        # Get visual context from locked scenes for cross-scene consistency
        context = await getProjectContext(scene["project_id"])
        consistencySuffix = buildConsistencyPrompt(context)

        # Get previous iteration's prompt for within-scene consistency
        prev_prompt = ""
        if scene["current_iteration_id"]:
            prev_row = await db.execute(
                "SELECT prompt_used FROM scene_iterations WHERE id = ?",
                (scene["current_iteration_id"],)
            )
            prev_iter = await prev_row.fetchone()
            if prev_iter:
                prev_prompt = prev_iter["prompt_used"]

        # Use pre-confirmed director notes from /consult flow, or consult on the fly
        director_notes = None
        if body.director_notes:
            director_notes = body.director_notes
        elif body.feedback:
            director_notes = consult_director(
                heading=scene["heading"] or "",
                description=scene["description"],
                mood=scene["mood"] or "neutral",
                visual_summary=scene["visual_summary"] or "",
                feedback=body.feedback,
                answers=body.answers,
                consistency_context=consistencySuffix,
            )

        # Rebuild prompt with user answers + director's interpretation
        prompt = buildPrompt(
            visualSummary=scene["visual_summary"] or "",
            mood=scene["mood"] or "neutral",
            answers=body.answers,
        )

        # Append director's refined prompt modifier (or raw feedback as fallback)
        if director_notes:
            prompt += f", {director_notes['prompt_modifier']}"
        elif body.feedback:
            prompt += f", artistic direction: {body.feedback}"

        # Append visual consistency context (cross-scene)
        if consistencySuffix:
            prompt += f", {consistencySuffix}"

        # Carry forward key visual anchors from previous iteration (within-scene)
        if prev_prompt:
            # Extract the core visual description from the previous prompt
            # (strip the style prefix and mood modifier, keep scene-specific content)
            # to give the image generator real context about what to maintain
            core_prev = prev_prompt
            # Remove common prefixes that aren't scene-specific
            for prefix in [
                "cinematic storyboard frame, detailed color illustration, film pre-visualization style, ",
            ]:
                if core_prev.startswith(prefix):
                    core_prev = core_prev[len(prefix):]
            # Truncate to keep only the most important visual details (first ~400 chars)
            if len(core_prev) > 400:
                cut = core_prev[:400].rfind(",")
                if cut > 200:
                    core_prev = core_prev[:cut]
                else:
                    core_prev = core_prev[:400]
            prompt += f", IMPORTANT - match previous frame: {core_prev}"
            prompt += ", maintain exact same character appearances, setting layout, camera angle, color palette, and art style as previous iteration"

        # Generate new sketch
        image = generateImage(prompt)

        # Save iteration to DB
        iteration_id = uuid.uuid4().hex
        sketch_url = f"/static/images/{image.filePath.split('/')[-1]}"
        await db.execute(
            """INSERT INTO scene_iterations
               (id, scene_id, iteration_number, prompt_used, answers, feedback, sketch_url, image_provider, director_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (iteration_id, scene_id, next_iteration, prompt,
             to_json(body.answers), body.feedback, sketch_url, image.source,
             to_json(director_notes))
        )

        # Update scene's current iteration
        await db.execute(
            "UPDATE scenes SET current_iteration_id = ?, updated_at = datetime('now') WHERE id = ?",
            (iteration_id, scene_id)
        )

        # Generate fresh clarifying questions for the next iteration
        # (context-aware, avoids repeating previous questions)
        if next_iteration < MAX_REFINEMENTS:
            try:
                prev_questions = from_json(scene["clarifying_questions"]) or []
                print(f"🔄 Generating new questions for iteration {next_iteration + 1} (prev had {len(prev_questions)} questions)")
                new_questions = generateRefinementQuestions(
                    heading=scene["heading"] or "",
                    description=scene["description"],
                    mood=scene["mood"] or "neutral",
                    visual_summary=scene["visual_summary"] or "",
                    previous_questions=prev_questions,
                    previous_answers=body.answers,
                    feedback=body.feedback,
                    iteration_number=next_iteration,
                )
                if new_questions:
                    print(f"✅ Generated {len(new_questions)} new clarifying questions")
                    for q in new_questions:
                        print(f"   → {q.get('question', '')[:80]}")
                    await db.execute(
                        "UPDATE scenes SET clarifying_questions = ? WHERE id = ?",
                        (to_json(new_questions), scene_id)
                    )
                else:
                    print("⚠️  generateRefinementQuestions returned empty list")
            except Exception as e:
                import traceback
                print(f"❌ Failed to generate refinement questions: {e}")
                traceback.print_exc()
        else:
            print(f"ℹ️  Skipping question generation: iteration {next_iteration} >= MAX_REFINEMENTS {MAX_REFINEMENTS}")

        await db.commit()

        # Return updated scene
        scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        updated_scene = await scene_row.fetchone()
        return await _build_scene_response(db, updated_scene)
    finally:
        await db.close()


# ── Director Consultation ──

@router.post("/scenes/{scene_id}/consult", response_model=ConsultResponse)
async def consult_scene(scene_id: str, body: ConsultRequest):
    """Start a conversation with the Director Agent about how to refine a scene."""
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is locked")

        context = await getProjectContext(scene["project_id"])
        consistencySuffix = buildConsistencyPrompt(context)

        notes = consult_director(
            heading=scene["heading"] or "",
            description=scene["description"],
            mood=scene["mood"] or "neutral",
            visual_summary=scene["visual_summary"] or "",
            feedback=body.feedback,
            answers=body.answers,
            consistency_context=consistencySuffix,
        )

        return ConsultResponse(**notes)
    finally:
        await db.close()


@router.post("/scenes/{scene_id}/consult/respond", response_model=ConsultResponse)
async def consult_respond(scene_id: str, body: ConsultFollowUpRequest):
    """Continue the Director conversation after answering a follow-up question."""
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is locked")

        notes = continue_consultation(
            heading=scene["heading"] or "",
            description=scene["description"],
            mood=scene["mood"] or "neutral",
            visual_summary=scene["visual_summary"] or "",
            conversation_history=body.conversation_history,
            user_response=body.response,
        )

        return ConsultResponse(**notes)
    finally:
        await db.close()


# ── Lock Scene ──

@router.post("/scenes/{scene_id}/lock", response_model=SceneResponse)
async def lock_scene(scene_id: str):
    """Lock a scene and extract visual details for cross-scene consistency."""
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is already locked")

        # Extract visual details for consistency with future scenes
        details = extractVisualDetails(
            heading=scene["heading"] or "",
            description=scene["description"],
            visualSummary=scene["visual_summary"] or "",
        )

        # Lock the scene and store visual context
        await db.execute(
            "UPDATE scenes SET locked = 1, visual_context = ?, updated_at = datetime('now') WHERE id = ?",
            (to_json(details), scene_id)
        )
        await db.commit()

        scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        updated_scene = await scene_row.fetchone()
        return await _build_scene_response(db, updated_scene)
    finally:
        await db.close()


@router.post("/scenes/{scene_id}/unlock", response_model=SceneResponse)
async def unlock_scene(scene_id: str):
    """Unlock a scene so it can be refined again."""
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if not scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is already unlocked")

        await db.execute(
            "UPDATE scenes SET locked = 0, visual_context = NULL, updated_at = datetime('now') WHERE id = ?",
            (scene_id,)
        )
        await db.commit()

        scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        updated_scene = await scene_row.fetchone()
        return await _build_scene_response(db, updated_scene)
    finally:
        await db.close()


# ── Structure Analysis ──

@router.get("/projects/{project_id}/structure", response_model=StructureAnalysis)
async def get_structure_analysis(project_id: str):
    """Analyze the full screenplay structure: pacing, tension arcs, tonal shifts."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        scene_rows = await db.execute(
            "SELECT scene_number, heading, mood, mood_confidence FROM scenes WHERE project_id = ? ORDER BY scene_number",
            (project_id,)
        )
        scenes = await scene_rows.fetchall()

        if not scenes:
            raise HTTPException(status_code=400, detail="No scenes to analyze")

        scene_moods = [
            {
                "scene_number": s["scene_number"],
                "heading": s["heading"],
                "mood": s["mood"],
                "confidence": s["mood_confidence"],
            }
            for s in scenes
        ]

        return await analyze_structure(scene_moods)
    finally:
        await db.close()


# ── Helper ──

async def _build_scene_response(db, scene) -> SceneResponse:
    """Build a SceneResponse from a DB row, including iterations + shot suggestions."""
    iter_rows = await db.execute(
        "SELECT * FROM scene_iterations WHERE scene_id = ? ORDER BY iteration_number",
        (scene["id"],)
    )
    iterations = await iter_rows.fetchall()

    iteration_responses = []
    for it in iterations:
        notes_raw = from_json(it["director_notes"]) if "director_notes" in it.keys() else None
        notes = DirectorNotes(**notes_raw) if notes_raw else None
        iteration_responses.append(SceneIterationResponse(
            id=it["id"],
            iteration_number=it["iteration_number"],
            prompt_used=it["prompt_used"],
            answers=from_json(it["answers"]),
            feedback=it["feedback"],
            sketch_url=it["sketch_url"],
            image_provider=it["image_provider"],
            director_notes=notes,
            created_at=it["created_at"]
        ))

    current = None
    if scene["current_iteration_id"]:
        current = next((i for i in iteration_responses if i.id == scene["current_iteration_id"]), None)

    shots = None
    if scene["mood"]:
        shots = suggest_shots(scene["mood"], scene["description"])

    return SceneResponse(
        id=scene["id"],
        project_id=scene["project_id"],
        scene_number=scene["scene_number"],
        heading=scene["heading"],
        description=scene["description"],
        mood=scene["mood"],
        mood_confidence=scene["mood_confidence"],
        vague_elements=from_json(scene["vague_elements"]) or [],
        clarifying_questions=from_json(scene["clarifying_questions"]) or [],
        visual_summary=scene["visual_summary"],
        shot_suggestions=shots,
        current_iteration=current,
        iterations=iteration_responses,
        locked=bool(scene["locked"]),
        created_at=scene["created_at"],
        updated_at=scene["updated_at"]
    )
