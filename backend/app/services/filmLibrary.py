"""
Film Reference Library
──────────────────────
A curated internal knowledge base of cinematography techniques, film references,
lighting styles, composition patterns, and director/DP signatures.

The Director Agent queries this library to ground its advice in real-world
filmmaking knowledge rather than relying solely on LLM parametric memory.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ── Data Structures ──


@dataclass
class FilmReference:
    title: str
    year: int
    director: str
    cinematographer: str
    tags: list[str] = field(default_factory=list)          # mood, genre, style
    visual_signature: str = ""                              # what makes it visually distinct
    key_techniques: list[str] = field(default_factory=list) # lighting, color, composition notes


@dataclass
class Technique:
    name: str
    category: str          # lighting | composition | color | movement | lens
    description: str
    when_to_use: str       # emotional / narrative context
    films: list[str] = field(default_factory=list)
    mood_tags: list[str] = field(default_factory=list)


@dataclass
class DPSignature:
    name: str
    known_for: str
    signature_look: str
    notable_films: list[str] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)


# ── Film Reference Catalogue ──

FILMS: list[FilmReference] = [
    # ── Nolan filmography (core references) ──
    FilmReference(
        "Memento", 2000, "Christopher Nolan", "Wally Pfister",
        tags=["tense", "thriller", "nonlinear", "mystery"],
        visual_signature="Desaturated color for forward timeline, stark B&W for reverse; tight handheld framing creates claustrophobia",
        key_techniques=["cross-cutting timelines via color grading", "extreme close-ups on tactile objects", "shallow depth of field for subjective POV"],
    ),
    FilmReference(
        "The Dark Knight", 2008, "Christopher Nolan", "Wally Pfister",
        tags=["action", "tense", "urban", "noir"],
        visual_signature="IMAX-scale wide shots of Chicago architecture juxtaposed with tight, chaotic handheld in action; cold steel-blue palette",
        key_techniques=["practical IMAX for scale", "underexposed shadows for moral ambiguity", "Dutch angles for Joker scenes only"],
    ),
    FilmReference(
        "Inception", 2010, "Christopher Nolan", "Wally Pfister",
        tags=["action", "tense", "sci-fi", "surreal"],
        visual_signature="Clean architectural lines that bend and fold; warm amber for reality, cool blue-grey for deeper dream layers",
        key_techniques=["in-camera rotating corridor set", "layered parallel editing across dream levels", "wide anamorphic for dreamscapes"],
    ),
    FilmReference(
        "Interstellar", 2014, "Christopher Nolan", "Hoyte van Hoytema",
        tags=["somber", "sci-fi", "emotional", "epic"],
        visual_signature="IMAX 65mm grain, vast landscapes dwarfing humans; warm golden farmland vs cold sterile space",
        key_techniques=["natural light on location", "lens flares from actual light sources", "silence in space scenes for realism"],
    ),
    FilmReference(
        "Dunkirk", 2017, "Christopher Nolan", "Hoyte van Hoytema",
        tags=["tense", "action", "war", "survival"],
        visual_signature="Bleached, desaturated coastal palette; relentless ticking-clock tension through intercutting three timelines",
        key_techniques=["IMAX handheld in water", "minimal dialogue — visual storytelling", "Shepard tone in score mirrors visual escalation"],
    ),
    FilmReference(
        "Oppenheimer", 2023, "Christopher Nolan", "Hoyte van Hoytema",
        tags=["tense", "somber", "drama", "historical"],
        visual_signature="IMAX B&W for Strauss subjective, vivid color for Oppenheimer; extreme close-ups of faces as landscapes",
        key_techniques=["IMAX 65mm B&W film (first ever)", "macro photography for atomic imagery", "shallow DOF isolating subjects in crowds"],
    ),

    # ── Classic cinematography touchstones ──
    FilmReference(
        "The Godfather", 1972, "Francis Ford Coppola", "Gordon Willis",
        tags=["tense", "somber", "drama", "crime"],
        visual_signature="Top-lit faces sinking into deep shadow; warm amber interiors vs harsh outdoor light",
        key_techniques=["overhead practicals only — 'Prince of Darkness' lighting", "slow zoom-ins during power shifts", "tableau compositions"],
    ),
    FilmReference(
        "Blade Runner", 1982, "Ridley Scott", "Jordan Cronenweth",
        tags=["somber", "sci-fi", "noir", "dystopian"],
        visual_signature="Rain-soaked neon reflecting off wet surfaces; dense atmospheric haze, shafts of light through venetian blinds",
        key_techniques=["smoke/haze for volumetric light", "anamorphic flares", "noir key lighting in a sci-fi context"],
    ),
    FilmReference(
        "Schindler's List", 1993, "Steven Spielberg", "Janusz Kamiński",
        tags=["somber", "drama", "war", "historical"],
        visual_signature="High-contrast B&W with documentary grain; the girl in the red coat as sole color accent",
        key_techniques=["handheld 'newsreel' style", "single-source hard lighting", "selective color for symbolic emphasis"],
    ),
    FilmReference(
        "No Country for Old Men", 2007, "Coen Brothers", "Roger Deakins",
        tags=["tense", "thriller", "western"],
        visual_signature="Flat West Texas light, muted earth tones; empty wide shots that make violence feel inevitable",
        key_techniques=["natural available light", "negative space in wide compositions", "minimal score — silence is the tension"],
    ),
    FilmReference(
        "Sicario", 2015, "Denis Villeneuve", "Roger Deakins",
        tags=["tense", "action", "thriller"],
        visual_signature="Golden-hour desert light bleeding into oppressive tunnel darkness; silhouettes against burning sky",
        key_techniques=["magic-hour extended shooting", "thermal/night-vision POV", "wide establishing shots before claustrophobic interiors"],
    ),
    FilmReference(
        "1917", 2019, "Sam Mendes", "Roger Deakins",
        tags=["tense", "action", "war"],
        visual_signature="Continuous single-take illusion; camera as companion, always at soldier's pace through trenches and fields",
        key_techniques=["stitched long takes", "natural light + hidden practicals", "Steadicam following movement through confined spaces"],
    ),
    FilmReference(
        "Moonlight", 2016, "Barry Jenkins", "James Laxton",
        tags=["somber", "emotional", "drama"],
        visual_signature="Saturated blues and purples of Miami night; intimate close-ups where faces fill the frame",
        key_techniques=["direct-to-camera close-ups for intimacy", "color-coded chapters", "shallow DOF soft backgrounds"],
    ),
    FilmReference(
        "Mad Max: Fury Road", 2015, "George Miller", "John Seale",
        tags=["action", "desert", "kinetic"],
        visual_signature="Hyper-saturated orange desert against teal sky; center-framed action for constant eye-tracking",
        key_techniques=["center-frame composition for fast cutting", "practical stunts over CG", "crash zooms and ramping speed"],
    ),
    FilmReference(
        "The Revenant", 2015, "Alejandro G. Iñárritu", "Emmanuel Lubezki",
        tags=["tense", "somber", "survival", "western"],
        visual_signature="Ultra-wide natural-light landscapes; breath-fogged lenses, blood-spatter on glass — visceral and immersive",
        key_techniques=["natural light only", "wide-angle close-ups for distortion", "long unbroken takes"],
    ),
    FilmReference(
        "La La Land", 2016, "Damien Chazelle", "Linus Sandgren",
        tags=["uplifting", "romance", "musical"],
        visual_signature="Magic-hour pastels, saturated primary colors; long Steadicam dance sequences celebrating classic Hollywood",
        key_techniques=["CinemaScope anamorphic", "whip pans between musical numbers", "golden-hour backlighting"],
    ),
    FilmReference(
        "Amélie", 2001, "Jean-Pierre Jeunet", "Bruno Delbonnel",
        tags=["uplifting", "whimsical", "comedy"],
        visual_signature="Hyper-stylized warm greens and reds; fish-eye lenses, snap zooms, and tilt-shifts for storybook feel",
        key_techniques=["heavy color grading — green/red palette", "macro inserts of small objects", "wide-angle lens distortion for whimsy"],
    ),
    FilmReference(
        "Drive", 2011, "Nicolas Winding Refn", "Newton Thomas Sigel",
        tags=["tense", "action", "noir", "neo-noir"],
        visual_signature="Neon-soaked Los Angeles night; long silences punctuated by extreme violence; pink/cyan split",
        key_techniques=["slow dolly reveals", "neon-lit close-ups", "extreme contrast between stillness and violence"],
    ),
    FilmReference(
        "Parasite", 2019, "Bong Joon-ho", "Hong Kyung-pyo",
        tags=["tense", "drama", "thriller"],
        visual_signature="Architectural framing — houses as class metaphor; precise blocking where vertical = power",
        key_techniques=["vertical composition for class hierarchy", "hidden cuts in long master shots", "light/shadow as wealth metaphor"],
    ),
    FilmReference(
        "There Will Be Blood", 2007, "Paul Thomas Anderson", "Robert Elswit",
        tags=["tense", "somber", "drama", "western"],
        visual_signature="Wide-open landscapes that trap characters; firelight and oil-black shadows; operatic visual scale",
        key_techniques=["long-lens compression of desert landscapes", "single-source firelight", "sustained wide shots before sudden close-ups"],
    ),
    FilmReference(
        "Her", 2013, "Spike Jonze", "Hoyte van Hoytema",
        tags=["somber", "emotional", "romance", "sci-fi"],
        visual_signature="Warm peach/coral palette, soft natural light; compositions that emphasize loneliness in crowds",
        key_techniques=["shallow DOF soft backgrounds", "warm pastel color grading", "close-ups of hands and details, not just faces"],
    ),
]


# ── Cinematographer Signatures ──

CINEMATOGRAPHERS: list[DPSignature] = [
    DPSignature(
        "Roger Deakins",
        known_for="Invisible, naturalistic lighting that serves the story without calling attention to itself",
        signature_look="Clean compositions, deep focus, motivated single-source lighting, earthy muted palettes",
        notable_films=["No Country for Old Men", "Blade Runner 2049", "1917", "Sicario", "Prisoners"],
        style_tags=["tense", "somber", "natural", "western", "thriller"],
    ),
    DPSignature(
        "Hoyte van Hoytema",
        known_for="Large-format IMAX intimacy — making epic feel personal",
        signature_look="65mm/IMAX grain, warm natural tones, vast landscapes with intimate close-ups, lens flares from real sources",
        notable_films=["Interstellar", "Dunkirk", "Oppenheimer", "Her", "Tenet"],
        style_tags=["epic", "somber", "tense", "sci-fi", "emotional"],
    ),
    DPSignature(
        "Wally Pfister",
        known_for="Nolan's original visual partner — grounded realism with scale",
        signature_look="Underexposed shadows, anamorphic widescreen, practical lighting, muted urban palettes",
        notable_films=["Memento", "The Dark Knight", "Inception", "The Prestige", "Batman Begins"],
        style_tags=["tense", "action", "noir", "urban"],
    ),
    DPSignature(
        "Emmanuel Lubezki",
        known_for="Immersive long takes in natural light — cinema as lived experience",
        signature_look="Wide-angle close-ups, unbroken Steadicam takes, natural and firelight only, visceral immediacy",
        notable_films=["The Revenant", "Birdman", "Children of Men", "Gravity", "The Tree of Life"],
        style_tags=["tense", "somber", "survival", "epic"],
    ),
    DPSignature(
        "Gordon Willis",
        known_for="'The Prince of Darkness' — master of shadow and underexposure",
        signature_look="Top-lit faces with eyes in shadow, deep blacks, warm amber practicals, classical compositions",
        notable_films=["The Godfather", "The Godfather Part II", "Manhattan", "All the President's Men"],
        style_tags=["somber", "tense", "drama", "crime"],
    ),
    DPSignature(
        "Janusz Kamiński",
        known_for="Spielberg's collaborator — emotional, high-contrast, atmospheric",
        signature_look="Blown-out windows, hard backlight, smoke/haze diffusion, high contrast",
        notable_films=["Schindler's List", "Saving Private Ryan", "Munich", "The Fabelmans"],
        style_tags=["somber", "action", "war", "emotional"],
    ),
    DPSignature(
        "Bradford Young",
        known_for="Painterly underexposure celebrating dark skin tones",
        signature_look="Low-key lighting, rich shadows, warm earth tones, shallow DOF, faces emerging from darkness",
        notable_films=["Arrival", "Selma", "When They See Us", "Solo: A Star Wars Story"],
        style_tags=["somber", "emotional", "drama", "sci-fi"],
    ),
]


# ── Technique Catalogue ──

TECHNIQUES: list[Technique] = [
    # Lighting
    Technique(
        "Chiaroscuro", "lighting",
        "Dramatic contrast between light and shadow. Faces half-lit, environments carved by single hard sources.",
        "Power dynamics, moral duality, characters hiding something. Classic for interrogation and confrontation scenes.",
        films=["The Godfather", "Schindler's List", "The Dark Knight"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "High-key natural light", "lighting",
        "Soft, even, abundant light from large natural sources (windows, overcast sky). Minimal shadows.",
        "Openness, honesty, vulnerability, pastoral calm. Strips away visual hiding places.",
        films=["Her", "Moonlight", "Nomadland"],
        mood_tags=["uplifting", "somber", "emotional"],
    ),
    Technique(
        "Practical-source only", "lighting",
        "All light in the scene comes from visible in-frame sources: lamps, candles, screens, fire.",
        "Realism and immersion. Forces the audience to feel 'present' in the space. Nolan's preferred approach.",
        films=["Interstellar", "The Revenant", "Barry Lyndon"],
        mood_tags=["somber", "tense"],
    ),
    Technique(
        "Silhouette / contre-jour", "lighting",
        "Subject backlit so they become a dark shape against bright background.",
        "Mystery, anonymity, epic scale. The audience projects emotion onto the featureless figure.",
        films=["Sicario", "Dunkirk", "No Country for Old Men"],
        mood_tags=["tense", "action", "somber"],
    ),
    Technique(
        "Neon-noir", "lighting",
        "Colored artificial light (neon signs, LED) as the dominant source, often reflected in wet surfaces.",
        "Urban isolation, night-world energy, moral ambiguity in a modern setting.",
        films=["Drive", "Blade Runner", "Collateral"],
        mood_tags=["tense", "action"],
    ),

    # Composition
    Technique(
        "Negative space", "composition",
        "Subject occupies a small portion of frame; vast emptiness around them.",
        "Isolation, vulnerability, insignificance against environment. Lets the landscape 'act.'",
        films=["No Country for Old Men", "Interstellar", "The Revenant"],
        mood_tags=["somber", "tense"],
    ),
    Technique(
        "Center framing", "composition",
        "Subject placed dead-center in the frame, often symmetrically.",
        "Authority, obsession, unease. Kubrick and Wes Anderson's signature. Creates a confrontational gaze.",
        films=["The Shining", "Mad Max: Fury Road", "Grand Budapest Hotel"],
        mood_tags=["tense", "action", "uplifting"],
    ),
    Technique(
        "Frame within a frame", "composition",
        "Subject viewed through doorways, windows, mirrors, or architectural elements.",
        "Entrapment, surveillance, voyeurism. The character is 'boxed in' by their circumstances.",
        films=["Parasite", "The Dark Knight", "Rear Window"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Vertical composition", "composition",
        "Blocking and framing that emphasizes vertical axis — staircases, levels, looking up/down.",
        "Power hierarchy. Who is above and who is below tells the story of class, authority, or aspiration.",
        films=["Parasite", "Joker", "Oppenheimer"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Wide master with sudden close-up", "composition",
        "Sustained wide shot that suddenly cuts to an extreme close-up.",
        "Shock, revelation, emotional punctuation. The contrast creates visceral impact. PTA and Nolan use this frequently.",
        films=["There Will Be Blood", "Oppenheimer", "Dunkirk"],
        mood_tags=["tense", "action"],
    ),

    # Color
    Technique(
        "Desaturated / bleach bypass", "color",
        "Pulled color, reduced saturation, lifted blacks. Looks like faded or processed film stock.",
        "Grit, memory, war fatigue, psychic numbness. Removes the 'comfort' of full color.",
        films=["Saving Private Ryan", "Dunkirk", "Memento"],
        mood_tags=["tense", "somber", "war"],
    ),
    Technique(
        "Warm amber / golden hour", "color",
        "Scene bathed in warm golden-orange tones. Often shot during actual golden hour or graded to match.",
        "Nostalgia, warmth, fleeting beauty. The audience feels time running out — or a memory being held on to.",
        films=["Interstellar", "La La Land", "The Godfather"],
        mood_tags=["uplifting", "somber", "emotional"],
    ),
    Technique(
        "Teal and orange", "color",
        "Complementary color split: warm skin tones against cool blue/teal backgrounds.",
        "Visual pop and readability. Separates subject from environment. Hollywood's most common modern grade.",
        films=["Mad Max: Fury Road", "Transformers", "Sicario"],
        mood_tags=["action", "tense"],
    ),
    Technique(
        "Monochrome / B&W", "color",
        "Full black and white. Strips the image to light, shadow, and shape.",
        "Timelessness, memory, stark moral clarity. Removes distraction of color; focuses on form and emotion.",
        films=["Schindler's List", "Oppenheimer", "Roma"],
        mood_tags=["somber", "tense", "drama"],
    ),
    Technique(
        "Color-coded storytelling", "color",
        "Specific colors assigned to characters, timelines, or emotional states.",
        "Subconscious narrative cues. The audience feels the shift before understanding it intellectually.",
        films=["Moonlight", "Oppenheimer", "The Matrix"],
        mood_tags=["tense", "somber", "uplifting"],
    ),

    # Camera movement
    Technique(
        "Slow dolly in", "movement",
        "Camera creeps forward toward the subject almost imperceptibly.",
        "Building dread, dawning realization, focus intensifying. Kubrick's signature approach.",
        films=["The Shining", "There Will Be Blood", "Oppenheimer"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Handheld / vérité", "movement",
        "Camera held on the operator's shoulder; organic, slightly unstable movement.",
        "Urgency, documentary realism, immersion. Puts the audience 'inside' the chaos.",
        films=["Dunkirk", "Saving Private Ryan", "The Bourne Ultimatum"],
        mood_tags=["tense", "action"],
    ),
    Technique(
        "Steadicam follow", "movement",
        "Smooth gliding camera following or leading a character through space.",
        "Journey, discovery, passage through a world. Creates a dreamlike, weightless quality.",
        films=["The Shining", "1917", "Goodfellas"],
        mood_tags=["tense", "uplifting"],
    ),
    Technique(
        "Static locked-off", "movement",
        "Camera bolted to the tripod. Zero movement. Patient, observational.",
        "Inevitability, stillness before violence, contemplation. Forces the audience to study the frame.",
        films=["No Country for Old Men", "Parasite", "There Will Be Blood"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Crash zoom / snap zoom", "movement",
        "Rapid zoom in or out, often handheld. Immediate, visceral.",
        "Surprise, comedic punctuation, or sudden threat. Breaks the visual rhythm intentionally.",
        films=["Mad Max: Fury Road", "Jaws", "The Evil Dead"],
        mood_tags=["action", "tense"],
    ),

    # Lens
    Technique(
        "Wide-angle close-up", "lens",
        "Wide lens (18-24mm) used very close to a face. Exaggerates features, distorts perspective.",
        "Intimacy pushed to discomfort. The audience cannot escape the character's face. Heightens anguish or mania.",
        films=["The Revenant", "Requiem for a Dream", "Fear and Loathing in Las Vegas"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Long-lens compression", "lens",
        "Telephoto (85-200mm+). Flattens depth, stacks background elements against subject.",
        "Surveillance, entrapment, the world closing in on the character. Separates subject with shallow DOF.",
        films=["Sicario", "There Will Be Blood", "Zodiac"],
        mood_tags=["tense", "somber"],
    ),
    Technique(
        "Anamorphic widescreen", "lens",
        "Anamorphic lenses create a 2.39:1 ratio with characteristic oval bokeh and horizontal flares.",
        "Epic, cinematic grandeur. The extra width creates compositional breathing room and a '35mm film' texture.",
        films=["Inception", "Blade Runner", "La La Land"],
        mood_tags=["action", "uplifting", "epic"],
    ),
]


# ── Search / Retrieval Tools ──


def search_references(
    mood: str | None = None,
    genre: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Search the film library by mood, genre, and/or keywords.
    Returns compact dicts suitable for LLM context injection.
    """
    scored: list[tuple[int, FilmReference]] = []

    for film in FILMS:
        score = 0
        tags_lower = [t.lower() for t in film.tags]

        if mood and mood.lower() in tags_lower:
            score += 3
        if genre:
            genre_l = genre.lower()
            if genre_l in tags_lower:
                score += 2
            elif any(genre_l in t for t in tags_lower):
                score += 1
        if keywords:
            blob = f"{film.visual_signature} {' '.join(film.key_techniques)} {' '.join(film.tags)}".lower()
            for kw in keywords:
                if kw.lower() in blob:
                    score += 1

        if score > 0:
            scored.append((score, film))

    scored.sort(key=lambda x: -x[0])
    results = []
    for _, f in scored[:limit]:
        results.append({
            "film": f"{f.title} ({f.year})",
            "director": f.director,
            "dp": f.cinematographer,
            "visual_signature": f.visual_signature,
            "techniques": f.key_techniques,
        })
    return results


