import uuid
import re
from fastapi import APIRouter, HTTPException, Depends
from app.db import get_db, to_json, from_json
from app.models.project import ProjectCreate, ProjectResponse, ProjectSummary
from app.models.scene import ScenesCreate, SceneResponse, SceneIterationResponse, DirectorNotes
from app.services.parser import ParsedScene, buildScene, parseHeading
from app.services.moodClassifier import classify_mood
from app.services.sceneAnalyzer import analyzeScene
from app.services.promptBuilder import buildPrompt, enrich_subjects_with_descriptions, PROMPT_BUILDER_VERSION
from app.services.imageGenerator import generateImage
from app.services.filmStyleExpander import expand_film_styles
from app.services.artistBrief import build_artist_brief
from app.config import settings
from app.services.visualConsistency import (
    extractVisualDetails,
    buildConsistencyPrompt,
    get_character_refs_for_scene,
    get_existing_characters,
    project_seed,
)
from app.models.common import VisualContext
from app.auth import get_current_user
from app.services.usageLimits import (
    enforce_daily_image_limit,
    enforce_project_scene_limit,
    enforce_upload_scene_limit,
)
from screenplay_tools.fountain.parser import Parser

router = APIRouter(tags=["projects"])


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
    """Extract likely character names from screenplay action text.

    Fountain often writes character intros in uppercase in action lines:
    e.g. "MARK ZUCKERBERG is a ...". Capture those so first-pass generation
    includes the characters even before any lock/refine cycle.
    """
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
    """Merge speaker names + named subjects from action text."""
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
    """Return setting-aware extras hint so first output isn't unnaturally empty."""
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

@router.post("/projects", response_model=ProjectResponse)
async def create_project(body: ProjectCreate, user: dict = Depends(get_current_user)):
    db = await get_db()
    project_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO projects (id, user_id, title, genre, time_period, tone, films) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, user["id"], body.title, body.genre, body.time_period, body.tone, to_json(body.films))
    )
    await db.commit()
    row = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = await row.fetchone()
    await db.close()
    return ProjectResponse(
        id=project["id"],
        title=project["title"],
        genre=project["genre"],
        time_period=project["time_period"],
        tone=project["tone"],
        films=from_json(project["films"]) or [],
        scenes=[],
        created_at=project["created_at"],
        updated_at=project["updated_at"]
    )


