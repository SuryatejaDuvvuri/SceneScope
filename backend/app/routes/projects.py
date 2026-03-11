import uuid
from fastapi import APIRouter, HTTPException
from app.db import get_db, to_json, from_json
from app.models.project import ProjectCreate, ProjectResponse, ProjectSummary
from app.models.scene import ScenesCreate, SceneResponse, SceneIterationResponse, DirectorNotes
from app.services.parser import ParsedScene, buildScene, parseHeading
from app.services.moodClassifier import classify_mood
from app.services.sceneAnalyzer import analyzeScene
from app.services.promptBuilder import buildPrompt
from app.services.imageGenerator import generateImage
from screenplay_tools.fountain.parser import Parser

router = APIRouter(tags=["projects"])

@router.post("/projects", response_model=ProjectResponse)
async def create_project(body: ProjectCreate):
    db = await get_db()
    project_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO projects (id, title, genre, time_period, tone, films) VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, body.title, body.genre, body.time_period, body.tone, to_json(body.films))
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
async def list_projects():
    db = await get_db()
    rows = await db.execute("SELECT id, title, genre, created_at FROM projects ORDER BY created_at DESC")
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
async def get_project(project_id: str):
    db = await get_db()
    row = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
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
async def delete_project(project_id: str):
    """Delete a project and all its scenes/iterations (CASCADE)."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return {"status": "deleted", "project_id": project_id}
    finally:
        await db.close()


@router.delete("/projects/{project_id}/scenes")
async def reset_scenes(project_id: str):
    """Delete all scenes for a project so the user can re-paste screenplay text."""
    db = await get_db()
    try:
        row = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        await db.execute("DELETE FROM scenes WHERE project_id = ?", (project_id,))
        await db.commit()
        return {"status": "reset", "project_id": project_id}
    finally:
        await db.close()


# ── Scenes Pipeline ──

@router.post("/projects/{project_id}/scenes", response_model=list[SceneResponse])
async def create_scenes(project_id: str, body: ScenesCreate):
    """The main pipeline: parse → classify mood → analyze → build prompt → generate sketch."""
    db = await get_db()

    # Verify project exists
    row = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    project = await row.fetchone()
    if not project:
        await db.close()
        raise HTTPException(status_code=404, detail="Project not found")

    # Step 1: Parse screenplay text into scenes
    fountain_parser = Parser()
    fountain_parser.add_text(body.text)

    parsed_scenes = []
    scene_number = 1
    current_heading = None
    description_lines = []
    collecting_description = False
    has_heading = False

    for element in fountain_parser.script.elements:
        el_type = element.__class__.__name__
        if el_type == "SceneHeading":
            has_heading = True
            if current_heading is not None:
                parsed_scenes.append(buildScene(scene_number, current_heading, description_lines))
                scene_number += 1
            current_heading = element.text
            description_lines = []
            collecting_description = True
        elif el_type == "Action":
            if collecting_description or not has_heading:
                description_lines.append(element.text)
        elif el_type in ("Dialogue", "Character", "Parenthetical", "Transition"):
            collecting_description = False

    if current_heading is not None:
        parsed_scenes.append(buildScene(scene_number, current_heading, description_lines))
    elif not has_heading and description_lines:
        parsed_scenes.append(buildScene(1, None, description_lines))

    # Step 2-5: For each parsed scene, run the full pipeline
    scene_responses = []
    errors = []

    for parsed in parsed_scenes:
        try:
            # Step 2: Classify mood
            mood_result = classify_mood(parsed.description)

            # Step 3: Analyze scene (vague elements, questions, visual summary)
            analysis = analyzeScene(
                heading=parsed.heading or "UNKNOWN",
                description=parsed.description,
                mood=mood_result.mood
            )

            # Step 4: Build image prompt
            prompt = buildPrompt(
                visualSummary=analysis.visualSummary,
                mood=mood_result.mood
            )

            # Step 5: Generate sketch
            image = generateImage(prompt)

            # Save scene to DB
            scene_id = uuid.uuid4().hex
            await db.execute(
                """INSERT INTO scenes (id, project_id, scene_number, heading, description,
                   mood, mood_confidence, vague_elements, clarifying_questions, visual_summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (scene_id, project_id, parsed.sceneNumber, parsed.heading, parsed.description,
                 mood_result.mood, mood_result.confidence,
                 to_json(analysis.vagueElements), to_json(analysis.clarifyingQuestions),
                 analysis.visualSummary)
            )

            # Save first iteration
            iteration_id = uuid.uuid4().hex
            sketch_url = f"/static/images/{image.filePath.split('/')[-1]}"
            await db.execute(
                """INSERT INTO scene_iterations (id, scene_id, iteration_number, prompt_used, sketch_url, image_provider)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (iteration_id, scene_id, 1, prompt, sketch_url, image.source)
            )

            # Link iteration to scene
            await db.execute(
                "UPDATE scenes SET current_iteration_id = ? WHERE id = ?",
                (iteration_id, scene_id)
            )

            await db.commit()

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
        current_iteration=current,
        iterations=iteration_responses,
        locked=bool(scene["locked"]),
        created_at=scene["created_at"],
        updated_at=scene["updated_at"]
    )