def search_techniques(
    mood: str | None = None,
    category: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Search the technique catalogue by mood, category, and/or keywords.
    """
    scored: list[tuple[int, Technique]] = []

    for tech in TECHNIQUES:
        score = 0
        if mood and mood.lower() in [t.lower() for t in tech.mood_tags]:
            score += 3
        if category and category.lower() == tech.category.lower():
            score += 2
        if keywords:
            blob = f"{tech.name} {tech.description} {tech.when_to_use}".lower()
            for kw in keywords:
                if kw.lower() in blob:
                    score += 2

        if score > 0:
            scored.append((score, tech))

    scored.sort(key=lambda x: -x[0])
    results = []
    for _, t in scored[:limit]:
        results.append({
            "technique": t.name,
            "category": t.category,
            "description": t.description,
            "when_to_use": t.when_to_use,
            "example_films": t.films,
        })
    return results


def search_cinematographers(
    mood: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 3,
) -> list[dict]:
    """
    Search DP signatures by mood and/or keywords.
    """
    scored: list[tuple[int, DPSignature]] = []

    for dp in CINEMATOGRAPHERS:
        score = 0
        if mood and mood.lower() in [t.lower() for t in dp.style_tags]:
            score += 3
        if keywords:
            blob = f"{dp.name} {dp.known_for} {dp.signature_look}".lower()
            for kw in keywords:
                if kw.lower() in blob:
                    score += 2

        if score > 0:
            scored.append((score, dp))

    scored.sort(key=lambda x: -x[0])
    results = []
    for _, d in scored[:limit]:
        results.append({
            "name": d.name,
            "known_for": d.known_for,
            "signature_look": d.signature_look,
            "notable_films": d.notable_films,
        })
    return results


def _extract_keywords(text: str) -> list[str]:
    """Pull meaningful keywords from user feedback for library search."""
    stop = {
        "the", "a", "an", "is", "it", "too", "very", "more", "less", "not",
        "and", "or", "but", "this", "that", "should", "be", "make", "like",
        "want", "need", "feel", "look", "looks", "doesn", "don", "can", "just",
        "really", "much", "some", "i", "me", "my", "we", "our", "scene",
    }
    words = text.lower().split()
    return [w.strip(".,!?;:'\"") for w in words if len(w) > 2 and w.lower() not in stop]


def gather_references(
    mood: str,
    genre: str | None = None,
    feedback: str = "",
) -> dict:
    """
    Main entry point: gather all relevant references for a director consultation.
    Returns a structured dict ready to inject into the LLM context.
    """
    keywords = _extract_keywords(feedback)

    films = search_references(mood=mood, genre=genre, keywords=keywords, limit=4)
    techniques = search_techniques(mood=mood, keywords=keywords, limit=4)
    dps = search_cinematographers(mood=mood, keywords=keywords, limit=2)

    return {
        "reference_films": films,
        "techniques": techniques,
        "cinematographers": dps,
    }