@router.get("/projects", response_model=list[ProjectSummary])
async def list_projects(user: dict = Depends(get_current_user)):
    db = await get_db()
    rows = await db.execute(
        "SELECT id, title, genre, created_at FROM projects WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    )
    projects = await rows.fetchall()
    result = []
    for p in projects:
        count_row = await db.execute("SELECT COUNT(*) as c FROM scenes WHERE project_id = ?", (p["id"],))
        count = await count_row.fetchone()
        result.append(ProjectSummary(
            id=p["id"],
            title=p["title"],
            genre=p["genre"],
            scene_count=count["c"],
            created_at=p["created_at"]
        ))
    await db.close()
    return result


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    db = await get_db()
    row = await db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
    project = await row.fetchone()
    if not project:
        await db.close()
        raise HTTPException(status_code=404, detail="Project not found")

    scene_rows = await db.execute("SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number", (project_id,))
    scenes = await scene_rows.fetchall()
    scene_responses = []
    for s in scenes:
        scene_responses.append(await _build_scene_response(db, s))
    await db.close()
    return ProjectResponse(
        id=project["id"],
        title=project["title"],
        genre=project["genre"],
        time_period=project["time_period"],
        tone=project["tone"],
        films=from_json(project["films"]) or [],
        scenes=scene_responses,
        created_at=project["created_at"],
        updated_at=project["updated_at"]
    )


# ── Delete / Reset ──

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """Delete a project and all its scenes/iterations (CASCADE)."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return {"status": "deleted", "project_id": project_id}
    finally:
        await db.close()


@router.delete("/projects/{project_id}/scenes")
async def reset_scenes(project_id: str, user: dict = Depends(get_current_user)):
    """Delete all scenes for a project so the user can re-paste screenplay text."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        await db.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))
        await db.commit()
        return {"status": "reset", "project_id": project_id}
    finally:
        await db.close()


# ── Scenes Pipeline ──

@router.post("/projects/{project_id}/scenes", response_model=list[SceneResponse])
async def create_scenes(project_id: str, body: ScenesCreate, user: dict = Depends(get_current_user)):
    """The main pipeline: parse → classify mood → analyze → build prompt → generate sketch."""
    db = await get_db()

    # Verify project exists and belongs to user
    row = await db.execute(
        "SELECT id, films, time_period, tone FROM projects WHERE id = ? AND user_id = ?",
        (project_id, user["id"]),
    )
    project = await row.fetchone()
    if not project:
        await db.close()
        raise HTTPException(status_code=404, detail="Project not found")

    # Step 1: Parse screenplay text into scenes
    fountain_parser = Parser()
    fountain_parser.add_text(body.text)

    parsed_scenes = []
    scene_dialogues = []  # parallel list: dialogue lines per scene
    scene_number = 1
    current_heading = None
    description_lines = []
    dialogue_lines = []
    current_speaker = None
    collecting_description = False
    has_heading = False

    for element in fountain_parser.script.elements:
        el_type = element.__class__.__name__
        if el_type == "SceneHeading":
            has_heading = True
            if current_heading is not None:
                parsed_scenes.append(buildScene(scene_number, current_heading, description_lines))
                scene_dialogues.append(dialogue_lines)
                scene_number += 1
            current_heading = element.text
            description_lines = []
            dialogue_lines = []
            current_speaker = None
            collecting_description = True
        elif el_type == "Action":
            if collecting_description or not has_heading:
                description_lines.append(element.text)
        elif el_type == "Character":
            current_speaker = element.text.strip()
            collecting_description = False
        elif el_type == "Dialogue":
            dialogue_lines.append({
                "character": current_speaker or "UNKNOWN",
                "text": element.text.strip(),
                "parenthetical": None,
            })
            collecting_description = False
        elif el_type == "Parenthetical":
            # Attach to the last dialogue line for the current speaker
            if dialogue_lines and dialogue_lines[-1]["character"] == current_speaker:
                dialogue_lines[-1]["parenthetical"] = element.text.strip()
            collecting_description = False
        elif el_type == "Transition":
            collecting_description = False

    if current_heading is not None:
        parsed_scenes.append(buildScene(scene_number, current_heading, description_lines))
        scene_dialogues.append(dialogue_lines)
    elif not has_heading and description_lines:
        parsed_scenes.append(buildScene(1, None, description_lines))
        scene_dialogues.append(dialogue_lines)

    # Usage controls: per-upload batch size, per-project cap, and daily image quota.
    enforce_upload_scene_limit(len(parsed_scenes))
    await enforce_project_scene_limit(db, project_id, len(parsed_scenes))
    await enforce_daily_image_limit(db, user["id"], len(parsed_scenes))

    # Step 2-5: For each parsed scene, run the full pipeline
    scene_responses = []
    errors = []
    location_cache: dict[str, str] = {}  # location_name -> visual description for cross-scene consistency

    for idx, parsed in enumerate(parsed_scenes):
        try:
            # Step 2: Classify mood
            mood_result = classify_mood(parsed.description)

            # Step 3: Analyze scene (vague elements, questions, visual summary)
            analysis = analyzeScene(
                heading=parsed.heading or "UNKNOWN",
                description=parsed.description,
                mood=mood_result.mood
            )

            # Step 4: Build image prompt (with cross-scene consistency for
            # both characters seen in earlier scenes AND locations previously
            # cached). The consistency string is filtered to entities that
            # actually appear in this scene's description, then placed at the
            # FRONT of the prompt by buildPrompt for high attention weight.
            scene_text_for_filter = f"{parsed.heading or ''}\n{parsed.description}"
            known_chars = await get_existing_characters(db, project_id)
            consistency_ctx = VisualContext(
                characters=known_chars,
                locations=location_cache,
                props={},
            )
            consistency_suffix = buildConsistencyPrompt(
                consistency_ctx,
                scene_text=scene_text_for_filter,
            )

            scene_dialogue = scene_dialogues[idx] if idx < len(scene_dialogues) else []

            # Extract character names from dialogue + action text and enrich with
            # any canonical descriptions already in the roster (from prior locked scenes).
            raw_subjects = _required_subjects(parsed.description, scene_dialogue)
            enriched_subjects = enrich_subjects_with_descriptions(raw_subjects, known_chars)
            ambient_hint = _ambient_population_hint(parsed.heading, parsed.description)

            # Expand reference film titles to actionable visual descriptors.
            # "The Social Network" → "The Social Network (intimate fluorescent-lit interiors, ...)"
            project_films = from_json(project["films"]) or []
            expanded_films = expand_film_styles(project_films) if project_films else []

            # Pre-draw reasoning pass — the mental framing a human artist
            # does before drawing. Injects setting archetype, implicit staging,
            # and emotional beat into the prompt.
            artist_brief = build_artist_brief(parsed.heading or "", parsed.description or "")

            prompt = buildPrompt(
                visualSummary=analysis.visualSummary,
                mood=mood_result.mood,
                reference_films=expanded_films or None,
                consistency=consistency_suffix or None,
                required_subjects=enriched_subjects or None,
                time_period=project["time_period"],
                tone=project["tone"],
                ambient_population_hint=ambient_hint,
                artist_brief=artist_brief,
            )

            # Step 5: Generate sketch with project-deterministic seed and
            # only the character refs whose names appear in this scene.
            char_refs = await get_character_refs_for_scene(project_id, scene_text_for_filter)
            image = generateImage(
                prompt,
                character_refs=char_refs or None,
                seed=project_seed(project_id),
                scene_text=scene_text_for_filter,
            )

            # Save scene to DB (including dialogue if present)
            scene_id = uuid.uuid4().hex
            await db.execute(
                """INSERT INTO scenes (id, project_id, scene_number, heading, description,
                   mood, mood_confidence, vague_elements, clarifying_questions, visual_summary, dialogue)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scene_id, project_id, parsed.sceneNumber, parsed.heading, parsed.description,
                 mood_result.mood, mood_result.confidence,
                 to_json(analysis.vagueElements), to_json(analysis.clarifyingQuestions),
                 analysis.visualSummary, to_json(scene_dialogue) if scene_dialogue else None)
            )

            # Save first iteration
            iteration_id = uuid.uuid4().hex
            sketch_url = f"/static/images/{image.filePath.split('/')[-1]}"
            await db.execute(
                """INSERT INTO scene_iterations
                   (id, scene_id, iteration_number, prompt_used, sketch_url, image_provider, llm_model, planner_version, intent_parser_version, prompt_builder_version)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    iteration_id,
                    scene_id,
                    1,
                    prompt,
                    sketch_url,
                    image.source,
                    settings.GROQ_MODEL,
                    None,
                    None,
                    PROMPT_BUILDER_VERSION,
                )
            )

            # Link iteration to scene
            await db.execute(
                "UPDATE scenes SET current_iteration_id = ? WHERE id = ?",
                (iteration_id, scene_id)
            )

            await db.commit()

            # Extract visual details immediately — subsequent scenes in the
            # same location will reuse them. Pass the known character roster
            # so the extractor doesn't generate fresh, drifting descriptions
            # for characters that already exist in this project.
            try:
                details = extractVisualDetails(
                    heading=parsed.heading or "",
                    description=parsed.description,
                    visualSummary=analysis.visualSummary,
                    known_characters=known_chars,
                )
                if details.get("locations"):
                    await db.execute(
                        "UPDATE scenes SET visual_context = ? WHERE id = ?",
                        (to_json(details), scene_id)
                    )
                    await db.commit()
                    location_cache.update(details["locations"])
            except Exception as e:
                print(f"Scene {parsed.sceneNumber} visual extraction failed: {e}")

            # Build response
            scene_row = await db.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
            scene = await scene_row.fetchone()
            scene_responses.append(await _build_scene_response(db, scene))

        except Exception as e:
            print(f"Scene {parsed.sceneNumber} failed: {e}")
            errors.append({"scene_number": parsed.sceneNumber, "error": str(e)})
            continue

    await db.close()

    if not scene_responses and errors:
        raise HTTPException(
            status_code=500,
            detail=f"All {len(errors)} scenes failed to process. First error: {errors[0]['error']}"
        )

    return scene_responses


# ── Helper ──

async def _build_scene_response(db, scene) -> SceneResponse:
    """Build a SceneResponse from a DB row, including iterations."""
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
            llm_model=it["llm_model"] if "llm_model" in it.keys() else None,
            planner_version=it["planner_version"] if "planner_version" in it.keys() else None,
            intent_parser_version=it["intent_parser_version"] if "intent_parser_version" in it.keys() else None,
            prompt_builder_version=it["prompt_builder_version"] if "prompt_builder_version" in it.keys() else None,
            created_at=it["created_at"]
        ))

    current = None
    if scene["current_iteration_id"]:
        current = next((i for i in iteration_responses if i.id == scene["current_iteration_id"]), None)

    dialogue = from_json(scene["dialogue"]) if scene["dialogue"] else []

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
        dialogue=dialogue or [],
        current_iteration=current,
        iterations=iteration_responses,
        locked=bool(scene["locked"]),
        created_at=scene["created_at"],
        updated_at=scene["updated_at"]
    )
