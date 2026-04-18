"""
Scenes API Routes
─────────────────
Handles the refinement loop, locking, and structure analysis.

The initial scene creation pipeline is in routes/projects.py (POST /projects/{id}/scenes).
This file handles everything AFTER initial creation.
"""

import uuid
import re
from fastapi import APIRouter, HTTPException, Depends
from app.db import get_db, to_json, from_json
from app.models.scene import (
    RefineRequest, SceneResponse, SceneIterationResponse, DirectorNotes,
    ConsultRequest, ConsultFollowUpRequest, ConsultResponse,
)
from app.models.common import StructureAnalysis
from app.services.promptBuilder import buildPrompt
from app.services.imageGenerator import generateImage
from app.services.moodClassifier import classify_mood
from app.services.shotSuggester import suggest_shots
from app.services.visualConsistency import (
    extractVisualDetails,
    getProjectContext,
    buildConsistencyPrompt,
    save_character_reference,
    get_character_refs_for_scene,
    get_existing_characters,
    ensure_character_portraits,
    project_seed,
)
from app.services.structureAnalyzer import analyze_structure
from app.services.directorAgent import consult_director, continue_consultation
from app.services.sceneAnalyzer import generateRefinementQuestions
from app.services.textSummary import summarize_to_chars
from app.services.usageLimits import enforce_daily_image_limit
from app.config import settings
from app.auth import get_current_user

router = APIRouter(tags=["scenes"])

MAX_REFINEMENTS = 3


async def _get_project_genre(db, project_id: str) -> str | None:
    """Fetch the genre of a project for reference library lookups."""
    row = await db.execute("SELECT genre FROM projects WHERE id = ?", (project_id,))
    project = await row.fetchone()
    return project["genre"] if project else None


async def _get_project_films(db, project_id: str) -> list[str]:
    row = await db.execute("SELECT films FROM projects WHERE id = ?", (project_id,))
    project = await row.fetchone()
    if not project:
        return []
    return from_json(project["films"]) or []


async def _get_project_style(db, project_id: str) -> tuple[str | None, str | None]:
    """Fetch project time_period and visual tone."""
    row = await db.execute("SELECT time_period, tone FROM projects WHERE id = ?", (project_id,))
    project = await row.fetchone()
    if not project:
        return None, None
    return project["time_period"], project["tone"]


def _dialogue_characters(dialogue_lines: list[dict]) -> list[str]:
    """Extract unique speaking character names in stable order."""
    seen: set[str] = set()
    names: list[str] = []
    for line in dialogue_lines or []:
        raw = (line.get("character") or "").strip()
        if not raw or raw.upper() == "UNKNOWN":
            continue
        key = raw.upper()
        if key in seen:
            continue
        seen.add(key)
        names.append(raw)
    return names


def _named_subjects_from_text(text: str) -> list[str]:
    """Extract likely character names from screenplay action text."""
    blacklist = {
        "INT", "EXT", "DAY", "NIGHT", "MORNING", "EVENING", "NOON",
        "CUT TO", "FADE IN", "FADE OUT",
    }
    pattern = r"\b[A-Z][A-Z]+(?:\s+[A-Z][A-Z]+){0,2}\b"
    candidates = re.findall(pattern, text or "")
    seen: set[str] = set()
    names: list[str] = []
    for c in candidates:
        cleaned = c.strip()
        if cleaned in blacklist:
            continue
        if len(cleaned) < 3:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        names.append(cleaned.title())
    return names


def _required_subjects(description: str, dialogue_lines: list[dict]) -> list[str]:
    """Merge dialogue speakers + uppercase action-line character mentions."""
    merged: list[str] = []
    seen: set[str] = set()
    for name in _dialogue_characters(dialogue_lines) + _named_subjects_from_text(description):
        key = name.strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(name.strip())
    return merged


def _ambient_population_hint(heading: str | None, description: str) -> str | None:
    """Setting-aware extras hint for more realistic first-pass frames."""
    text = f"{heading or ''}\n{description}".lower()
    crowded_setting_keywords = (
        "bar", "pub", "club", "cafe", "coffee shop", "restaurant", "campus",
        "classroom", "hallway", "street", "market", "party",
    )
    isolation_keywords = ("empty", "abandoned", "deserted", "vacant", "alone")

    if any(k in text for k in isolation_keywords):
        return "background population: keep environment sparsely populated or empty if story context demands isolation"
    if any(k in text for k in crowded_setting_keywords):
        return "background population: include plausible ambient extras (patrons/students/bystanders) without replacing the primary named characters"
    return None


