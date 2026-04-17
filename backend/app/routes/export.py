"""
Export Routes
─────────────
PDF storyboard export using fpdf2.
"""

import os
import tempfile
import unicodedata
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from fpdf import FPDF
from app.db import get_db, from_json
from app.config import settings
from app.auth import get_current_user

router = APIRouter(tags=["export"])



# Use DejaVuSans for Unicode support
FONT_DIR = os.path.join(os.path.dirname(__file__), "../../static/fonts")
DEJAVU = os.path.abspath(os.path.join(FONT_DIR, "DejaVuSans.ttf"))
DEJAVU_BOLD = os.path.abspath(os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"))

class StoryboardPDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefer Unicode DejaVu fonts if available; otherwise fallback to built-in Helvetica.
        self.base_font_family = "Helvetica"
        self.supports_italic = True

        if os.path.isfile(DEJAVU) and os.path.isfile(DEJAVU_BOLD):
            self.add_font("DejaVu", "", DEJAVU, uni=True)
            self.add_font("DejaVu", "B", DEJAVU_BOLD, uni=True)
            self.base_font_family = "DejaVu"
            # Only regular + bold are bundled; drop italic styles when DejaVu is active.
            self.supports_italic = False
        else:
            print(
                "Export font fallback: DejaVu TTF files not found. "
                "Using Helvetica for PDF export."
            )

        self.set_pdf_font(size=12)

    def set_pdf_font(self, style: str = "", size: int = 12):
        safe_style = style
        if not self.supports_italic:
            safe_style = safe_style.replace("I", "")
        self.set_font(self.base_font_family, safe_style, size)

    def safe_text(self, text: str | None) -> str:
        """Ensure text is compatible with fallback core fonts that are Latin-1 only."""
        if text is None:
            return ""
        value = str(text)

        # DejaVu supports Unicode directly.
        if self.base_font_family == "DejaVu":
            return value

        substitutions = str.maketrans({
            "—": "-",
            "–": "-",
            "‘": "'",
            "’": "'",
            "“": '"',
            "”": '"',
            "…": "...",
            "\u00A0": " ",
        })
        value = value.translate(substitutions)
        value = unicodedata.normalize("NFKD", value)
        return value.encode("latin-1", "replace").decode("latin-1")

    def header(self):
        self.set_pdf_font("B", 14)
        self.cell(0, 10, self.safe_text(self.title), align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
 
    def footer(self):
        self.set_y(-15)
        self.set_pdf_font("I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def _add_scene_page(pdf: StoryboardPDF, scene: dict, sketch_path: str | None):
    """Add a single scene to the PDF."""
    pdf.add_page()

    # Scene heading
    heading = scene["heading"] or f"Scene {scene['scene_number']}"
    pdf.set_pdf_font("B", 12)
    pdf.cell(0, 8, pdf.safe_text(f"Scene {scene['scene_number']}: {heading}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Sketch image
    if sketch_path and os.path.isfile(sketch_path):
        page_width = pdf.w - pdf.l_margin - pdf.r_margin
        img_width = min(page_width, 160)
        pdf.image(sketch_path, x=pdf.l_margin, w=img_width)
        pdf.ln(4)

    # Mood
    if scene["mood"]:
        pdf.set_pdf_font("B", 10)
        pdf.cell(20, 6, pdf.safe_text("Mood: "))
        pdf.set_pdf_font("", 10)
        confidence = scene["mood_confidence"] or 0
        pdf.cell(0, 6, pdf.safe_text(f"{scene['mood']} ({confidence:.0%})"), new_x="LMARGIN", new_y="NEXT")

    # Description
    pdf.ln(2)
    pdf.set_pdf_font("B", 10)
    pdf.cell(0, 6, pdf.safe_text("Description:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_pdf_font("", 9)
    pdf.multi_cell(0, 5, pdf.safe_text(scene["description"][:500]))

    # Visual summary
    if scene["visual_summary"]:
        pdf.ln(2)
        pdf.set_pdf_font("B", 10)
        pdf.cell(0, 6, pdf.safe_text("Visual Summary:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_pdf_font("", 9)
        pdf.multi_cell(0, 5, pdf.safe_text(scene["visual_summary"][:300]))


@router.get("/projects/{project_id}/export")
async def export_storyboard(project_id: str, user: dict = Depends(get_current_user)):
    """Generate and download a PDF storyboard of all locked scenes."""
    db = await get_db()
    try:
        # Verify project and ownership
        row = await db.execute("SELECT * FROM projects WHERE id = ? AND user_id = ?", (project_id, user["id"]))
        project = await row.fetchone()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get all scenes (locked ones get full treatment, unlocked get basic info)
        scene_rows = await db.execute(
            "SELECT * FROM scenes WHERE project_id = ? ORDER BY scene_number",
            (project_id,)
        )
        scenes = await scene_rows.fetchall()
        if not scenes:
            raise HTTPException(status_code=400, detail="No scenes to export")

        # Build PDF
        pdf = StoryboardPDF()
        pdf.title = f"{project['title']} — Storyboard"
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=20)

        for scene in scenes:
            # Get the current iteration's sketch
            sketch_path = None
            if scene["current_iteration_id"]:
                iter_row = await db.execute(
                    "SELECT sketch_url FROM scene_iterations WHERE id = ?",
                    (scene["current_iteration_id"],)
                )
                iteration = await iter_row.fetchone()
                if iteration and iteration["sketch_url"]:
                    # Convert URL path to filesystem path
                    filename = iteration["sketch_url"].split("/")[-1]
                    sketch_path = os.path.join(settings.STATIC_DIR, filename)

            _add_scene_page(pdf, dict(scene), sketch_path)

        # Write to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf.output(tmp.name)
        tmp.close()

        safe_title = "".join(c for c in project["title"] if c.isalnum() or c in " -_").strip()
        filename = f"{safe_title}_storyboard.pdf"

        return FileResponse(
            path=tmp.name,
            media_type="application/pdf",
            filename=filename,
        )
    finally:
        await db.close()
