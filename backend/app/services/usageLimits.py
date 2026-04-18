from fastapi import HTTPException

from app.config import settings


async def enforce_project_scene_limit(db, project_id: str, additional_scenes: int) -> None:
    """Prevent a single project from growing unbounded."""
    row = await db.execute(
        "SELECT COUNT(*) as c FROM scenes WHERE project_id = ?",
        (project_id,),
    )
    current = await row.fetchone()
    total_after = (current["c"] if current else 0) + max(0, additional_scenes)
    if total_after > settings.MAX_SCENES_PER_PROJECT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Scene limit reached for this project "
                f"({settings.MAX_SCENES_PER_PROJECT} max). "
                f"Current: {current['c'] if current else 0}, requested: {additional_scenes}."
            ),
        )


def enforce_upload_scene_limit(parsed_scene_count: int) -> None:
    """Guard expensive batch scene generation from huge screenplay pastes."""
    if parsed_scene_count > settings.MAX_SCENES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Upload contains {parsed_scene_count} scenes. "
                f"Maximum per upload is {settings.MAX_SCENES_PER_UPLOAD}. "
                "Split your screenplay into smaller chunks and add scenes in batches."
            ),
        )


async def enforce_daily_image_limit(db, user_id: str, requested_images: int) -> None:
    """Basic rate limit by generated images/day (proxy for provider cost)."""
    row = await db.execute(
        """
        SELECT COUNT(*) as c
        FROM scene_iterations si
        JOIN scenes s ON si.scene_id = s.id
        JOIN projects p ON s.project_id = p.id
        WHERE p.user_id = ? AND date(si.created_at) = date('now')
        """,
        (user_id,),
    )
    current = await row.fetchone()
    used_today = current["c"] if current else 0
    projected = used_today + max(0, requested_images)
    if projected > settings.MAX_IMAGE_GENERATIONS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily generation limit exceeded ({settings.MAX_IMAGE_GENERATIONS_PER_DAY}/day). "
                f"Used today: {used_today}, requested: {requested_images}. Try again tomorrow."
            ),
        )