async def _verify_scene_ownership(db, scene_id: str, user_id: str):
    """Verify user owns the project that contains this scene. Returns scene row or raises 404."""
    row = await db.execute(
        """SELECT s.* FROM scenes s
           JOIN projects p ON s.project_id = p.id
           WHERE s.id = ? AND p.user_id = ?""",
        (scene_id, user_id),
    )
    scene = await row.fetchone()
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene


# ── Refinement Loop ──

@router.post("/scenes/{scene_id}/refine", response_model=SceneResponse)
async def refine_scene(scene_id: str, body: RefineRequest, user: dict = Depends(get_current_user)):
    """Refine a scene: rebuild prompt with user answers + visual context, regenerate sketch."""
    db = await get_db()
    try:
        # Fetch scene and verify ownership
        scene = await _verify_scene_ownership(db, scene_id, user["id"])
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

        # Get visual context from locked scenes for cross-scene consistency.
        # Filter to characters/locations actually mentioned in THIS scene so the
        # prompt isn't drowned by every character the project has ever locked.
        context = await getProjectContext(scene["project_id"])
        scene_text_for_filter = f"{scene['heading'] or ''}\n{scene['description'] or ''}"
        consistencySuffix = buildConsistencyPrompt(context, scene_text=scene_text_for_filter)

        # Get previous iteration's prompt for within-scene consistency
        prev_prompt = ""
        prev_sketch_url = None
        if scene["current_iteration_id"]:
            prev_row = await db.execute(
                "SELECT prompt_used, sketch_url FROM scene_iterations WHERE id = ?",
                (scene["current_iteration_id"],)
            )
            prev_iter = await prev_row.fetchone()
            if prev_iter:
                prev_prompt = prev_iter["prompt_used"]
                prev_sketch_url = prev_iter["sketch_url"]

        project_films = await _get_project_films(db, scene["project_id"])
        project_time_period, project_tone = await _get_project_style(db, scene["project_id"])

        # Use pre-confirmed director notes from /consult flow, or consult on the fly
        director_notes = None
        if body.director_notes:
            director_notes = body.director_notes
        elif body.feedback:
            genre = await _get_project_genre(db, scene["project_id"])
            # Gather previous iteration history so director knows what's been tried
            history_rows = await db.execute(
                "SELECT iteration_number, feedback, director_notes FROM scene_iterations WHERE scene_id = ? ORDER BY iteration_number",
                (scene_id,)
            )
            iteration_history = [dict(r) for r in await history_rows.fetchall()]
            director_notes = consult_director(
                heading=scene["heading"] or "",
                description=scene["description"],
                mood=scene["mood"] or "neutral",
                visual_summary=scene["visual_summary"] or "",
                feedback=body.feedback,
                answers=body.answers,
                consistency_context=consistencySuffix,
                genre=genre,
                iteration_history=iteration_history,
            )

        # Rebuild prompt with user answers + director's interpretation.
        # Consistency is now placed at the FRONT of the prompt (right after the
        # style anchor) so character/location descriptions get high attention
        # weight from the diffusion model — this is the single biggest lever
        # for cross-scene character identity stability.
        scene_dialogue = from_json(scene["dialogue"]) if scene["dialogue"] else []
        required_subjects = _required_subjects(scene["description"] or "", scene_dialogue)
        ambient_hint = _ambient_population_hint(scene["heading"], scene["description"] or "")
        prompt = buildPrompt(
            visualSummary=scene["visual_summary"] or "",
            mood=scene["mood"] or "neutral",
            answers=body.answers,
            reference_films=project_films,
            consistency=consistencySuffix or None,
            required_subjects=required_subjects or None,
            time_period=project_time_period,
            tone=project_tone,
            ambient_population_hint=ambient_hint,
        )

        # Append director's refined prompt modifier (or raw feedback as fallback)
        if director_notes:
            prompt += f", {director_notes['prompt_modifier']}"
        elif body.feedback:
            prompt += f", artistic direction: {body.feedback}"

        # Carry forward key visual anchors from previous iteration (within-scene)
        if prev_prompt:
            # Extract the core visual description from the previous prompt
            # (strip the style prefix and mood modifier, keep scene-specific content)
            # to give the image generator real context about what to maintain
            core_prev = prev_prompt
            # Remove the style prefix that isn't scene-specific
            from app.services.promptBuilder import STYLE_PREFIX
            if core_prev.startswith(STYLE_PREFIX):
                core_prev = core_prev[len(STYLE_PREFIX):].lstrip(", ")
            core_prev = summarize_to_chars(
                core_prev,
                400,
                focus_text=f"{scene['heading'] or ''} {scene['mood'] or ''} visual continuity",
            )
            prompt += f", IMPORTANT - match previous frame: {core_prev}"
            prompt += ", maintain exact same character appearances, setting layout, architecture, camera angle, color palette, and art style as previous iteration. Only apply the requested refinements, do not change anything else"

        # Generate new sketch
        reference_image_url = None
        if prev_sketch_url:
            # If backend URL is configured publicly, providers can use this image as conditioning input.
            base = getattr(settings, "BACKEND_PUBLIC_URL", "").rstrip("/")
            if base:
                reference_image_url = f"{base}{prev_sketch_url}"
            elif settings.STRICT_REFERENCE_REFINEMENT:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Refinement consistency requires BACKEND_PUBLIC_URL so providers can access "
                        "the previous frame as a reference image."
                    ),
                )

        # Only pass character refs whose names appear in this scene — passing
        # the full project roster confuses character-conditioned providers.
        char_refs = await get_character_refs_for_scene(scene["project_id"], scene_text_for_filter)

        # Per-project deterministic seed: same project → consistent style,
        # composition rhythm, and color palette across all scenes.
        gen_seed = project_seed(scene["project_id"])

        # Rate limit: each refinement consumes one additional image generation.
        await enforce_daily_image_limit(db, user["id"], 1)

        image = generateImage(
            prompt,
            reference_image_url=reference_image_url,
            character_refs=char_refs or None,
            seed=gen_seed,
            scene_text=scene_text_for_filter,
            strict_reference_mode=bool(reference_image_url) and settings.STRICT_REFERENCE_REFINEMENT,
        )

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
                print(f"Generating new questions for iteration {next_iteration + 1} (prev had {len(prev_questions)} questions)")
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
                    print(f"Generated {len(new_questions)} new clarifying questions")
                    for q in new_questions:
                        print(f"   → {q.get('question', '')[:80]}")
                    await db.execute(
                        "UPDATE scenes SET clarifying_questions = ? WHERE id = ?",
                        (to_json(new_questions), scene_id)
                    )
                else:
                    print("Refinement Questions returned empty list")
            except Exception as e:
                import traceback
                print(f"Failed to generate refinement questions: {e}")
                traceback.print_exc()
        else:
            print(f"Skipping question generation: iteration {next_iteration} >= MAX_REFINEMENTS {MAX_REFINEMENTS}")

        await db.commit()


        scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        updated_scene = await scene_row.fetchone()
        return await _build_scene_response(db, updated_scene)
    finally:
        await db.close()

@router.post("/scenes/{scene_id}/consult", response_model=ConsultResponse)
async def consult_scene(scene_id: str, body: ConsultRequest, user: dict = Depends(get_current_user)):
    """Start a conversation with the Director Agent about how to refine a scene."""
    db = await get_db()
    try:
        scene = await _verify_scene_ownership(db, scene_id, user["id"])
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is locked")

        context = await getProjectContext(scene["project_id"])
        consistencySuffix = buildConsistencyPrompt(
            context,
            scene_text=f"{scene['heading'] or ''}\n{scene['description'] or ''}",
        )
        genre = await _get_project_genre(db, scene["project_id"])

        notes = consult_director(
            heading=scene["heading"] or "",
            description=scene["description"],
            mood=scene["mood"] or "neutral",
            visual_summary=scene["visual_summary"] or "",
            feedback=body.feedback,
            answers=body.answers,
            consistency_context=consistencySuffix,
            genre=genre,
        )

        return ConsultResponse(**notes)
    finally:
        await db.close()


@router.post("/scenes/{scene_id}/consult/respond", response_model=ConsultResponse)
async def consult_respond(scene_id: str, body: ConsultFollowUpRequest, user: dict = Depends(get_current_user)):
    """Continue the Director conversation after answering a follow-up question."""
    db = await get_db()
    try:
        scene = await _verify_scene_ownership(db, scene_id, user["id"])
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is locked")

        genre = await _get_project_genre(db, scene["project_id"])

        notes = continue_consultation(
            heading=scene["heading"] or "",
            description=scene["description"],
            mood=scene["mood"] or "neutral",
            visual_summary=scene["visual_summary"] or "",
            conversation_history=body.conversation_history,
            user_response=body.response,
            genre=genre,
        )

        return ConsultResponse(**notes)
    finally:
        await db.close()


# ── Lock Scene ──

@router.post("/scenes/{scene_id}/lock", response_model=SceneResponse)
async def lock_scene(scene_id: str, user: dict = Depends(get_current_user)):
    """Lock a scene and extract visual details for cross-scene consistency."""
    db = await get_db()
    try:
        scene = await _verify_scene_ownership(db, scene_id, user["id"])
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")
        if scene["locked"]:
            raise HTTPException(status_code=400, detail="Scene is already locked")

        # Pass the existing canonical roster so the extractor reuses prior
        # descriptions verbatim for any returning character (prevents drift).
        known_roster = await get_existing_characters(db, scene["project_id"])
        details = extractVisualDetails(
            heading=scene["heading"] or "",
            description=scene["description"],
            visualSummary=scene["visual_summary"] or "",
            known_characters=known_roster,
        )

        # Lock the scene and store visual context
        await db.execute(
            "UPDATE scenes SET locked = 1, visual_context = ?, updated_at = datetime('now') WHERE id = ?",
            (to_json(details), scene_id)
        )
        await db.commit()

        # Persist canonical character descriptions. ``save_character_reference``
        # does NOT overwrite existing descriptions, so the first lock for each
        # character defines them forever (any later re-extraction is ignored).
        # We deliberately do NOT save the scene sketch as the character's
        # ``image_url`` — a wide-shot group sketch is a terrible character
        # reference and was actively poisoning Ideogram's character_reference
        # input. Real per-character portraits are generated below.
        new_characters: dict[str, str] = {}
        for char_name, char_desc in (details.get("characters") or {}).items():
            await save_character_reference(
                project_id=scene["project_id"],
                character_name=char_name,
                image_url=None,
                description=char_desc,
            )
            if char_name not in known_roster:
                new_characters[char_name] = char_desc

        # Generate a clean solo portrait for each character that's new to the
        # project. Best-effort: if portrait generation fails, lock still
        # succeeds. These portraits become the character_reference inputs for
        # all subsequent scenes featuring this character.
        if new_characters:
            try:
                await ensure_character_portraits(scene["project_id"], new_characters)
            except Exception as e:
                print(f"ensure_character_portraits failed: {e}")

        scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        updated_scene = await scene_row.fetchone()
        return await _build_scene_response(db, updated_scene)
    finally:
        await db.close()


@router.post("/scenes/{scene_id}/unlock", response_model=SceneResponse)
async def unlock_scene(scene_id: str, user: dict = Depends(get_current_user)):
    """Unlock a scene so it can be refined again."""
    db = await get_db()
    try:
        scene = await _verify_scene_ownership(db, scene_id, user["id"])
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
async def get_structure_analysis(project_id: str, user: dict = Depends(get_current_user)):
    """Analyze the full screenplay structure: pacing, tension arcs, tonal shifts."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
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
    # Lazily re-classify scenes that have 0 confidence (created before the local model was wired up)
    mood = scene["mood"]
    mood_confidence = scene["mood_confidence"]
    if (mood_confidence is None or mood_confidence == 0.0) and scene["description"]:
        try:
            result = classify_mood(scene["description"])
            if result.confidence > 0:
                await db.execute(
                    "UPDATE scenes SET mood = ?, mood_confidence = ? WHERE id = ?",
                    (result.mood, result.confidence, scene["id"])
                )
                await db.commit()
                mood = result.mood
                mood_confidence = result.confidence
        except Exception as e:
            print(f"Lazy mood re-classify failed: {e}")

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
    if mood:
        shots = suggest_shots(mood, scene["description"])

    # Parse dialogue if available
    dialogue = []
    try:
        dialogue_raw = from_json(scene["dialogue"]) if scene["dialogue"] else []
        dialogue = dialogue_raw or []
    except Exception:
        pass

    return SceneResponse(
        id=scene["id"],
        project_id=scene["project_id"],
        scene_number=scene["scene_number"],
        heading=scene["heading"],
        description=scene["description"],
        mood=mood,
        mood_confidence=mood_confidence,
        vague_elements=from_json(scene["vague_elements"]) or [],
        clarifying_questions=from_json(scene["clarifying_questions"]) or [],
        visual_summary=scene["visual_summary"],
        dialogue=dialogue,
        shot_suggestions=shots,
        current_iteration=current,
        iterations=iteration_responses,
        locked=bool(scene["locked"]),
        created_at=scene["created_at"],
        updated_at=scene["updated_at"]
    )
